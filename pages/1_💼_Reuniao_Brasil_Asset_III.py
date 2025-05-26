import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from persevera_tools.data import get_series
from utils.chart_helpers import extract_codes_from_config, organize_charts_by_context, render_chart_group_with_context
from configs.pages.reuniao_brasil_asset import CHARTS_BRASIL_ASSET

st.set_page_config(
    page_title="Brasil Asset III | Persevera",
    page_icon="🗓️",
    layout="wide"
)

# Inclusão do CSS
assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
css_path = os.path.join(assets_dir, 'style.css')
with open(css_path) as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Common meetings header with navigation links
st.title("Brasil Asset III")

@st.cache_data(ttl=3600)
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Chart configurations
chart_configs = CHARTS_BRASIL_ASSET

# Extract all unique column codes
CODES = extract_codes_from_config(chart_configs)

# Date range selector
st.sidebar.header("Filtros")
start_date = st.sidebar.date_input("Data Inicial", datetime.now() - timedelta(days=365), format="DD/MM/YYYY")
start_date_str = start_date.strftime('%Y-%m-%d')

# Load data with progress indicator
with st.spinner("Carregando dados de mercado..."):
    data = load_data(CODES, start_date=start_date_str)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    # Organize charts by context and group
    charts_by_context = organize_charts_by_context(chart_configs)
        
    # Create tabs for different regions
    tabs = st.tabs(["Títulos Públicos", "Renda Variável", "Moedas", "Crédito Privado"])
    
    # Tab 1: Títulos Públicos
    with tabs[0]:
        st.header("Títulos Públicos")
        render_chart_group_with_context(data, chart_configs, "Títulos Públicos", "Curvas de Juros", charts_by_context)

    # Tab 2: Renda Variável
    with tabs[1]:
        st.header("Renda Variável")
        render_chart_group_with_context(data, chart_configs, "Renda Variável", "Índices", charts_by_context)

    # Tab 3: Moedas
    with tabs[2]:
        st.header("Moedas")
        render_chart_group_with_context(data, chart_configs, "Moedas", "Índices e Taxas de Câmbio", charts_by_context)
