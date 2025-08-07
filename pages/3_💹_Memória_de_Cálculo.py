import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication
from persevera_tools.data.providers import ComdinheiroProvider
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS

st.set_page_config(
    page_title="Memória de Cálculo | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Memória de Cálculo")

with st.sidebar:
    st.header("Parâmetros")
    selected_carteira = st.selectbox("Carteira selecionada", options=CODIGOS_CARTEIRAS)
    start_date = st.date_input("Data Inicial", format="DD/MM/YYYY", value=pd.to_datetime(date.today()), min_value=datetime(2024, 1, 1), max_value=pd.to_datetime(date.today()))
    end_date = st.date_input("Data Final", format="DD/MM/YYYY", value=pd.to_datetime(date.today()), min_value=datetime(2024, 1, 1), max_value=pd.to_datetime(date.today()))
    btn_run = st.button("Executar")

if 'table_data' not in st.session_state:
    st.session_state.df = None

if btn_run:
    with st.spinner("Carregando dados..."):
        provider = ComdinheiroProvider()
        df = provider.get_data(
            category='comdinheiro',
            data_type='portfolio_historical_positions',
            portfolios=[selected_carteira],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
        )
        st.session_state.df = df

df = st.session_state.df
if df is not None:
    try:
        table_data = df[df['ativo'] == 'Taxa de Administração']
        st.dataframe(style_table(
            table_data,
            column_names=['Data', 'Ativo', 'Descrição', 'Saldo Bruto'],
            date_cols=['Data'],
            currency_cols=['Saldo Bruto']),
        hide_index=True)

    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo: {e}")
