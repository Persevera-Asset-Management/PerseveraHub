import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
from datetime import datetime
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from persevera_tools.data.providers import ComdinheiroProvider
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS
from utils.auth import check_authentication

st.set_page_config(
    page_title="Atribuição de Performance | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Atribuição de Performance")

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_carteira = st.selectbox("Carteira selecionada", options=CODIGOS_CARTEIRAS)
    selected_report_date = st.date_input("Data do Relatório", format="DD/MM/YYYY", value=datetime.now(), min_value=datetime(2024, 1, 1), max_value=datetime.now())
    selected_inception_date = st.date_input("Data de Início (Inception)", format="DD/MM/YYYY", value=datetime.now(), min_value=datetime(2024, 1, 1), max_value=datetime.now())
    btn_run = st.button("Gerar Relatório")

if 'table_data' not in st.session_state:
    st.session_state.table_data = None

if btn_run:
    with st.spinner("Carregando dados..."):
        provider = ComdinheiroProvider()
        st.session_state.table_data = provider.get_data(
            category='portfolio_statement',
            portfolio=selected_carteira,
            date_inception=selected_inception_date.strftime('%Y-%m-%d'),
            date_report=selected_report_date.strftime('%Y-%m-%d'),
        )

table_data = st.session_state.table_data
if table_data is not None:
    try:
        st.dataframe(table_data['Posição Consolidada - No Mês'])

    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo: {e}")
