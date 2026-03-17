import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from persevera_tools.data import get_series
from utils.chart_helpers import extract_codes_from_config, organize_charts_by_context, render_chart_group_with_context
from configs.pages.reuniao_economia import CHARTS_ECONOMIA
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

st.set_page_config(
    page_title="Reunião · Economia | Persevera",
    page_icon="🗓️",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title('Reunião · Economia')

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
    # Organize charts by context and group
    charts_by_context = organize_charts_by_context(chart_configs)
        
    # Create tabs for different regions
    tabs = st.tabs(["Estados Unidos", "Brasil"])
    
    # Tab 1: Estados Unidos
    with tabs[0]:
        st.header("Estados Unidos")
        us_context = charts_by_context.get("Estados Unidos", {})
        
        us_tabs = st.tabs(["PIB", "Inflação", "Indústria", "Varejo", "Crédito", "Imobiliário", "Sentimento", "Emprego", "Fiscal"])
    
        with us_tabs[0]:
            if "PIB" in us_context:
                render_chart_group_with_context(data, chart_configs, "Estados Unidos", "PIB", charts_by_context)

        with us_tabs[1]:
            if "Inflação" in us_context:
                render_chart_group_with_context(data, chart_configs, "Estados Unidos", "Inflação", charts_by_context)

        with us_tabs[2]:
            if "Indústria" in us_context:
                render_chart_group_with_context(data, chart_configs, "Estados Unidos", "Indústria", charts_by_context)

        with us_tabs[3]:
            if "Varejo" in us_context:
                render_chart_group_with_context(data, chart_configs, "Estados Unidos", "Varejo", charts_by_context)

        with us_tabs[4]:
            if "Crédito" in us_context:
                render_chart_group_with_context(data, chart_configs, "Estados Unidos", "Crédito", charts_by_context)

        with us_tabs[5]:
            if "Imobiliário" in us_context:
                render_chart_group_with_context(data, chart_configs, "Estados Unidos", "Imobiliário", charts_by_context)

        with us_tabs[6]:
            if "Sentimento" in us_context:
                render_chart_group_with_context(data, chart_configs, "Estados Unidos", "Sentimento", charts_by_context)

        with us_tabs[7]:
            if "Emprego" in us_context:
                render_chart_group_with_context(data, chart_configs, "Estados Unidos", "Emprego", charts_by_context)

        with us_tabs[8]:
            if "Fiscal" in us_context:
                render_chart_group_with_context(data, chart_configs, "Estados Unidos", "Fiscal", charts_by_context)

    # Tab 2: Brasil
    with tabs[1]:
        st.header("Brasil")
        br_context = charts_by_context.get("Brasil", {})
        
        br_tabs = st.tabs(["PIB", "IBC-Br", "Indústria", "Serviços", "Varejo", "Inflação", "Fiscal", "Emprego", "Sentimento", "Crédito", "Setor Externo"])
        
        with br_tabs[0]:
            if "PIB" in br_context:
                render_chart_group_with_context(data, chart_configs, "Brasil", "PIB", charts_by_context)
                
        with br_tabs[1]:
            if "IBC-Br" in br_context:
                render_chart_group_with_context(data, chart_configs, "Brasil", "IBC-Br", charts_by_context) 

        with br_tabs[2]:
            if "Indústria" in br_context:
                render_chart_group_with_context(data, chart_configs, "Brasil", "Indústria", charts_by_context)
                
        with br_tabs[3]:
            if "Serviços" in br_context:
                render_chart_group_with_context(data, chart_configs, "Brasil", "Serviços", charts_by_context)

        with br_tabs[4]:
            if "Varejo" in br_context:
                render_chart_group_with_context(data, chart_configs, "Brasil", "Varejo", charts_by_context)

        with br_tabs[5]:
            if "Inflação" in br_context:
                render_chart_group_with_context(data, chart_configs, "Brasil", "Inflação", charts_by_context)

        with br_tabs[6]:
            if "Fiscal" in br_context:
                render_chart_group_with_context(data, chart_configs, "Brasil", "Fiscal", charts_by_context)

        with br_tabs[7]:
            if "Emprego" in br_context:
                render_chart_group_with_context(data, chart_configs, "Brasil", "Emprego", charts_by_context)

        with br_tabs[8]:
            if "Sentimento" in br_context:
                render_chart_group_with_context(data, chart_configs, "Brasil", "Sentimento", charts_by_context)

        with br_tabs[9]:
            if "Crédito" in br_context:
                render_chart_group_with_context(data, chart_configs, "Brasil", "Crédito", charts_by_context)

        with br_tabs[10]:
            if "Setor Externo" in br_context:
                render_chart_group_with_context(data, chart_configs, "Brasil", "Setor Externo", charts_by_context)

    # Tab 3: Global
    # with tabs[2]:
    #     st.header("Global")
