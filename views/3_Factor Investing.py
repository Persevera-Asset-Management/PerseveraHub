import streamlit as st
import pandas as pd
from datetime import datetime

import streamlit_highcharts as hct

from utils.table import style_table
from utils.chart_helpers import create_chart

from persevera_tools.data import get_series
from persevera_tools.quant_research.factor_investing import (
    BacktestConfig,
    get_factor_options,
    run_backtest,
)
from persevera_tools.quant_research.factor_investing.result import build_summary

STYLE_OPTIONS = ["Momentum", "Value", "Quality", "Risk", "Liquidity", "Custom"]

CONSTRUCTION_LABELS = {
    "Long Only": "long_only",
    "Long/Short": "long_short",
}

SELECTION_LABELS = {
    "Quantile": "quantile",
    "Top N": "top_n",
}

REBALANCE_OPTIONS = {
    "Mensal (BME)": "BME",
    "Semanal (W-FRI)": "W-FRI",
    "Trimestral (BQE)": "BQE",
}

BENCHMARK_OPTIONS: dict[str, str] = {
    "IBOV": "br_ibovespa",
    "CDI": "br_cdi_index",
}


@st.cache_data(ttl=3600)
def _load_factor_options() -> dict[str, str]:
    """Alias -> Name (mnemonic)."""
    return get_factor_options()


@st.cache_data(ttl=3600)
def _load_benchmark_prices(tickers: tuple[str, ...], start_date: str) -> pd.DataFrame:
    """Load close prices; normalizes single-ticker Series to a named DataFrame."""
    if not tickers:
        return pd.DataFrame()
    try:
        data = get_series(list(tickers), start_date=start_date, field=["close"])
        if isinstance(data, pd.Series):
            # get_series returns a Series named "close" when only one code is requested
            return data.to_frame(name=tickers[0])
        if isinstance(data.columns, pd.MultiIndex):
            data = data.copy()
            data.columns = data.columns.get_level_values(0)
        return data
    except Exception:
        return pd.DataFrame()


st.title("Factor Investing")

with st.sidebar:
    st.header("Parâmetros")

    start_date = st.date_input(
        "Data Inicial",
        min_value=datetime(2000, 1, 1),
        max_value=datetime.today(),
        value=datetime(2019, 12, 31),
        format="DD/MM/YYYY",
    )
    end_date = st.date_input(
        "Data Final",
        min_value=datetime(2000, 1, 1),
        max_value=datetime.today(),
        value=datetime.today(),
        format="DD/MM/YYYY",
    )

    style = st.selectbox("Estilo", options=STYLE_OPTIONS, index=0)

    selected_aliases: list[str] = []
    if style == "Custom":
        factor_options = _load_factor_options()
        selected_aliases = st.multiselect(
            "Métricas",
            options=list(factor_options.keys()),
            default=[],
            help="Selecione os fatores (mnemonics) que compõem a estratégia customizada.",
        )
    else:
        factor_options = {}

    construction_label = st.selectbox(
        "Construção",
        options=list(CONSTRUCTION_LABELS.keys()),
        index=0,
    )
    construction = CONSTRUCTION_LABELS[construction_label]

    selection_label = st.selectbox(
        "Modo de Seleção",
        options=list(SELECTION_LABELS.keys()),
        index=0,
    )
    selection_mode = SELECTION_LABELS[selection_label]

    if selection_mode == "quantile":
        quantile_pct = st.slider(
            "Quantile (por cauda)",
            min_value=5,
            max_value=50,
            value=20,
            step=5,
            format="%d%%",
            help="Fração do universo selecionada em cada cauda (ex.: 20% = quintis).",
        )
        quantile = quantile_pct / 100
        top_n = None
    else:
        quantile = 0.2
        top_n = st.number_input("Top N (por cauda)", min_value=1, max_value=200, value=20, step=1)

    rebalance_label = st.selectbox(
        "Rebalanceamento",
        options=list(REBALANCE_OPTIONS.keys()),
        index=0,
    )
    rebalance_freq = REBALANCE_OPTIONS[rebalance_label]

    adtv_min = st.number_input(
        "ADTV Mínimo (21d)",
        min_value=0.0,
        value=8_000_000.0,
        step=500_000.0,
        format="%.0f",
    )

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
        default=["IBOV"],
    )

    run_clicked = st.button("Rodar Backtest", type="primary", width="stretch")


