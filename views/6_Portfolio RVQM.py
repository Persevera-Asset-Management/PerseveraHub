import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from utils.chart_helpers import create_chart
from utils.table import style_table, get_performance_table
from utils.tearsheet import render_tearsheet

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
    strategy_weights_by_tipo: dict[str, pd.DataFrame],
    strategy_returns_by_tipo: dict[str, pd.Series],
    portfolio_tipo_map: dict[str, str],
    start_ts,
    end_ts,
) -> dict:
    """Processa raw ComDinheiro → pesos, retornos e summary (cacheável).

    Cada carteira é comparada à carteira-modelo aderida (ex.: RVQM, MAGO).
    """
    RVQM_INSTRUMENTS = ("Ação", "BDR")
    hist_positions = prepare_comdinheiro_historical_positions_df(raw_hist)
    equity_positions = filter_equity_sleeve(hist_positions, load_assets(RVQM_INSTRUMENTS))
    if equity_positions.empty:
        return {"status": "empty_sleeve"}

    client_weights = positions_to_weights(equity_positions)
    client_tickers = sorted(
        {ticker for weights in client_weights.values() for ticker in weights.columns}
    )
    strategy_starts = [
        weights.index.min()
        for weights in strategy_weights_by_tipo.values()
        if not weights.empty
    ]
    if not strategy_starts:
        return {"status": "empty_prices"}
    price_start = min(min(strategy_starts), equity_positions["Data"].min())
    adherence_prices = merge_prices(prices, client_tickers, start_date=price_start)
    if adherence_prices.empty:
        return {"status": "empty_prices"}

    client_returns = {
        name: calculate_portfolio_twr(weights, adherence_prices, lag_weights=True)
        for name, weights in client_weights.items()
    }

    strategy_by_portfolio: dict[str, str] = {}
    strategy_returns_by_portfolio: dict[str, pd.Series] = {}
    strategy_weights_by_portfolio: dict[str, pd.DataFrame] = {}
    strategy_period_by_tipo: dict[str, pd.Series] = {}

    for name in client_returns:
        tipo = portfolio_tipo_map.get(name)
        if not tipo or tipo not in strategy_returns_by_tipo:
            return {"status": "missing_strategy", "portfolio": name, "tipo": tipo}
        strategy_by_portfolio[name] = tipo
        strat_rets = strategy_returns_by_tipo[tipo]
        strategy_returns_by_portfolio[name] = strat_rets.loc[
            (strat_rets.index >= start_ts) & (strat_rets.index <= end_ts)
        ]
        strategy_weights_by_portfolio[name] = strategy_weights_by_tipo[tipo]
        if tipo not in strategy_period_by_tipo:
            strategy_period_by_tipo[tipo] = strategy_returns_by_portfolio[name]

    client_period = {
        name: rets.loc[(rets.index >= start_ts) & (rets.index <= end_ts)]
        for name, rets in client_returns.items()
    }
    summary = build_adherence_summary(
        client_period,
        strategy_returns_by_portfolio,
        client_weights,
        strategy_weights_by_portfolio,
        strategy_by_portfolio=strategy_by_portfolio,
    )
    return {
        "status": "ok",
        "client_weights": client_weights,
        "strategy_period_by_tipo": strategy_period_by_tipo,
        "strategy_returns_by_portfolio": strategy_returns_by_portfolio,
        "strategy_by_portfolio": strategy_by_portfolio,
        "client_period": client_period,
        "summary": summary,
    }

# =============================================================================
# Carregamento de dados
# =============================================================================

with st.spinner("Carregando composição da carteira..."):
    equities_all = load_equities_portfolio()
    strategy_options = sorted(
        t for t in equities_all["tipo"].dropna().astype(str).str.strip().unique().tolist() if t
    )
    if not strategy_options:
        st.warning("Nenhuma estratégia disponível na carteira-modelo.")
        st.stop()

default_strategy_idx = strategy_options.index("RVQM") if "RVQM" in strategy_options else 0
with st.sidebar:
    st.header("Estratégia")
    selected_strategy = st.selectbox(
        "Carteira-modelo",
        options=strategy_options,
        index=default_strategy_idx,
        help="Define qual carteira-modelo é exibida na análise de composição e performance.",
    )

equities_portfolio = equities_all[equities_all["tipo"] == selected_strategy].copy()
securities_list = tuple(sorted(equities_all["code"].dropna().unique().tolist()))
data_start = equities_all["date"].min()

if equities_portfolio.empty or len(securities_list) == 0:
    st.warning(f"Nenhum dado disponível para a estratégia {selected_strategy}.")
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
    f"{selected_strategy} &nbsp;·&nbsp; "
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

# Pré-calcula retornos/pesos de todas as estratégias para a aderência por Tipo.
strategy_weights_by_tipo: dict[str, pd.DataFrame] = {}
strategy_returns_by_tipo: dict[str, pd.Series] = {}
for tipo in strategy_options:
    tipo_portfolio = equities_all[equities_all["tipo"] == tipo]
    if tipo_portfolio.empty:
        continue
    tipo_weights = pivot_model_weights(tipo_portfolio).reindex(prices.index).ffill()
    strategy_weights_by_tipo[tipo] = tipo_weights
    strategy_returns_by_tipo[tipo] = calculate_portfolio_twr(
        tipo_weights, prices, lag_weights=True
    )

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
# Seleção de período (sidebar — após load, para min/max válidos)
# =============================================================================

