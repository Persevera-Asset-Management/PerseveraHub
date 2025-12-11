import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from persevera_tools.data import get_series, get_funds_data
from utils.chart_helpers import create_chart
import streamlit_highcharts as hct
from utils.table import style_table
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

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

st.subheader("Configuração dos Portfólios")
st.markdown(
    "Inclua os **ativos** informando o **ticker** e os **pesos em %** para cada portfólio. "
    "Os pesos serão **normalizados** para somarem 100% antes do backtest."
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
    edited_df = st.data_editor(
        st.session_state["portfolio_table"],
        hide_index=True,
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

    # Coleta todos os tickers únicos
    tickers = list(df_input["Ticker"].unique())

    with st.spinner("Carregando dados dos ativos...", show_time=True):
        data = load_data(tickers, field=["close"], start_date=start_date_str)

    if data.empty:
        st.warning("Não foi possível carregar os dados. Verifique os tickers informados ou tente novamente mais tarde.")
        st.stop()

    data.ffill(inplace=True, limit=1)

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

        weights_raw = weights_raw[weights_raw > 0]
        
        if weights_raw.empty:
            st.warning(f"'{portfolio_name}' não possui pesos válidos (maiores que zero).")
            continue

        # Normaliza pesos
        weights = weights_raw.reindex(available_tickers).fillna(0.0)
        weights = weights / weights.sum()
        portfolio_weights_info[portfolio_name] = weights

        # Calcula curva do portfólio
        # Ajuste: se um ativo não tem dado em um determinado dia (NaN em `returns`),
        # o peso dele é redistribuído proporcionalmente entre os ativos com dado.
        weights_matrix = pd.DataFrame(
            np.tile(weights.values, (len(returns), 1)),
            index=returns.index,
            columns=returns.columns,
        )

        # Zera pesos nos dias/ativos sem retorno observado
        valid_mask = returns.notna()
        weights_matrix = weights_matrix.where(valid_mask, 0.0)

        # Renormaliza linha a linha para que a soma de pesos dos ativos "válidos" seja 1
        row_sums = weights_matrix.sum(axis=1)
        weights_matrix = weights_matrix.div(row_sums.replace(0, np.nan), axis=0).fillna(0.0)

        # Para dias em que nenhum ativo tem dado, o retorno do portfólio será 0
        portfolio_returns = (returns.fillna(0.0) * weights_matrix).sum(axis=1)
        portfolio_index = (1 + portfolio_returns).cumprod() * 100
        
        result_df[portfolio_name] = portfolio_index
        portfolio_returns_df[portfolio_name] = portfolio_returns

        # Calcula estatísticas avançadas
        try:
            # Número de dias úteis no período
            num_days = len(portfolio_returns[portfolio_returns != 0])
            num_years = num_days / 252 if num_days > 0 else 1
            
            # Retorno total e anualizado
            total_return = portfolio_index.iloc[-1] / portfolio_index.iloc[0] - 1
            annualized_return = (1 + total_return) ** (1 / num_years) - 1 if num_years > 0 else 0
            
            # Volatilidade anualizada
            volatility = portfolio_returns.std() * np.sqrt(252)
            
            # Sharpe Ratio (assumindo risk-free rate = 0)
            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
            
            # Máximo Drawdown
            cumulative = (1 + portfolio_returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # Melhor e pior retorno diário
            best_day = portfolio_returns.max()
            worst_day = portfolio_returns.min()
            
            # Retornos mensais
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
            pass

    if result_df.empty:
        st.warning("Nenhum portfólio foi calculado com sucesso.")
        st.stop()

    # ===== VISUALIZAÇÕES =====
    
    row_1 = st.columns(2)
    with row_1[0]:
        # st.subheader("Equity Curve")
        chart = create_chart(
            data=result_df,
            columns=list(result_df.columns),
            names=list(result_df.columns),
            chart_type="line",
            title="Equity Curve",
            y_axis_title="Índice",
        )
        hct.streamlit_highcharts(chart)

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
                use_container_width=True
            )
        else:
            st.warning("Nenhum portfólio foi calculado com sucesso.")

    # Drawdown
    row_2 = st.columns(2)
    with row_2[0]:
        # st.subheader("📉 Drawdown dos Portfólios")
        drawdown_df = pd.DataFrame(index=result_df.index)
        
        for col in result_df.columns:
            cumulative = result_df[col]
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max * 100
            drawdown_df[col] = drawdown
    
        chart_drawdown = create_chart(
            data=drawdown_df,
            columns=list(drawdown_df.columns),
            names=list(drawdown_df.columns),
            chart_type="line",
            title="Drawdown",
            y_axis_title="Drawdown (%)",
        )
        hct.streamlit_highcharts(chart_drawdown)

    with row_2[1]:
        # Correlação entre portfolios (se houver mais de um)
        if len(portfolio_returns_df.columns) > 1:
            # st.subheader("🔗 Correlação entre Portfólios")
            
            corr_matrix = portfolio_returns_df.corr()
            corr_matrix = corr_matrix.where(np.tril(np.ones(corr_matrix.shape)).astype(np.bool_))
            corr_matrix = corr_matrix.sort_index(ascending=False)

            chart_corr = create_chart(
                data=corr_matrix,
                columns=list(corr_matrix.columns),
                names=list(corr_matrix.columns),
                chart_type="heatmap",
                title="Correlação",
                y_axis_title="Portfólio",
            )
            hct.streamlit_highcharts(chart_corr)
        else:
            st.warning("Há somente um portfólio. Não é possível calcular a correlação entre portfólios.")