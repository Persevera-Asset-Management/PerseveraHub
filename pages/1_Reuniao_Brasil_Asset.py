import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from persevera_tools.data import get_series
from utils.chart_helpers import extract_codes_from_config, organize_charts_by_group, render_chart_group

st.set_page_config(
    page_title="Brasil Asset III | Persevera",
    page_icon="🗓️",
    layout="wide"
)

# Common meetings header with navigation links
st.title("Brasil Asset III")

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Chart configurations
chart_configs = {
    "curva_juros_pre": {
        "title": "#### Curva de Juros Pré",
        "chart_config": {
            "columns": ["br_pre_1y", "br_pre_2y", "br_pre_5y", "br_generic_10y"],
            "names": ["1Y", "2Y", "5Y", "10Y"],
            "chart_type": "line",
            "title": "Curva de Juros Pré",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "renda_fixa"
    },
    "curva_juros_ipca": {
        "title": "#### Curva de Juros IPCA",
        "chart_config": {
            "columns": ["br_ipca_1y", "br_ipca_2y", "br_ipca_5y", "br_ipca_10y"],
            "names": ["1Y", "2Y", "5Y", "10Y"],
            "chart_type": "line",
            "title": "Curva de Juros IPCA",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "renda_fixa"
    },
    "bolsas_ibov": {
        "title": "#### Ibovespa",
        "chart_config": {
            "columns": "br_ibovespa",
            "names": "Ibovespa",
            "chart_type": "line",
            "title": "Ibovespa",
            "y_axis_title": "Pontos",
        },
        "width": 6,
        "group": "renda_variavel"
    },
    "bolsas_sp500": {
        "title": "#### S&P 500",
        "chart_config": {
            "columns": "us_sp500",
            "names": "S&P 500",
            "chart_type": "line",
            "title": "S&P 500",
            "y_axis_title": "Pontos",
        },
        "width": 6,
        "group": "renda_variavel"
    },
    "bolsas_euro_stoxx": {
        "title": "#### Euro Stoxx 50",
        "chart_config": {
            "columns": "euro_stoxx50",
            "names": "Euro Stoxx 50",
            "chart_type": "line",
            "title": "Euro Stoxx 50",
            "y_axis_title": "Pontos",
        },
        "width": 6,
        "group": "renda_variavel"
    },
    "bolsas_china_csi1000": {
        "title": "#### CSI 1000",
        "chart_config": {
            "columns": "china_csi1000",
            "names": "CSI 1000",
            "chart_type": "line",
            "title": "CSI 1000",
            "y_axis_title": "Pontos",
        },
        "width": 6,
        "group": "renda_variavel"
    },
    "moedas_dxy": {
        "title": "#### DXY",
        "chart_config": {
            "columns": "dxy_index",
            "names": "DXY",
            "chart_type": "line",
            "title": "DXY",
            "y_axis_title": "Pontos",
        },
        "width": 6,
        "group": "moedas"
    },
    "moedas_eurusd": {
        "title": "#### EUR/USD",
        "chart_config": {
            "columns": "eur_usd",
            "names": "EUR/USD",
            "chart_type": "line",
            "title": "EUR/USD",
            "y_axis_title": "Taxa",
        },
        "width": 6,
        "group": "moedas"
    },
    "moedas_usdbrl": {
        "title": "#### BRL/USD",
        "chart_config": {
            "columns": "brl_usd",
            "names": "BRL/USD",
            "chart_type": "line",
            "title": "BRL/USD",
            "y_axis_title": "Taxa",
        },
        "width": 6,
        "group": "moedas"
    },
    "moedas_mxnusd": {
        "title": "#### MXN/USD",
        "chart_config": {
            "columns": "mxn_usd",
            "names": "MXN/USD",
            "chart_type": "line",
            "title": "MXN/USD",
            "y_axis_title": "Taxa",
        },
        "width": 6,
        "group": "moedas"
    },
}

# Extract all unique column codes
CODES = extract_codes_from_config(chart_configs)

# Date range selector
col1, col2 = st.columns([1, 3])
with col1:
    start_date = st.date_input("Data Inicial", datetime.now() - timedelta(days=180), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

# Load data with progress indicator
with st.spinner("Carregando dados de mercado..."):
    data = load_data(CODES, start_date=start_date_str)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    # Organize charts by group
    charts_by_group = organize_charts_by_group(chart_configs)
    
    # Render each group of charts
    for group_name in ["renda_fixa", "renda_variavel", "moedas"]:
        if group_name in charts_by_group:
            render_chart_group(data, chart_configs, group_name, charts_by_group)