def _summary_to_series(name: str, summary: dict) -> pd.Series:
    return pd.Series(
        {
            "Retorno Total": summary.get("total_return", float("nan")) * 100,
            "Retorno Anualizado": summary.get("annualized_return", float("nan")) * 100,
            "Volatilidade Anual": summary.get("annualized_volatility", float("nan")) * 100,
            "Sharpe Ratio": summary.get("sharpe", float("nan")),
            "Máx. Drawdown": summary.get("max_drawdown", float("nan")) * 100,
            "Observações": summary.get("n_obs", 0),
        },
        name=name,
    )


def _holdings_for_date(
    weights: pd.DataFrame,
    scores: pd.DataFrame,
    rebalance_date: pd.Timestamp,
) -> pd.DataFrame:
    """Build ticker / weight% / score table for a single rebalance date."""
    if weights is None or weights.empty or rebalance_date not in weights.index:
        return pd.DataFrame(columns=["Ticker", "Peso (%)", "Score"])

    w = weights.loc[rebalance_date]
    w = w[w.notna() & (w != 0.0)].astype(float)
    if w.empty:
        return pd.DataFrame(columns=["Ticker", "Peso (%)", "Score"])

    holdings = w.rename("Peso").to_frame()
    holdings["Peso (%)"] = holdings["Peso"] * 100

    if scores is not None and not scores.empty and rebalance_date in scores.index:
        s = scores.loc[rebalance_date]
        holdings["Score"] = s.reindex(holdings.index).astype(float)
    else:
        holdings["Score"] = float("nan")

    holdings = holdings.reset_index(names="Ticker")
    holdings = holdings.sort_values("Peso (%)", ascending=False, key=abs)
    return holdings[["Ticker", "Peso (%)", "Score"]].reset_index(drop=True)


def _weights_history(weights: pd.DataFrame) -> pd.DataFrame:
    """Long-format history of non-zero weights across rebalances."""
    if weights is None or weights.empty:
        return pd.DataFrame(columns=["Data", "Ticker", "Peso (%)"])

    long = (
        weights.reset_index(names="Data")
        .melt(id_vars="Data", var_name="Ticker", value_name="Peso")
    )
    long = long[long["Peso"].notna() & (long["Peso"] != 0.0)].copy()
    long["Peso (%)"] = long["Peso"].astype(float) * 100
    long["Data"] = pd.to_datetime(long["Data"]).dt.strftime("%Y-%m-%d")
    long = long.assign(_abs=long["Peso (%)"].abs())
    long = long.sort_values(["Data", "_abs"], ascending=[True, False])
    return long[["Data", "Ticker", "Peso (%)"]].reset_index(drop=True)


def _benchmark_indexed_nav(
    prices: pd.Series,
    index: pd.DatetimeIndex,
) -> pd.Series | None:
    """Align benchmark prices to strategy index and normalize to base 100."""
    raw = prices.reindex(index).ffill()
    first = raw.first_valid_index()
    if first is None:
        return None
    return (raw / raw.loc[first]) * 100


is_custom = style == "Custom"
custom_components = (
    [factor_options[alias] for alias in selected_aliases if alias in factor_options]
    if is_custom
    else None
)

if run_clicked:
    if end_date < start_date:
        st.error("A data final não pode ser anterior à data inicial.")
        st.stop()

    if is_custom and not custom_components:
        st.error("Selecione ao menos uma métrica para o estilo Custom.")
        st.stop()

    config = BacktestConfig(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        style=None if is_custom else style,
        components=custom_components,
        construction=construction,
        selection_mode=selection_mode,
        quantile=float(quantile),
        top_n=int(top_n) if top_n is not None else None,
        rebalance_freq=rebalance_freq,
        adtv_min=float(adtv_min),
        risk_free_rate=float(risk_free_rate),
    )

    with st.spinner("Rodando backtest fatorial...", show_time=True):
        try:
            result = run_backtest(config)
        except Exception as e:
            st.error(f"Erro ao rodar o backtest: {e}")
            st.stop()

    factor_label = (
        f"Custom ({len(custom_components)})" if is_custom else style
    )
    st.session_state["factor_bt_result"] = result
    st.session_state["factor_bt_label"] = (
        f"{factor_label} · {construction_label} · {selection_label} · {rebalance_label}"
    )


result = st.session_state.get("factor_bt_result")
if result is None:
    st.info("Configure os parâmetros na barra lateral e clique em **Rodar Backtest**.")
    st.stop()

label = st.session_state.get("factor_bt_label", "Estratégia")
st.caption(label)
if result.components:
    st.caption("**Fatores**: " + ", ".join(result.components))

nav = result.nav.dropna()
if nav.empty:
    st.warning("O backtest não retornou NAV válido para o período selecionado.")
    st.stop()

# Normaliza para base 100 (visualização)
nav_indexed = (nav / nav.iloc[0]) * 100
chart_df = nav_indexed.to_frame(name="Estratégia")
stats_series = [_summary_to_series("Estratégia", result.summary or {})]

