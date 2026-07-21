import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from utils.chart_helpers import create_chart
from utils.table import style_table, get_monthly_returns_table, get_performance_table

from services.position_service import (
    load_assets,
    load_equities_portfolio,
    load_historical_positions_from_comdinheiro,
    load_portfolios_rvqm,
    prepare_comdinheiro_historical_positions_df,
)
from services.rvqm_adherence_service import (
    build_adherence_summary,
    calculate_portfolio_twr,
    filter_equity_sleeve,
    pivot_model_weights,
    positions_to_weights,
)

from persevera_tools.data import get_descriptors, get_series
from persevera_tools.quant_research.metrics import calculate_drawdown

_CACHE_TTL = 10800  # 3h — alinhado a position_service

st.title("RVQM · Portfolio")

# =============================================================================
# Funções de carregamento
# =============================================================================

@st.cache_data(ttl=_CACHE_TTL)
def load_data(codes: tuple, start_date, field: tuple):
    descriptors = list(field)
    return get_descriptors(list(codes), start_date=start_date, descriptors=descriptors)

@st.cache_data(ttl=_CACHE_TTL)
def load_indicators(codes: tuple, start_date):
    return get_series(list(codes), start_date=start_date)


def merge_prices(base_prices: pd.DataFrame, extra_tickers: list, start_date) -> pd.DataFrame:
    """Reusa preços já carregados e busca só tickers ausentes."""
    missing = sorted(set(extra_tickers) - set(base_prices.columns))
    if not missing:
        return base_prices
    extra = load_data(tuple(missing), start_date=start_date, field=("price_close",))
    if extra.empty:
        return base_prices
    return base_prices.join(extra, how="outer")


def build_adherence_payload(
    raw_hist: pd.DataFrame,
    prices: pd.DataFrame,
    strategy_weights: pd.DataFrame,
    strategy_returns: pd.Series,
    start_ts,
    end_ts,
) -> dict:
    """Processa raw ComDinheiro → pesos, retornos e summary (cacheável)."""
    RVQM_INSTRUMENTS = ("Ação", "BDR")
    hist_positions = prepare_comdinheiro_historical_positions_df(raw_hist)
    equity_positions = filter_equity_sleeve(hist_positions, load_assets(RVQM_INSTRUMENTS))
    if equity_positions.empty:
        return {"status": "empty_sleeve"}

    client_weights = positions_to_weights(equity_positions)
    client_tickers = sorted(
        {ticker for weights in client_weights.values() for ticker in weights.columns}
    )
    price_start = min(strategy_weights.index.min(), equity_positions["Data"].min())
    adherence_prices = merge_prices(prices, client_tickers, start_date=price_start)
    if adherence_prices.empty:
        return {"status": "empty_prices"}

    client_returns = {
        name: calculate_portfolio_twr(weights, adherence_prices, lag_weights=True)
        for name, weights in client_weights.items()
    }
    strategy_period = strategy_returns.loc[
        (strategy_returns.index >= start_ts) & (strategy_returns.index <= end_ts)
    ]
    client_period = {
        name: rets.loc[(rets.index >= start_ts) & (rets.index <= end_ts)]
        for name, rets in client_returns.items()
    }
    summary = build_adherence_summary(
        client_period,
        strategy_period,
        client_weights,
        strategy_weights,
    )
    return {
        "status": "ok",
        "client_weights": client_weights,
        "strategy_period": strategy_period,
        "client_period": client_period,
        "summary": summary,
    }

# =============================================================================
# Funções analíticas
# =============================================================================

def color_returns_cell(val):
    if pd.isna(val):
        return ''
    if val > 0:
        intensity = min(val / 8.0, 1.0)
        r = int(198 * (1 - intensity) + 26 * intensity)
        g = int(239 * (1 - intensity) + 122 * intensity)
        b = int(198 * (1 - intensity) + 49 * intensity)
        text = 'white' if intensity > 0.6 else 'black'
    else:
        intensity = min(abs(val) / 8.0, 1.0)
        r = int(255 * (1 - intensity) + 192 * intensity)
        g = int(199 * (1 - intensity) + 0 * intensity)
        b = int(206 * (1 - intensity) + 0 * intensity)
        text = 'white' if intensity > 0.6 else 'black'
    return f'background-color: rgb({r},{g},{b}); color: {text}'

