import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from persevera_tools.data.private_credit import get_series
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication
import streamlit_highcharts as hct
import numpy as np

st.set_page_config(
    page_title="Crédito Privado (Pricing) | Persevera",
    page_icon="📈",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

# Common meetings header with navigation links
st.title("Crédito Privado (Pricing)")

def load_data(code):
    try:
        df = get_series(code, field=['price_close', 'price_close_adj'])
        df.columns = df.columns.droplevel(0)
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

with st.sidebar:
    st.header("Parâmetros")
    code = st.text_input("Código do Ativo")
    btn_load = st.button("Carregar Dados")

if btn_load:
    with st.spinner("Carregando dados...", show_time=True):
        data = load_data(code)
    
    if data.empty:
        st.warning("Não foi possível carregar os dados. Código de ativo não encontrado.")
    else:
        st.subheader("Preço por Fonte")

        row_1 = st.columns(2)
        with row_1[0]:
            st.dataframe(
                style_table(
                    data.sort_index(ascending=False).reset_index(),
                    numeric_cols_format_as_float=data.columns.tolist(),
                    date_cols=['date']
                ),
                hide_index=True
            )
        with row_1[1]:
            chart_price = create_chart(
                data=data,
                columns=data.columns.tolist(),
                names=data.columns.tolist(),
                chart_type='line',
                title="Evolução do Preço do Ativo",
                y_axis_title="Preço (R$)",
                decimal_precision=2
            )
            hct.streamlit_highcharts(chart_price)