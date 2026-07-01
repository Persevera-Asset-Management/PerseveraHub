import streamlit as st
import pandas as pd
from datetime import datetime

from utils.chart_helpers import create_chart, render_chart

from persevera_tools.data import get_securities_by_exchange, get_descriptors


DESCRIPTOR_LABELS = {
    "price_to_earnings_fwd": "P/E Fwd",
    "earnings_per_share_fwd": "EPS Fwd",
    "ev_to_ebitda_fwd": "EV/EBITDA Fwd",
    "ebitda_fwd": "EBITDA Fwd",
}

VALUATION_DESCRIPTORS = list(DESCRIPTOR_LABELS.keys())
MULTIPLE_DESCRIPTORS = ["price_to_earnings_fwd", "ev_to_ebitda_fwd"]

st.title("Valuation")


@st.cache_data(ttl=3600)
def load_securities_list():
    return sorted(get_securities_by_exchange(exchange="BZ").values())


securities_list = load_securities_list()


@st.cache_data(ttl=3600)
def load_data(tickers, start_date_str, descriptors):
    ticker_list = [tickers] if isinstance(tickers, str) else list(tickers)
    descriptor_list = [descriptors] if isinstance(descriptors, str) else list(descriptors)
    return get_descriptors(
        tickers=ticker_list,
        start_date=start_date_str,
        descriptors=descriptor_list,
    )


def to_single_stock_dataframe(df):
    if isinstance(df, pd.Series):
        df = df.to_frame()
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel("ticker", axis=1)
    available = [col for col in VALUATION_DESCRIPTORS if col in df.columns]
    return df[available] if available else pd.DataFrame()


def to_comparative_dataframe(df, descriptor):
    if isinstance(df, pd.Series):
        df = df.to_frame()
    if isinstance(df.columns, pd.MultiIndex):
        if "descriptor" in df.columns.names:
            result = df.xs(descriptor, level="descriptor", axis=1)
        else:
            df_swapped = df.swaplevel(0, 1, axis=1)
            result = df_swapped[descriptor] if descriptor in df_swapped.columns.get_level_values(0) else pd.DataFrame()
    elif descriptor in df.columns:
        result = df[[descriptor]]
    else:
        return pd.DataFrame()

    if isinstance(result, pd.Series):
        result = result.to_frame()
    return result


def apply_smoothing(df, use_moving_average, window):
    if not use_moving_average:
        return df
    return df.rolling(window=window, min_periods=1).mean()


def series_suffix(use_moving_average, window):
    return f" · MM {window}d" if use_moving_average else ""


with st.sidebar:
    st.header("Configurações")
    view_mode = st.radio("Modo", ["Ativo único", "Comparativo"], horizontal=True)
    start_date = st.date_input(
        "Data Inicial",
        min_value=datetime(2010, 1, 1),
        value=datetime(2015, 1, 1),
        format="DD/MM/YYYY",
    )
    start_date_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")

    st.subheader("Série")
    use_moving_average = st.toggle("Média móvel", value=False)
    ma_window = None
    if use_moving_average:
        ma_window = st.number_input(
            "Janela (dias)",
            min_value=2,
            max_value=252,
            value=21,
            step=1,
        )

    if view_mode == "Ativo único":
        selected_stock = st.selectbox("Selecione um ativo", options=[""] + securities_list)
        selected_stocks = []
    else:
        selected_stock = ""
        selected_stocks = st.multiselect("Selecione os ativos", options=securities_list)

if view_mode == "Ativo único":
    if not selected_stock:
        st.info("Selecione um ativo para visualizar as métricas de valuation.")
        st.stop()
    tickers = selected_stock
    descriptors = VALUATION_DESCRIPTORS
else:
    if len(selected_stocks) < 2:
        st.info("Selecione pelo menos dois ativos para o comparativo.")
        st.stop()
    tickers = tuple(selected_stocks)
    descriptors = MULTIPLE_DESCRIPTORS

with st.spinner("Carregando dados...", show_time=True):
    try:
        df = load_data(tickers, start_date_str, tuple(descriptors))
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

