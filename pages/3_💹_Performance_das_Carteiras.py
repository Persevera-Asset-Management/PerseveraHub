import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
from datetime import datetime, date
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table, get_performance_table
from persevera_tools.data import get_series
from persevera_tools.data.providers import ComdinheiroProvider
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS_ADM
from utils.auth import check_authentication

st.set_page_config(
    page_title="Performance das Carteiras | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Performance das Carteiras")

@st.cache_data(ttl=3600)
def load_indicators(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data", format="DD/MM/YYYY", value=datetime(2024, 12, 30), min_value=datetime(2024, 1, 1), max_value=pd.to_datetime(date.today()))
    end_date = st.date_input("Data", format="DD/MM/YYYY", value=pd.to_datetime(date.today()), min_value=datetime(2024, 1, 1), max_value=pd.to_datetime(date.today()))
    selected_carteiras = st.multiselect("Carteiras selecionadas", options=sorted(CODIGOS_CARTEIRAS_ADM.keys()), default=sorted(CODIGOS_CARTEIRAS_ADM.keys()))
    btn_run = st.button("Executar")

if 'df' not in st.session_state:
    st.session_state.df = None

if btn_run:
    with st.spinner("Carregando dados...", show_time=True):
        provider = ComdinheiroProvider()
        st.session_state.nav_data = provider.get_data(
            category='comdinheiro',
            data_type='portfolio_nav',
            portfolios=selected_carteiras,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        st.session_state.nav_data.dropna(inplace=True)
    
    with st.spinner("Carregando indicadores...", show_time=True):
        indicators = load_indicators(['br_ibovespa', 'br_cdi_index'], start_date=start_date.strftime('%Y-%m-%d'))
        indicators.ffill(inplace=True)

nav_data = st.session_state.nav_data
if nav_data is not None:
    try:
        df = pd.merge(
            nav_data.pivot(index='date', columns='portfolio', values='nav'),
            indicators.rename(columns={'br_ibovespa': 'Ibovespa', 'br_cdi_index': 'CDI'}),
            left_index=True,
            right_index=True,
            how='left'
        )
        # df.ffill(inplace=True)
        performance_table = get_performance_table(df)
        performance_table.set_index('index', inplace=True)

        st.dataframe(style_table(
            performance_table.drop(columns=['24m', '36m']),
            numeric_cols_format_as_float=['mtd', 'ytd', '1m', '3m', '6m', '12m']),
        hide_index=True)

    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo: {e}")
