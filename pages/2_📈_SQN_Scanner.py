import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from persevera_tools.data import get_securities_by_exchange, get_descriptors
from persevera_tools.quant_research.metrics import calculate_sqn

from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication

st.set_page_config(
    page_title="SQN Scanner | Persevera",
    page_icon="📈",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("SQN Scanner")

with st.sidebar:
    st.header("Configurações")
    lookback_days = st.slider("Período de Análise (dias)", min_value=30, max_value=720, value=100, step=10)
    min_liquidity = st.number_input("Liquidez Mínima (em milhões)", min_value=0, value=8e6, step=1e6)
    n_periods = st.slider("Número de Períodos", min_value=5, max_value=30, value=10, step=1)

@st.cache_data(ttl=3600)
def load_data(start_date, descriptors_list):
    try:
        codes = get_securities_by_exchange(exchange='BZ').values()
        return get_descriptors(list(codes), start_date=start_date, descriptors=descriptors_list)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

df = load_data(start_date=datetime.now() - timedelta(days=180), descriptors_list=["price_close", "median_dollar_volume_traded_21d"])
df = df.swaplevel(0, axis=1)
most_liquid = df["median_dollar_volume_traded_21d"].dropna(how='all', axis='rows').iloc[-1]
most_liquid = most_liquid[most_liquid > min_liquidity]

df = df["price_close"][most_liquid.index]
df = df.apply(calculate_sqn, period=lookback_days, axis=0)
df = df.tail(n_periods).T
df = df[sorted(df.columns, reverse=True)]
df = df.sort_values(by=df.columns[0], ascending=False)
df = df.dropna(how='all', axis='rows')

st.dataframe(
    style_table(
        df=df,
        column_names=[col.strftime('%Y-%m-%d') for col in df.columns],
        numeric_cols_format_as_float=[col.strftime('%Y-%m-%d') for col in df.columns]
    )
)