if df is None or (isinstance(df, pd.DataFrame) and df.empty):
    st.warning("Não foi possível carregar os dados.")
    st.stop()

latest_date = pd.to_datetime(df.index.max()).date()
st.markdown(f"Dado mais recente: `{latest_date}`")

suffix = series_suffix(use_moving_average, ma_window)

if view_mode == "Ativo único":
    stock_data = apply_smoothing(
        to_single_stock_dataframe(df).dropna(how="all"),
        use_moving_average,
        ma_window,
    )

    if stock_data.empty:
        st.warning(f"Sem dados de valuation para {selected_stock} no período selecionado.")
        st.stop()

    col_earnings, col_ebitda = st.columns(2)

    with col_earnings:
        earnings_data = stock_data[["price_to_earnings_fwd", "earnings_per_share_fwd"]].dropna(how="all")
        if earnings_data.empty:
            st.warning(f"Sem dados de earnings para {selected_stock}.")
        else:
            render_chart(
                create_chart(
                    data=earnings_data,
                    columns=(["price_to_earnings_fwd"], ["earnings_per_share_fwd"]),
                    names=(
                        [DESCRIPTOR_LABELS["price_to_earnings_fwd"]],
                        [DESCRIPTOR_LABELS["earnings_per_share_fwd"]],
                    ),
                    chart_type="dual_axis_line",
                    title=f"Earnings · {selected_stock}{suffix}",
                    y_axis_title=(
                        DESCRIPTOR_LABELS["price_to_earnings_fwd"],
                        DESCRIPTOR_LABELS["earnings_per_share_fwd"],
                    ),
                    x_axis_title="Data",
                    decimal_precision=2,
                    enable_fullscreen_on_dblclick=True,
                ),
                key="valuation_earnings",
            )

    with col_ebitda:
        ebitda_data = stock_data[["ev_to_ebitda_fwd", "ebitda_fwd"]].dropna(how="all")
        if ebitda_data.empty:
            st.warning(f"Sem dados de EBITDA para {selected_stock}.")
        else:
            render_chart(
                create_chart(
                    data=ebitda_data,
                    columns=(["ev_to_ebitda_fwd"], ["ebitda_fwd"]),
                    names=(
                        [DESCRIPTOR_LABELS["ev_to_ebitda_fwd"]],
                        [DESCRIPTOR_LABELS["ebitda_fwd"]],
                    ),
                    chart_type="dual_axis_line",
                    title=f"EBITDA · {selected_stock}{suffix}",
                    y_axis_title=(
                        DESCRIPTOR_LABELS["ev_to_ebitda_fwd"],
                        DESCRIPTOR_LABELS["ebitda_fwd"],
                    ),
                    x_axis_title="Data",
                    decimal_precision=2,
                    enable_fullscreen_on_dblclick=True,
                ),
                key="valuation_ebitda",
            )

else:
    col_pe, col_ev = st.columns(2)
    chart_specs = [
        ("price_to_earnings_fwd", col_pe, "valuation_compare_pe"),
        ("ev_to_ebitda_fwd", col_ev, "valuation_compare_ev_ebitda"),
    ]

    has_data = False
    for descriptor, column, chart_key in chart_specs:
        compare_data = apply_smoothing(
            to_comparative_dataframe(df, descriptor).dropna(how="all"),
            use_moving_average,
            ma_window,
        )
        with column:
            if compare_data.empty:
                st.warning(f"Sem dados de {DESCRIPTOR_LABELS[descriptor]} para os ativos selecionados.")
            else:
                has_data = True
                render_chart(
                    create_chart(
                        data=compare_data,
                        columns=list(compare_data.columns),
                        names=list(compare_data.columns),
                        chart_type="line",
                        title=f"{DESCRIPTOR_LABELS[descriptor]}{suffix}",
                        y_axis_title=DESCRIPTOR_LABELS[descriptor],
                        x_axis_title="Data",
                        decimal_precision=2,
                        enable_fullscreen_on_dblclick=True,
                    ),
                    key=chart_key,
                )

    if not has_data:
        st.stop()