# =============================================================================
# Carregamento de dados
# =============================================================================

with st.spinner("Carregando composição da carteira..."):
    equities_portfolio = load_equities_portfolio()
    securities_list = tuple(sorted(equities_portfolio["code"].dropna().unique().tolist()))
    data_start = equities_portfolio["date"].min()

if len(securities_list) == 0:
    st.warning("Nenhum dado disponível para exibir.")
    st.stop()

with st.spinner("Carregando preços e indicadores..."):
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            prices_future = executor.submit(
                load_data, securities_list, data_start, ("price_close",)
            )
            indicators_future = executor.submit(
                load_indicators,
                ("br_ibovespa", "br_smll", "br_cdi_index"),
                data_start,
            )
            raw_data = prices_future.result()
            indicators = indicators_future.result()
    except Exception as e:
        st.error(f"Erro ao carregar preços/indicadores: {e}")
        st.stop()

if raw_data.empty:
    st.warning("Nenhum dado disponível para exibir.")
    st.stop()

prices = raw_data

# =============================================================================
# Composição Atual
# =============================================================================

current_date = equities_portfolio['date'].max()
current_portfolio = (
    equities_portfolio[equities_portfolio['date'] == current_date]
    .copy()
    .sort_values('weight', ascending=False)
    .reset_index(drop=True)
)
total_weight = current_portfolio['weight'].sum()
current_portfolio['weight_pct'] = current_portfolio['weight'] / total_weight * 100

st.markdown(
    f"<p style='color:#888; font-size:0.85rem; margin-bottom:6px;'>"
    f"{len(current_portfolio)} ativos &nbsp;·&nbsp; {current_date.strftime('%d/%m/%Y')}"
    f"</p>",
    unsafe_allow_html=True,
)