# Benchmarks (podem mudar sem re-rodar o backtest)
if selected_benchmarks:
    bm_tickers = tuple(BENCHMARK_OPTIONS[name] for name in selected_benchmarks)
    bm_start = nav.index.min().strftime("%Y-%m-%d")
    with st.spinner("Carregando benchmarks...", show_time=True):
        bm_prices = _load_benchmark_prices(bm_tickers, bm_start)

    for bm_label in selected_benchmarks:
        bm_ticker = BENCHMARK_OPTIONS[bm_label]
        if bm_prices.empty or bm_ticker not in bm_prices.columns:
            st.warning(f"Benchmark '{bm_label}' não encontrado nos dados.")
            continue

        bm_indexed = _benchmark_indexed_nav(bm_prices[bm_ticker], chart_df.index)
        if bm_indexed is None:
            st.warning(f"Benchmark '{bm_label}' sem dados no período.")
            continue

        chart_df[bm_label] = bm_indexed
        bm_raw = bm_prices[bm_ticker].reindex(nav.index).ffill().dropna()
        stats_series.append(
            _summary_to_series(
                bm_label,
                build_summary(bm_raw, risk_free_rate=float(risk_free_rate)),
            )
        )

stats_df = pd.DataFrame(stats_series)

row_1 = st.columns([1, 2, 2])
with row_1[0]:
    st.dataframe(
        style_table(
            stats_df.T,
            numeric_cols_format_as_float=list(stats_df.T.columns),
        ),
        width="stretch",
    )

with row_1[1]:
    chart = create_chart(
        data=chart_df,
        columns=list(chart_df.columns),
        names=list(chart_df.columns),
        chart_type="line",
        title="Equity Curve",
        y_axis_title="Índice (base 100)",
    )
    hct.streamlit_highcharts(chart, key="factor_equity_curve")

with row_1[2]:
    drawdown_df = pd.DataFrame(index=chart_df.index)
    for col in chart_df.columns:
        cumulative = chart_df[col]
        running_max = cumulative.expanding().max()
        drawdown_df[col] = (cumulative - running_max) / running_max * 100

    chart_drawdown = create_chart(
        data=drawdown_df,
        columns=list(drawdown_df.columns),
        names=list(drawdown_df.columns),
        chart_type="area",
        title="Drawdown",
        y_axis_title="Drawdown (%)",
    )
    hct.streamlit_highcharts(chart_drawdown, key="factor_drawdown")

st.markdown("##### Holdings")
weights = result.weights
scores = result.scores

if weights is None or weights.empty:
    st.info("Nenhuma carteira de rebalanceamento disponível neste backtest.")
else:
    rebalance_dates = list(pd.DatetimeIndex(weights.index).sort_values())
    date_labels = [d.strftime("%Y-%m-%d") for d in rebalance_dates]
    label_to_date = dict(zip(date_labels, rebalance_dates))

    tab_posicao, tab_historico = st.tabs(["Posição", "Histórico"])

    with tab_posicao:
        selected_label = st.selectbox(
            "Data de rebalanceamento",
            options=date_labels,
            index=len(date_labels) - 1,
            key="factor_bt_rebalance_date",
            width=300,
        )
        selected_date = label_to_date[selected_label]
        holdings_df = _holdings_for_date(weights, scores, selected_date)

        if holdings_df.empty:
            st.warning("Sem posições com peso diferente de zero nesta data.")
        else:
            long_sum = holdings_df.loc[holdings_df["Peso (%)"] > 0, "Peso (%)"].sum()
            short_sum = holdings_df.loc[holdings_df["Peso (%)"] < 0, "Peso (%)"].sum()
            st.caption(
                f"{len(holdings_df)} ativos · "
                f"Long {long_sum:.1f}% · Short {short_sum:.1f}% · "
                f"Net {long_sum + short_sum:.1f}%"
            )
            st.dataframe(
                style_table(
                    holdings_df,
                    percent_cols=["Peso (%)"],
                    numeric_cols_format_as_float=["Score"],
                ),
                width="stretch",
                hide_index=True,
            )

    with tab_historico:
        history_df = _weights_history(weights)
        n_rebals = len(rebalance_dates)
        st.caption(f"{n_rebals} rebalanceamentos · {len(history_df)} posições (não nulas)")
        if history_df.empty:
            st.warning("Histórico de pesos vazio.")
        else:
            st.dataframe(
                style_table(
                    history_df,
                    percent_cols=["Peso (%)"],
                ),
                width="stretch",
                hide_index=True,
                height=400,
            )
