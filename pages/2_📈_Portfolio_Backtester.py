import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

import streamlit as st
import streamlit_highcharts as hct

from utils.chart_helpers import create_chart
from utils.table import style_table
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

from persevera_tools.data import get_series, get_funds_data
from persevera_tools.quant_research.metrics import (
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
)

# Edite este dicionário para adicionar/remover benchmarks disponíveis.
# Formato: "Nome exibido no multiselect": "ticker_na_base"
BENCHMARK_OPTIONS: dict[str, str] = {
    "CDI": "br_cdi_index",
    "IBOV": "br_ibovespa",
    "BRL/USD": "brl_usd",
    "S&P 500 (USD)": "us_sp500",
}

st.set_page_config(
    page_title="Portfolio Backtester | Persevera",
    page_icon="📈",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title('Portfolio Backtester')

@st.cache_data(ttl=3600)
def load_data(codes, field, start_date):
    try:
        try:
            indicators = get_series(codes, start_date=start_date, field=field)
        except Exception as e:
            indicators = pd.DataFrame()
        try:
            funds = get_funds_data(cnpjs=codes, start_date=start_date, fields=['fund_nav'])
        except Exception as e:
            funds = pd.DataFrame()
        
        df = pd.concat([indicators.dropna(how='all', axis='columns'), funds.dropna(how='all', axis='columns')], axis=1)
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", min_value=datetime(2000, 1, 1), max_value=datetime.today(), value=datetime(2010, 1, 1), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')
    risk_free_rate = st.number_input(
        "Taxa Livre de Risco (% a.a.)",
        min_value=0.0,
        max_value=50.0,
        value=10.75,
        step=0.25,
        format="%.2f",
    ) / 100
    selected_benchmarks = st.multiselect(
        "Benchmarks",
        options=list(BENCHMARK_OPTIONS.keys()),
    )

st.subheader("Configuração dos Portfólios")
st.markdown(
    "Inclua os **ativos** informando o **ticker** e os **pesos em %** para cada portfólio. "
    "Pesos **positivos** são normalizados para somar 100%. "
    "Use pesos **negativos** para posições vendidas — nesse caso os valores são usados como alocação absoluta (ex: −50, −50, +200)."
)

# Inicialização do estado
if "num_portfolios" not in st.session_state:
    st.session_state["num_portfolios"] = 1

if "portfolio_table" not in st.session_state:
    st.session_state["portfolio_table"] = pd.DataFrame({"Ticker": [""], "Portfolio 1 (%)": [0.0]})

# Botões para adicionar/remover portfolios
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("➕ Adicionar Portfolio"):
        st.session_state["num_portfolios"] += 1
        new_col_name = f"Portfolio {st.session_state['num_portfolios']} (%)"
        st.session_state["portfolio_table"][new_col_name] = 0.0
        st.rerun()

with col2:
    if st.button("➖ Remover Portfolio") and st.session_state["num_portfolios"] > 1:
        col_to_remove = f"Portfolio {st.session_state['num_portfolios']} (%)"
        if col_to_remove in st.session_state["portfolio_table"].columns:
            st.session_state["portfolio_table"] = st.session_state["portfolio_table"].drop(columns=[col_to_remove])
        st.session_state["num_portfolios"] -= 1
        st.rerun()

with st.form("portfolio_form"):
    weight_col_config = {
        col: st.column_config.NumberColumn(col, format="%.1f")
        for col in st.session_state["portfolio_table"].columns
        if col != "Ticker"
    }
    edited_df = st.data_editor(
        st.session_state["portfolio_table"],
        hide_index=True,
        column_config=weight_col_config,
        use_container_width=True,
        key="portfolio_table_editor",
        num_rows="dynamic",
    )

    run_backtest = st.form_submit_button("Rodar Backtest")

st.session_state["portfolio_table"] = edited_df

if run_backtest:
    df_input = edited_df.copy()
    df_input["Ticker"] = df_input["Ticker"].astype(str).str.strip()
    df_input = df_input[df_input["Ticker"] != ""]

    if df_input.empty:
        st.warning("Informe ao menos um ticker para rodar o backtest.")
        st.stop()

    # Identifica as colunas de peso (todas menos "Ticker")
    weight_columns = [col for col in df_input.columns if col != "Ticker"]
    
    if not weight_columns:
        st.warning("Nenhum portfólio configurado.")
        st.stop()

    # Coleta todos os tickers únicos (portfólios + benchmarks, sem duplicatas)
    tickers = list(df_input["Ticker"].unique())
    benchmark_tickers = [BENCHMARK_OPTIONS[label] for label in selected_benchmarks]
    load_tickers = list(dict.fromkeys(tickers + benchmark_tickers))

    with st.spinner("Carregando dados dos ativos...", show_time=True):
        data = load_data(load_tickers, field=["close"], start_date=start_date_str)

    if data.empty:
        st.warning("Não foi possível carregar os dados. Verifique os tickers informados ou tente novamente mais tarde.")
        st.stop()

    data = data.ffill(limit=1)

    # Prepara base de preços (apenas fechamento)
    close_prices = data.copy()
    if isinstance(close_prices.columns, pd.MultiIndex):
        close_prices = close_prices.copy()
        close_prices.columns = close_prices.columns.get_level_values(0)

    # Garante que usamos apenas os tickers que possuem dados
    available_tickers = [t for t in tickers if t in close_prices.columns]
    close_prices = close_prices[available_tickers]

    if close_prices.empty:
        st.warning("Não há dados de preços disponíveis para os ativos informados.")
        st.stop()

    prices = close_prices[available_tickers].dropna(how="all")
    if prices.empty:
        st.warning("Não há histórico suficiente para calcular o backtest.")
        st.stop()

    # Calcula retornos (mantendo NaNs para tratar ativos "não iniciados")
    returns = prices.pct_change(fill_method=None)

    # Processa cada portfólio
    result_df = pd.DataFrame(index=prices.index)
    portfolio_returns_df = pd.DataFrame(index=prices.index)
    portfolio_stats = []
    portfolio_weights_info = {}

    for weight_col in weight_columns:
        portfolio_name = weight_col.replace(" (%)", "")
        
        try:
            weights_raw = df_input.set_index("Ticker")[weight_col].astype(float)
        except Exception:
            st.error(f"Não foi possível ler os pesos para '{portfolio_name}'. Verifique os valores.")
            continue

        # Remove zeros, mas mantém pesos negativos (posições vendidas)
        weights_raw = weights_raw[weights_raw != 0]

        if weights_raw.empty:
            st.warning(f"'{portfolio_name}' não possui pesos válidos (diferentes de zero).")
            continue

        # Modo alavancado: qualquer peso negativo → alocação absoluta (divide por 100)
        # Modo padrão: todos positivos → normaliza para somar 1
        is_leveraged = (weights_raw < 0).any()

        weights = weights_raw.reindex(available_tickers).fillna(0.0)
        if is_leveraged:
            weights = weights / 100
        else:
            weights = weights / weights.sum()
        portfolio_weights_info[portfolio_name] = weights

        # Calcula curva do portfólio
        weights_matrix = pd.DataFrame(
            np.tile(weights.values, (len(returns), 1)),
            index=returns.index,
            columns=returns.columns,
        )

        # Zera pesos nos dias/ativos sem retorno observado
        valid_mask = returns.notna()
        weights_matrix = weights_matrix.where(valid_mask, 0.0)

        if not is_leveraged:
            # Long-only: redistribui pesos de ativos sem dado proporcionalmente
            row_sums = weights_matrix.sum(axis=1)
            weights_matrix = weights_matrix.div(row_sums.replace(0, np.nan), axis=0).fillna(0.0)
        # Alavancado: mantém pesos fixos; ativo sem dado contribui com retorno 0

        # Para dias em que nenhum ativo tem dado, o retorno do portfólio será 0
        portfolio_returns = (returns.fillna(0.0) * weights_matrix).sum(axis=1)
        portfolio_index = (1 + portfolio_returns).cumprod() * 100
        
        result_df[portfolio_name] = portfolio_index
        portfolio_returns_df[portfolio_name] = portfolio_returns

        # Calcula estatísticas avançadas
        try:
            total_return = portfolio_index.iloc[-1] / portfolio_index.iloc[0] - 1
            annualized_return = calculate_annualized_return(portfolio_index)
            volatility = calculate_annualized_volatility(portfolio_index, frequency='daily')
            sharpe_ratio = calculate_sharpe_ratio(portfolio_index, risk_free_rate=risk_free_rate)
            max_drawdown = calculate_max_drawdown(portfolio_index)

            best_day = portfolio_returns.max()
            worst_day = portfolio_returns.min()

            monthly_returns = portfolio_returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
            best_month = monthly_returns.max()
            worst_month = monthly_returns.min()

            portfolio_stats.append({
                "Portfólio": portfolio_name,
                "Retorno Total": total_return * 100,
                "Retorno Anualizado": annualized_return * 100,
                "Volatilidade Anual": volatility * 100,
                "Sharpe Ratio": sharpe_ratio,
                "Máx. Drawdown": max_drawdown * 100,
                "Melhor Dia": best_day * 100,
                "Pior Dia": worst_day * 100,
                "Melhor Mês": best_month * 100,
                "Pior Mês": worst_month * 100,
            })
        except Exception as e:
            st.warning(f"Erro ao calcular estatísticas para '{portfolio_name}': {e}")

    if result_df.empty:
        st.warning("Nenhum portfólio foi calculado com sucesso.")
        st.stop()

    # ===== BENCHMARKS =====
    benchmark_returns_dict: dict[str, pd.Series] = {}
    chart_df = result_df.copy()

    for label in selected_benchmarks:
        bm_ticker = BENCHMARK_OPTIONS[label]
        if bm_ticker not in data.columns:
            st.warning(f"Benchmark '{label}' ({bm_ticker}) não encontrado nos dados.")
            continue

        bm_raw = data[bm_ticker].reindex(result_df.index).ffill()
        bm_first_valid = bm_raw.first_valid_index()
        if bm_first_valid is None:
            st.warning(f"Benchmark '{label}' não possui dados no período selecionado.")
            continue

        bm_index = bm_raw / bm_raw[bm_first_valid] * 100
        bm_returns = bm_raw.pct_change(fill_method=None)
        benchmark_returns_dict[label] = bm_returns
        chart_df[label] = bm_index

        try:
            bm_total_return = bm_index.iloc[-1] / bm_index.iloc[0] - 1
            bm_monthly = bm_returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
            portfolio_stats.append({
                "Portfólio": label,
                "Retorno Total": bm_total_return * 100,
                "Retorno Anualizado": calculate_annualized_return(bm_index) * 100,
                "Volatilidade Anual": calculate_annualized_volatility(bm_index, frequency='daily') * 100,
                "Sharpe Ratio": calculate_sharpe_ratio(bm_index, risk_free_rate=risk_free_rate),
                "Máx. Drawdown": calculate_max_drawdown(bm_index) * 100,
                "Melhor Dia": bm_returns.max() * 100,
                "Pior Dia": bm_returns.min() * 100,
                "Melhor Mês": bm_monthly.max() * 100,
                "Pior Mês": bm_monthly.min() * 100,
            })
        except Exception as e:
            st.warning(f"Erro ao calcular estatísticas do benchmark '{label}': {e}")

    # ===== VISUALIZAÇÕES =====
    
    row_1 = st.columns(2)
    with row_1[0]:
        chart = create_chart(
            data=chart_df,
            columns=list(chart_df.columns),
            names=list(chart_df.columns),
            chart_type="line",
            title="Equity Curve",
            y_axis_title="Índice",
        )
        hct.streamlit_highcharts(chart, key="equity_curve")

    with row_1[1]:
        if portfolio_stats:
            st.markdown("##### Estatísticas de Performance")
            stats_df = pd.DataFrame(portfolio_stats).set_index("Portfólio")
            
            st.dataframe(
                style_table(
                    stats_df,
                    percent_cols=["Retorno Total", "Retorno Anualizado", "Volatilidade Anual", 
                                "Máx. Drawdown", "Melhor Dia", "Pior Dia", "Melhor Mês", "Pior Mês"],
                    numeric_cols_format_as_float=["Sharpe Ratio"],
                ),
                width='stretch'
            )
        else:
            st.warning("Nenhum portfólio foi calculado com sucesso.")

    # Drawdown
    row_2 = st.columns(2)
    with row_2[0]:
        drawdown_df = pd.DataFrame(index=chart_df.index)
        for col in chart_df.columns:
            cumulative = chart_df[col]
            running_max = cumulative.expanding().max()
            drawdown_df[col] = (cumulative - running_max) / running_max * 100

        chart_drawdown = create_chart(
            data=drawdown_df,
            columns=list(drawdown_df.columns),
            names=list(drawdown_df.columns),
            chart_type="line",
            title="Drawdown",
            y_axis_title="Drawdown (%)",
        )
        hct.streamlit_highcharts(chart_drawdown, key="drawdown")

    with row_2[1]:
        # Correlação — inclui benchmarks selecionados
        corr_df = portfolio_returns_df.copy()
        for bm_label, bm_rets in benchmark_returns_dict.items():
            corr_df[bm_label] = bm_rets

        if len(corr_df.columns) > 1:
            corr_matrix = corr_df.corr()
            corr_matrix = corr_matrix.where(np.tril(np.ones(corr_matrix.shape)).astype(np.bool_))
            # corr_matrix = corr_matrix.sort_index(ascending=False)

            chart_corr = create_chart(
                data=corr_matrix,
                columns=list(corr_matrix.columns),
                names=list(corr_matrix.columns),
                chart_type="heatmap",
                title="Correlação",
                y_axis_title="Portfólio",
            )
            hct.streamlit_highcharts(chart_corr, key="correlacao")
        else:
            st.warning("Há somente um portfólio e nenhum benchmark. Não é possível calcular a correlação.")