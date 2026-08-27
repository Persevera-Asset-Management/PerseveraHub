import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from persevera_tools.data import get_series
from utils.chart_helpers import extract_codes_from_config, organize_charts_by_context, render_chart_group_with_context
from configs.pages.reuniao_economia import CHARTS_ECONOMIA

st.title('Comitê de Investimentos')

@st.cache_data(ttl=7200)
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Chart configurations
chart_configs = CHARTS_ECONOMIA

# Extract all unique column codes
CODES = extract_codes_from_config(chart_configs)

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", min_value=datetime(1990, 1, 1), value=datetime(2010, 1, 1), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

with st.spinner("Carregando dados...", show_time=True):
    data = load_data(CODES, start_date=start_date_str)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    charts_by_context = organize_charts_by_context(chart_configs)
        
    tabs = st.tabs(["Cockpit", "Temas", "Mercados", "Micro", "Teses", "Carteiras"])
    
    with tabs[0]:   # Tab 1: Cockpit
        st.header("Cockpit")

    with tabs[1]:   # Tab 2: Temas
        st.header("Temas")

    with tabs[2]:   # Tab 3: Mercados
        st.header("Mercados")

    with tabs[3]:   # Tab 4: Micro
        st.header("Micro")

    with tabs[4]:   # Tab 5: Teses
        st.header("Teses")

    with tabs[5]:   # Tab 6: Carteiras
        st.header("Carteiras")