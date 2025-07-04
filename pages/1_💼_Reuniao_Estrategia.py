import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from persevera_tools.data import get_series
from utils.chart_helpers import extract_codes_from_config, organize_charts_by_context, render_chart_group_with_context
from configs.pages.reuniao_estrategia import CHARTS_ESTRATEGIA
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

st.set_page_config(
    page_title="Reunião Estratégia | Persevera",
    page_icon="🗓️",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title('Reunião Estratégia')

@st.cache_data(ttl=3600)
def load_data(codes, start_date, field='close'):
    try:
        return get_series(codes, start_date=start_date, field=field)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Chart configurations
chart_configs = CHARTS_ESTRATEGIA

# Extract all unique column codes
CODES = extract_codes_from_config(chart_configs)

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", min_value=datetime(1990, 1, 1), value=datetime(2010, 1, 1), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

# Load data with progress indicator
with st.spinner("Carregando dados econômicos..."):
    data = load_data(CODES, start_date=start_date_str)
    data_valuation = load_data(CODES, start_date=start_date_str, field='price_to_earnings_fwd')

if data.empty or data_valuation.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    # Organize charts by context and group
    charts_by_context = organize_charts_by_context(chart_configs)
        
    # Create tabs for different regions
    tabs = st.tabs(["Juros", "Cenários", "Commodities", "Moedas", "Equities"])
    
    # Tab 1: Juros
    with tabs[0]:
        juros_context = charts_by_context.get("Juros", {})        
        juros_tabs = st.tabs(["Taxas de Juros (US)", "Taxas Corporativas (US)", "Taxas de Juros (BR)"])
        
        # Taxas de Juros (US)
        with juros_tabs[0]:
            if "Taxas de Juros (US)" in juros_context:
                render_chart_group_with_context(data, chart_configs, "Juros", "Taxas de Juros (US)", charts_by_context)

        # Taxas Corporativas (US)
        with juros_tabs[1]:
            if "Taxas Corporativas (US)" in juros_context:
                render_chart_group_with_context(data, chart_configs, "Juros", "Taxas Corporativas (US)", charts_by_context)

        # Taxas de Juros (BR)
        with juros_tabs[2]:
            if "Taxas de Juros (BR)" in juros_context:
                render_chart_group_with_context(data, chart_configs, "Juros", "Taxas de Juros (BR)", charts_by_context)

    # Tab 2: Cenários
    with tabs[1]:
        cenarios_context = charts_by_context.get("Cenários", {})
        cenarios_tabs = st.tabs(["Cenários"])

        # Cenários
        with cenarios_tabs[0]:
            if "Cenários" in cenarios_context:
                render_chart_group_with_context(data, chart_configs, "Cenários", "Cenários", charts_by_context)
    
    # Tab 3: Commodities
    with tabs[2]:
        commodities_context = charts_by_context.get("Commodities", {})
        commodities_tabs = st.tabs(["Commodities"])

        # Commodities
        with commodities_tabs[0]:
            if "Commodities" in commodities_context:
                render_chart_group_with_context(data, chart_configs, "Commodities", "Commodities", charts_by_context)

    # Tab 4: Moedas
    with tabs[3]:
        moedas_context = charts_by_context.get("Moedas", {})

        if "Modelo Cambial" in moedas_context:
            render_chart_group_with_context(data, chart_configs, "Moedas", "Modelo Cambial", charts_by_context)

        if "Performance" in moedas_context:
            render_chart_group_with_context(data, chart_configs, "Moedas", "Performance", charts_by_context)

    # Tab 5: Equities
    with tabs[4]:
        equities_context = charts_by_context.get("Equities", {})
        equities_tabs = st.tabs(["Valuation"])

        # Valuation
        with equities_tabs[0]:
            if "Valuation" in equities_context:
                render_chart_group_with_context(data_valuation, chart_configs, "Equities", "Valuation", charts_by_context)