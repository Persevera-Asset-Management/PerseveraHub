import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
from datetime import datetime

from utils.chart_helpers import create_chart

from persevera_tools.data import get_securities_by_exchange, get_descriptors


DESCRIPTOR_LABELS = {
    "price_to_earnings_fwd": "P/E Fwd",
    "earnings_per_share_fwd": "EPS Fwd",
    "ev_to_ebitda_fwd": "EV/EBITDA Fwd",
    "ebitda_fwd": "EBITDA Fwd",
}

VALUATION_DESCRIPTORS = list(DESCRIPTOR_LABELS.keys())

st.title("Valuation")

securities = [""] + sorted(get_securities_by_exchange(exchange="BZ").values())

with st.sidebar:
    st.header("Configurações")
    selected_stock = st.selectbox("Selecione um ativo", options=securities)
    start_date = st.date_input("Data Inicial", min_value=datetime(2010, 1, 1), value=datetime(2015, 1, 1), format="DD/MM/YYYY")
    start_date = pd.to_datetime(start_date)

@st.cache_data(ttl=3600)
def load_data(code, start_date):
    try:
        return get_descriptors(
            tickers=code,
            start_date=start_date.strftime("%Y-%m-%d"),
            descriptors=VALUATION_DESCRIPTORS,
        )
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

def to_stock_dataframe(df):
    if isinstance(df, pd.Series):
        df = df.to_frame()
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel("ticker", axis=1)
    available = [col for col in VALUATION_DESCRIPTORS if col in df.columns]
    return df[available] if available else pd.DataFrame()

if not selected_stock:
    st.info("Selecione um ativo para visualizar as métricas de valuation.")
    st.stop()

with st.spinner("Carregando dados...", show_time=True):
    df = load_data(selected_stock, start_date=start_date)

if df.empty:
    st.warning("Não foi possível carregar os dados.")
    st.stop()

stock_data = to_stock_dataframe(df).dropna(how="all")

if stock_data.empty:
    st.warning(f"Sem dados de valuation para {selected_stock} no período selecionado.")
    st.stop()

col_earnings, col_ebitda = st.columns(2)

with col_earnings:
    earnings_data = stock_data[["price_to_earnings_fwd", "earnings_per_share_fwd"]].dropna(how="all")
    if earnings_data.empty:
        st.warning(f"Sem dados de earnings para {selected_stock}.")
    else:
        hct.streamlit_highcharts(
            create_chart(
                data=earnings_data,
                columns=(["price_to_earnings_fwd"], ["earnings_per_share_fwd"]),
                names=(
                    [DESCRIPTOR_LABELS["price_to_earnings_fwd"]],
                    [DESCRIPTOR_LABELS["earnings_per_share_fwd"]],
                ),
                chart_type="dual_axis_line",
                title=f"Earnings · {selected_stock}",
                y_axis_title=(
                    DESCRIPTOR_LABELS["price_to_earnings_fwd"],
                    DESCRIPTOR_LABELS["earnings_per_share_fwd"],
                ),
                x_axis_title="Data",
                decimal_precision=2,
            ),
            key="valuation_earnings",
        )

with col_ebitda:
    ebitda_data = stock_data[["ev_to_ebitda_fwd", "ebitda_fwd"]].dropna(how="all")
    if ebitda_data.empty:
        st.warning(f"Sem dados de EBITDA para {selected_stock}.")
    else:
        hct.streamlit_highcharts(
            create_chart(
                data=ebitda_data,
                columns=(["ev_to_ebitda_fwd"], ["ebitda_fwd"]),
                names=(
                    [DESCRIPTOR_LABELS["ev_to_ebitda_fwd"]],
                    [DESCRIPTOR_LABELS["ebitda_fwd"]],
                ),
                chart_type="dual_axis_line",
                title=f"EBITDA · {selected_stock}",
                y_axis_title=(
                    DESCRIPTOR_LABELS["ev_to_ebitda_fwd"],
                    DESCRIPTOR_LABELS["ebitda_fwd"],
                ),
                x_axis_title="Data",
                decimal_precision=2,
            ),
            key="valuation_ebitda",
        )