chips = "".join(
    f'<span style="display:inline-block; background:#1e3a5f; color:white; border-radius:8px; '
    f'padding:6px 14px; margin:3px 4px; font-size:0.83rem; font-weight:600; letter-spacing:0.3px;">'
    f'{row["code"]}&nbsp;'
    f'<span style="font-weight:300; opacity:0.7;">{row["weight_pct"]:.1f}%</span></span>'
    for _, row in current_portfolio.iterrows()
)
st.markdown(f'<div style="line-height:2.8">{chips}</div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# =============================================================================
# Retornos e cumulativo completo
# =============================================================================

weights_df = pivot_model_weights(equities_portfolio)
weights_df = weights_df.reindex(prices.index).ffill()

returns_portfolio = calculate_portfolio_twr(weights_df, prices, lag_weights=True)
returns_df = pd.concat([returns_portfolio, indicators.pct_change(fill_method=None).fillna(0)], axis=1)
returns_df.columns = ['Carteira', 'Ibovespa', 'SMLL', 'CDI']

# =============================================================================
# Histórico de Alocações (só materializa se solicitado)
# =============================================================================

show_weights_history = st.checkbox("Mostrar histórico de alocações", value=False)
if show_weights_history:
    weights_history_table = weights_df.replace(0, np.nan).mul(100)
    weights_history_table.index = weights_history_table.index.strftime('%Y-%m-%d')
    st.dataframe(
        style_table(
            weights_history_table,
            percent_cols=weights_df.columns.tolist()
        ),
        hide_index=False
    )

# =============================================================================
# Seleção de período
# =============================================================================

min_date_val = returns_df.index.min().date()
max_date_val = returns_df.index.max().date()

if 'start_date_picker' not in st.session_state:
    st.session_state['start_date_picker'] = min_date_val
if 'end_date_picker' not in st.session_state:
    st.session_state['end_date_picker'] = max_date_val

cols_date = st.columns(2)
with cols_date[0]:
    start_date_input = st.date_input(
        "Data Inicial",
        format="DD/MM/YYYY",
        min_value=min_date_val,
        max_value=max_date_val,
        key='start_date_picker'
    )
with cols_date[1]:
    end_date_input = st.date_input(
        "Data Final",
        format="DD/MM/YYYY",
        min_value=min_date_val,
        max_value=max_date_val,
        key='end_date_picker'
    )

if start_date_input > end_date_input:
    st.warning("Data inicial deve ser anterior à data final.")
    st.stop()

start_ts = pd.to_datetime(start_date_input)
end_ts = pd.to_datetime(end_date_input)

mask = (returns_df.index >= start_ts) & (returns_df.index <= end_ts)
returns_period = returns_df[mask]
cumulative_period = (1 + returns_period).cumprod() - 1

# =============================================================================
# Performance Acumulada + Drawdown
# =============================================================================

col_charts = st.columns(2)
with col_charts[0]:
    hct.streamlit_highcharts(create_chart(
        data=cumulative_period * 100,
        columns=["Carteira", "Ibovespa", "SMLL", "CDI"],
        names=["Carteira", "Ibovespa", "SMLL", "CDI"],
        chart_type='line',
        title="Performance Acumulada",
        y_axis_title="Retorno (%)",
        decimal_precision=2
    ))

with col_charts[1]:
    dd_df = pd.DataFrame({
        'Carteira': calculate_drawdown((1 + returns_period['Carteira']).cumprod()) * 100,
        'Ibovespa': calculate_drawdown((1 + returns_period['Ibovespa']).cumprod()) * 100,
    })
    hct.streamlit_highcharts(create_chart(
        data=dd_df,
        columns=['Carteira', 'Ibovespa'],
        names=['Carteira', 'Ibovespa'],
        chart_type='area',
        title="Drawdown",
        y_axis_title="Drawdown (%)",
        decimal_precision=2
    ))

# =============================================================================
# Retorno Mensal
# =============================================================================

st.markdown("#### Retorno Mensal — Carteira (%)")
monthly_table = get_monthly_returns_table(returns_df['Carteira'])
performance_table = get_performance_table(cumulative_period.add(1)).set_index('index')

styled_monthly = (
    monthly_table.style
    .map(color_returns_cell)
    .format("{:.1f}%", na_rep="—")
)
st.dataframe(styled_monthly, width="stretch")

st.dataframe(
    style_table(
        performance_table,
        numeric_cols_format_as_float=list(performance_table.columns),
        highlight_quartile=list(performance_table.columns)
        ),
    width="stretch"
)

# =============================================================================
# Retorno Diário (só materializa se solicitado)
# =============================================================================

show_daily = st.checkbox("Mostrar retorno diário", value=False)
if show_daily:
    hct.streamlit_highcharts(create_chart(
        data=returns_period * 10000,
        columns=["Carteira", "Ibovespa"],
        names=["Carteira", "Ibovespa"],
        chart_type='column',
        title="Retorno Diário",
        y_axis_title="Retorno (bps)",
        decimal_precision=0
    ))

# =============================================================================
# Aderência · Carteiras Investidas
# =============================================================================

st.divider()
st.markdown("### Aderência · Carteiras Investidas")
st.caption(
    "TWR diário ponderado por saldo da sleeve de ações/BDRs, com pesos de t−1. "
    "Comparado à carteira-modelo RVQM na mesma metodologia."
)

for key in (
    "rvqm_adherence_raw",
    "rvqm_adherence_raw_key",
    "rvqm_adherence_result",
    "rvqm_adherence_result_key",
):
    st.session_state.setdefault(key, None)

# Lazy: clientes RVQM só quando a seção de aderência é montada (após o bloco da estratégia).
try:
    portfolios_rvqm = load_portfolios_rvqm()
    portfolio_options = sorted(portfolios_rvqm["Portfolio"].dropna().unique().tolist())
except Exception as e:
    st.error(f"Erro ao carregar clientes RVQM: {e}")
    portfolio_options = []

adherence_cols = st.columns([3, 1])
with adherence_cols[0]:
    selected_portfolios = st.multiselect(
        "Carteiras",
        options=portfolio_options,
        default=portfolio_options[:1] if portfolio_options else [],
        key="rvqm_adherence_selected",
    )
with adherence_cols[1]:
    st.write("")
    st.write("")
    btn_adherence = st.button("Calcular aderência", type="primary")

adherence_key = (
    tuple(sorted(selected_portfolios)),
    pd.Timestamp(start_ts),
    pd.Timestamp(end_ts),
)


def _raw_covers_period(raw_key, portfolios: tuple, start: pd.Timestamp, end: pd.Timestamp) -> bool:
    """True se o raw em cache já cobre carteiras + intervalo pedido (permite só fatiar)."""
    if raw_key is None:
        return False
    cached_ports, cached_start, cached_end = raw_key
    return (
        cached_ports == portfolios
        and pd.Timestamp(cached_start) <= start
        and pd.Timestamp(cached_end) >= end
    )


def _slice_raw_hist(raw_hist: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if raw_hist is None or raw_hist.empty:
        return raw_hist
    date_col = "date" if "date" in raw_hist.columns else None
    if date_col is None:
        return raw_hist
    dates = pd.to_datetime(raw_hist[date_col])
    return raw_hist.loc[(dates >= start) & (dates <= end)].copy()


# Recalcula a partir do raw em cache quando só o período muda (sem novo hit no ComDinheiro).
can_reuse_raw = _raw_covers_period(
    st.session_state.rvqm_adherence_raw_key,
    adherence_key[0],
    start_ts,
    end_ts,
)
needs_result_refresh = (
    can_reuse_raw
    and st.session_state.rvqm_adherence_raw is not None
    and st.session_state.rvqm_adherence_result_key != adherence_key
)

if btn_adherence or needs_result_refresh:
    if btn_adherence and not selected_portfolios:
        st.warning("Selecione ao menos uma carteira.")
    elif selected_portfolios:
        need_fetch = not can_reuse_raw
        if need_fetch and btn_adherence:
            with st.spinner("Carregando posições históricas do ComDinheiro...", show_time=True):
                try:
                    raw_hist = load_historical_positions_from_comdinheiro(
                        portfolios=adherence_key[0],
                        start_date=start_ts.strftime("%Y-%m-%d"),
                        end_date=end_ts.strftime("%Y-%m-%d"),
                    )
                    st.session_state.rvqm_adherence_raw = raw_hist
                    st.session_state.rvqm_adherence_raw_key = adherence_key
                except Exception as e:
                    st.session_state.rvqm_adherence_raw = None
                    st.session_state.rvqm_adherence_raw_key = None
                    st.session_state.rvqm_adherence_result = None
                    st.session_state.rvqm_adherence_result_key = None
                    st.error(f"Erro ao carregar posições históricas: {e}")

        raw_hist = st.session_state.rvqm_adherence_raw
        should_process = raw_hist is not None and (
            needs_result_refresh
            or (
                btn_adherence
                and st.session_state.rvqm_adherence_raw_key == adherence_key
            )
        )
        if should_process and not raw_hist.empty:
            raw_sliced = _slice_raw_hist(raw_hist, start_ts, end_ts)
            with st.spinner("Calculando aderência..."):
                try:
                    payload = build_adherence_payload(
                        raw_hist=raw_sliced,
                        prices=prices,
                        strategy_weights=weights_df,
                        strategy_returns=returns_df["Carteira"],
                        start_ts=start_ts,
                        end_ts=end_ts,
                    )
                    st.session_state.rvqm_adherence_result = payload
                    st.session_state.rvqm_adherence_result_key = adherence_key
                except Exception as e:
                    st.session_state.rvqm_adherence_result = None
                    st.session_state.rvqm_adherence_result_key = None
                    st.error(f"Erro ao calcular aderência: {e}")
        elif should_process and raw_hist.empty:
            st.session_state.rvqm_adherence_result = {"status": "empty_raw"}
            st.session_state.rvqm_adherence_result_key = adherence_key

result = st.session_state.rvqm_adherence_result
result_key = st.session_state.rvqm_adherence_result_key
status = (result or {}).get("status")

if result is None:
    st.info("Selecione as carteiras e clique em **Calcular aderência**.")
elif result_key != adherence_key and not can_reuse_raw:
    st.info(
        "Período ou carteiras mudaram e exigem novo download do ComDinheiro. "
        "Clique em **Calcular aderência** para atualizar."
    )
elif status == "empty_raw":
    st.warning("Nenhuma posição histórica retornada para o período/carteiras selecionados.")
elif status == "empty_sleeve":
    st.warning("Nenhuma posição de Ação/BDR identificada após o filtro da sleeve RVQM.")
elif status == "empty_prices":
    st.warning("Não foi possível carregar preços para calcular o TWR das carteiras.")
elif status != "ok":
    st.warning("Não foi possível calcular a aderência.")
else:
    summary = result["summary"]
    strategy_period = result["strategy_period"]
    client_period = result["client_period"]
    client_weights = result["client_weights"]

    if not summary.empty:
        display_summary = summary.copy()
        display_summary["excess_return"] = display_summary["excess_return"] * 100
        display_summary["tracking_error"] = display_summary["tracking_error"] * 100
        display_summary["correlation"] = display_summary["correlation"] * 100
        display_summary["hit_ratio"] = display_summary["hit_ratio"] * 100
        display_summary["active_share"] = display_summary["active_share"] * 100
        display_summary = display_summary.rename(
            columns={
                "excess_return": "Excess Return (%)",
                "tracking_error": "Tracking Error (% a.a.)",
                "correlation": "Correlação (%)",
                "hit_ratio": "Hit Ratio (%)",
                "active_share": "Active Share (%)",
                "obs": "Obs.",
            }
        )

        st.dataframe(
            style_table(
                display_summary,
                numeric_cols_format_as_float=[
                    "Excess Return (%)",
                    "Tracking Error (% a.a.)",
                    "Correlação (%)",
                    "Hit Ratio (%)",
                    "Active Share (%)",
                ],
                numeric_cols_format_as_int=["Obs."],
            ),
            width="stretch",
        )

    row_1 = st.columns(2)
    with row_1[0]:
        cumulative_adherence = pd.DataFrame({"Estratégia RVQM": strategy_period})
        for name, rets in client_period.items():
            cumulative_adherence[name] = rets.reindex(cumulative_adherence.index)
        cumulative_adherence = cumulative_adherence.dropna(how="all")
        cumulative_adherence = (1 + cumulative_adherence.fillna(0)).cumprod() - 1

        chart_cols = list(cumulative_adherence.columns)
        hct.streamlit_highcharts(
            create_chart(
                data=cumulative_adherence * 100,
                columns=chart_cols,
                names=chart_cols,
                chart_type="line",
                title="Performance Acumulada - Estratégia vs Carteiras",
                y_axis_title="Retorno (%)",
                decimal_precision=2,
            )
        )

    with row_1[1]:
        excess_df = pd.DataFrame(
            {
                name: (
                    1
                    + rets.reindex(strategy_period.index)
                    .sub(strategy_period)
                    .fillna(0)
                ).cumprod()
                - 1
                for name, rets in client_period.items()
            }
        )
        if not excess_df.empty:
            hct.streamlit_highcharts(
                create_chart(
                    data=excess_df * 100,
                    columns=list(excess_df.columns),
                    names=list(excess_df.columns),
                    chart_type="line",
                    title="Excess Return Acumulado vs Estratégia",
                    y_axis_title="Excess Return (%)",
                    decimal_precision=2,
                )
            )

    show_sleeve = st.checkbox("Mostrar detalhe da sleeve (última data)", value=False)
    if show_sleeve:
        latest_rows = []
        for carteira, weights in client_weights.items():
            if weights.empty:
                continue
            last_date = weights.index.max()
            last_w = weights.loc[last_date]
            last_w = last_w[last_w > 0].sort_values(ascending=False)
            for ticker, weight in last_w.items():
                latest_rows.append(
                    {
                        "Carteira": carteira,
                        "Data": last_date,
                        "Ticker": ticker,
                        "Peso (%)": weight * 100,
                    }
                )
        if latest_rows:
            latest_df = pd.DataFrame(latest_rows)
            st.dataframe(
                style_table(
                    latest_df,
                    date_cols=["Data"],
                    percent_cols=["Peso (%)"],
                ),
                hide_index=True,
                width="stretch",
            )