min_date_val = returns_df.index.min().date()
max_date_val = returns_df.index.max().date()

if "start_date_picker" not in st.session_state:
    st.session_state["start_date_picker"] = min_date_val
if "end_date_picker" not in st.session_state:
    st.session_state["end_date_picker"] = max_date_val

# Clamp session values if the available range shrunk (e.g. strategy change).
st.session_state["start_date_picker"] = max(
    min_date_val, min(st.session_state["start_date_picker"], max_date_val)
)
st.session_state["end_date_picker"] = max(
    min_date_val, min(st.session_state["end_date_picker"], max_date_val)
)

with st.sidebar:
    st.header("Período")
    start_date_input = st.date_input(
        "Data Inicial",
        format="DD/MM/YYYY",
        min_value=min_date_val,
        max_value=max_date_val,
        key="start_date_picker",
    )
    end_date_input = st.date_input(
        "Data Final",
        format="DD/MM/YYYY",
        min_value=min_date_val,
        max_value=max_date_val,
        key="end_date_picker",
    )

if start_date_input > end_date_input:
    st.warning("Data inicial deve ser anterior à data final.")
    st.stop()

start_ts = pd.to_datetime(start_date_input)
end_ts = pd.to_datetime(end_date_input)

mask = (returns_df.index >= start_ts) & (returns_df.index <= end_ts)
returns_period = returns_df[mask]

# =============================================================================
# Tearsheet de performance
# =============================================================================

tearsheet_cols = [c for c in ["Carteira", "Ibovespa", "SMLL", "CDI"] if c in returns_period.columns]
tearsheet_out = render_tearsheet(
    key_prefix="rvqm",
    returns=returns_period[tearsheet_cols],
    drawdown_columns=[c for c in ["Carteira", "Ibovespa"] if c in returns_period.columns],
    monthly_column="Carteira",
    show_correlation=True,
    correlation_returns=returns_period[["Carteira", "Ibovespa"]],
)

performance_table = get_performance_table(tearsheet_out["levels"]).set_index("index")
st.dataframe(
    style_table(
        performance_table,
        numeric_cols_format_as_float=list(performance_table.columns),
        highlight_quartile=list(performance_table.columns),
    ),
    width="stretch",
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
    "Cada carteira é comparada automaticamente à carteira-modelo aderida."
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
    portfolio_tipo_map = (
        portfolios_rvqm.dropna(subset=["Portfolio"])
        .assign(Tipo=lambda d: d["Tipo"].astype(str).str.strip())
        .set_index("Portfolio")["Tipo"]
        .to_dict()
    )
    portfolio_options = sorted(portfolios_rvqm["Portfolio"].dropna().unique().tolist())
except Exception as e:
    st.error(f"Erro ao carregar clientes RVQM: {e}")
    portfolios_rvqm = pd.DataFrame()
    portfolio_tipo_map = {}
    portfolio_options = []

adherence_cols = st.columns([3, 1])
with adherence_cols[0]:
    selected_portfolios = st.multiselect(
        "Carteiras",
        options=portfolio_options,
        default=portfolio_options[:1] if portfolio_options else [],
        format_func=lambda p: f"{p} ({portfolio_tipo_map.get(p, '?')})",
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
                        strategy_weights_by_tipo=strategy_weights_by_tipo,
                        strategy_returns_by_tipo=strategy_returns_by_tipo,
                        portfolio_tipo_map=portfolio_tipo_map,
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
elif status == "missing_strategy":
    missing_portfolio = (result or {}).get("portfolio", "?")
    missing_tipo = (result or {}).get("tipo") or "não definido"
    st.warning(
        f"Carteira {missing_portfolio} com carteira-modelo '{missing_tipo}' sem composição correspondente."
    )
elif status != "ok":
    st.warning("Não foi possível calcular a aderência.")
else:
    summary = result["summary"]
    strategy_period_by_tipo = result["strategy_period_by_tipo"]
    strategy_returns_by_portfolio = result["strategy_returns_by_portfolio"]
    client_period = result["client_period"]
    client_weights = result["client_weights"]

    if not summary.empty:
        display_summary = summary.copy()
        display_summary["excess_return"] = display_summary["excess_return"] * 100
        display_summary["tracking_error"] = display_summary["tracking_error"] * 100
        display_summary["correlation"] = display_summary["correlation"] * 100
        display_summary["hit_ratio"] = display_summary["hit_ratio"] * 100
        display_summary["active_share"] = display_summary["active_share"] * 100
        rename_map = {
            "excess_return": "Excess Return (%)",
            "tracking_error": "Tracking Error (% a.a.)",
            "correlation": "Correlação (%)",
            "hit_ratio": "Hit Ratio (%)",
            "active_share": "Active Share (%)",
            "obs": "Obs.",
            "estrategia": "Estratégia",
        }
        display_summary = display_summary.rename(columns=rename_map)

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
        cumulative_adherence = pd.DataFrame(
            {
                f"Estratégia {tipo}": period
                for tipo, period in strategy_period_by_tipo.items()
            }
        )
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
                    + rets.reindex(strategy_returns_by_portfolio[name].index)
                    .sub(strategy_returns_by_portfolio[name])
                    .fillna(0)
                ).cumprod()
                - 1
                for name, rets in client_period.items()
                if name in strategy_returns_by_portfolio
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
