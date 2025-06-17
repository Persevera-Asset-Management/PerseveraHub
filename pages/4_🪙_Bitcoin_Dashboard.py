import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from persevera_tools.data import get_series
from utils.chart_helpers import extract_codes_from_config, organize_charts_by_context, render_chart_group_with_context
from configs.pages.dashboard_bitcoin import BITCOIN_DASHBOARD
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

st.set_page_config(
    page_title="Bitcoin Dashboard | Persevera",
    page_icon="🪙",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title('Bitcoin Dashboard')

@st.cache_data(ttl=3600)
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Chart configurations
chart_configs = BITCOIN_DASHBOARD

# Extract all unique column codes
CODES = extract_codes_from_config(chart_configs)

# Date range selector
st.sidebar.header("Filtros")
start_date = st.sidebar.date_input("Data Inicial", min_value=datetime(1990, 1, 1), value=datetime(2015, 1, 1), format="DD/MM/YYYY")
start_date_str = start_date.strftime('%Y-%m-%d')

# Load data with progress indicator
with st.spinner("Carregando dados econômicos..."):
    data = load_data(CODES, start_date=start_date_str)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    # Organize charts by context and group
    charts_by_context = organize_charts_by_context(chart_configs)
        
    st.header("Bitcoin")
    bitcoin_context = charts_by_context.get("Bitcoin", {})
        
    render_chart_group_with_context(data, chart_configs, "Bitcoin", "Volatilidade", charts_by_context)
    render_chart_group_with_context(data, chart_configs, "Bitcoin", "Correlação", charts_by_context)
