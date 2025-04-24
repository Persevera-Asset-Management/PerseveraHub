import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit_highcharts as hct
from persevera_tools.data import get_series
from utils.chart_helpers import extract_codes_from_config, organize_charts_by_group, render_chart_group

st.set_page_config(
    page_title="Reunião de Economia | Persevera",
    page_icon="🗓️",
    layout="wide"
)

# Common meetings header with navigation links
st.title("Reunião de Economia")

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Chart configurations
chart_configs = {
    # Estados Unidos
    "us_gdp_qoq": {
        "title": "#### US GDP Growth QoQ",
        "chart_config": {
            "columns": ["us_gdp_qoq"],
            "names": ["GDP QoQ (%)"],
            "chart_type": "column",
            "title": "PIB QoQ",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "us_gdp"
    },
    "us_gdp_yoy": {
        "title": "#### US GDP Growth YoY",
        "chart_config": {
            "columns": ["us_gdp_yoy"],
            "names": ["GDP YoY (%)"],
            "chart_type": "column",
            "title": "PIB YoY",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "us_gdp"
    },
    "us_industry_surprise": {
        "chart_config": {
            "columns": ["us_bloomberg_industry_surprise_index"],
            "names": ["Industry"],
            "chart_type": "area",
            "title": "Bloomberg US Industrial Sector Surprise Index",
            "y_axis_title": "Índice",
        },
        "width": 6,
        "group": "Industrial Bloomberg Data Surprise"
    },
    "us_industry_production": {
        "chart_config": {
            "columns": ["us_industrial_production_index", "us_capacity_utilization_index"],
            "names": ["Industrial Production", "Capacity Utilization"],
            "chart_type": "line",
            "title": "Produção Industrial e Utilização de Capacidade",
            "y_axis_title": "Índice",
        },
        "width": 6,
        "group": "Produção Industrial & Utilização de Capacidade"
    },
    "us_retail_surprise": {
        "chart_config": {
            "columns": ["us_bloomberg_retail_surprise_index"],
            "names": ["Retail Sales"],
            "chart_type": "area",
            "title": "Bloomberg Retail & Wholesale Sector Surprise Index",
            "y_axis_title": "Índice",
        },
        "width": 6,
        "group": "Retail & Wholesale Bloomberg Data Surprise"
    },
    "us_retail_sales": {
        "chart_config": {
            "columns": ["us_advance_retail_sales_total", "us_advance_retail_sales_ex_auto_total"],
            "names": ["Retail Sales"],
            "chart_type": "line",
            "title": "Vendas no Varejo",
            "y_axis_title": "Índice",
        },
        "width": 6,
        "group": "Vendas no Varejo"
    },


    # Brasil
    "br_ibcbr_index": {
        "title": "#### IBC-Br",
        "chart_config": {
            "columns": ["br_ibcbr_index"],
            "names": ["IBC-Br"],
            "chart_type": "line",
            "title": "IBC-Br",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "br_ibcbr"
    },
    "br_gdp_qoq": {
        "title": "#### PIB QoQ",
        "chart_config": {
            "columns": ["br_gdp_index"],
            "names": ["GDP QoQ (%)"],
            "chart_type": "column",
            "title": "PIB QoQ",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "br_gdp"   
    },
    "br_gdp_yoy": {
        "title": "#### PIB YoY",
        "chart_config": {
            "columns": ["br_gdp_12m"],
            "names": ["GDP YoY (%)"],
            "chart_type": "column",
            "title": "PIB YoY",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "br_gdp"
    },
}

# Extract all unique column codes
CODES = extract_codes_from_config(chart_configs)

# Date range selector
col1, col2 = st.columns([1, 3])
with col1:
    start_date = st.date_input("Data Inicial", datetime(2000, 1, 1), format="DD/MM/YYYY", key="date_input")
    start_date_str = start_date.strftime('%Y-%m-%d')

# Load data with progress indicator
with st.spinner("Carregando dados econômicos..."):
    data = load_data(CODES, start_date=start_date_str)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    # Organize charts by group
    charts_by_group = organize_charts_by_group(chart_configs)
    
    # Create tabs for different regions
    tabs = st.tabs(["Estados Unidos", "Brasil", "Global"])
    
    # Tab 1: Estados Unidos
    with tabs[0]:
        # Nested tabs for US data categories
        us_tabs = st.tabs(["PIB", "Inflação", "Emprego", "Indústria", "Varejo", "Imobiliário", "Crédito", "Sentimento"])
        
        with us_tabs[0]:
            if "us_gdp" in charts_by_group:
                render_chart_group(data, chart_configs, "us_gdp", charts_by_group)

        with us_tabs[1]:
            if "us_inflation" in charts_by_group:
                render_chart_group(data, chart_configs, "us_inflation", charts_by_group)

        with us_tabs[2]:
            if "us_employment" in charts_by_group:
                render_chart_group(data, chart_configs, "us_employment", charts_by_group)

        with us_tabs[3]:
            if "Industrial Bloomberg Data Surprise" in charts_by_group:
                render_chart_group(data, chart_configs, "Industrial Bloomberg Data Surprise", charts_by_group)
            
            if "Produção Industrial & Utilização de Capacidade" in charts_by_group:
                render_chart_group(data, chart_configs, "Produção Industrial & Utilização de Capacidade", charts_by_group)
                
        with us_tabs[4]:
            if "Retail & Wholesale Bloomberg Data Surprise" in charts_by_group:
                render_chart_group(data, chart_configs, "Retail & Wholesale Bloomberg Data Surprise", charts_by_group)
                
            if "Vendas no Varejo" in charts_by_group:
                render_chart_group(data, chart_configs, "Vendas no Varejo", charts_by_group)
                

        with us_tabs[5]:
            if "us_real_estate" in charts_by_group:
                render_chart_group(data, chart_configs, "us_real_estate", charts_by_group)

        with us_tabs[6]:
            if "us_credit" in charts_by_group:
                render_chart_group(data, chart_configs, "us_credit", charts_by_group)

        with us_tabs[7]:
            if "us_sentiment" in charts_by_group:
                render_chart_group(data, chart_configs, "us_sentiment", charts_by_group)
    
    # Tab 2: Brasil
    with tabs[1]:
        # Nested tabs for Brazil data categories
        br_tabs = st.tabs(["IBC-Br", "PIB", "Inflação", "Indústria", "Serviços", "Varejo", "Sentimento", "Emprego", "Crédito", "Setor Externo", "Commodities", "Fiscal"])
        
        with br_tabs[0]:
            if "br_ibcbr" in charts_by_group:
                render_chart_group(data, chart_configs, "br_ibcbr", charts_by_group)
                
        with br_tabs[1]:
            if "br_gdp" in charts_by_group:
                render_chart_group(data, chart_configs, "br_gdp", charts_by_group)
    
    # Tab 3: Global
    with tabs[2]:
        # Nested tabs for global data categories
        global_tabs = st.tabs(["PMI"])
        
