import pandas as pd
from datetime import datetime, timedelta, date

import streamlit as st
import streamlit_highcharts as hct

from utils.chart_helpers import create_chart, extract_codes_from_config, organize_charts_by_context, render_chart_group_with_context
from configs.pages.reuniao_brasil_asset import CHARTS_BRASIL_ASSET

from persevera_tools.data import get_series
from persevera_tools.fixed_income import calculate_spread

st.title("Reunião · Brasil Asset III")

@st.cache_data(ttl=3600)
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field="close")
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_spreads(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field=["median", "mean", "weighted_mean"])
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Chart configurations
chart_configs = CHARTS_BRASIL_ASSET

# Extract all unique column codes
CODES = extract_codes_from_config(chart_configs)

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", pd.to_datetime(date.today() - timedelta(days=365)), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

with st.spinner("Carregando dados...", show_time=True):
    data = load_data(CODES, start_date=start_date_str)
    spreads = load_spreads(["persevera_anbima_debentures_spread_di", "persevera_anbima_debentures_spread_ipca_incent"], start_date=start_date_str)

if data.empty or spreads.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    # Organize charts by context and group
    charts_by_context = organize_charts_by_context(chart_configs)
        
    # Create tabs for different regions
    tabs = st.tabs(["Títulos Públicos", "Renda Variável", "Moedas", "Crédito Privado"])
    
    # Tab 1: Títulos Públicos
    with tabs[0]:
        st.subheader("Títulos Públicos")
        render_chart_group_with_context(data, chart_configs, "Títulos Públicos", "Curvas de Juros", charts_by_context)

    # Tab 2: Renda Variável
    with tabs[1]:
        st.subheader("Renda Variável")
        render_chart_group_with_context(data, chart_configs, "Renda Variável", "Índices", charts_by_context)

    # Tab 3: Moedas
    with tabs[2]:
        st.subheader("Moedas")
        render_chart_group_with_context(data, chart_configs, "Moedas", "Índices e Taxas de Câmbio", charts_by_context)

    # Tab 4: Crédito Privado
    with tabs[3]:
        st.subheader("Crédito Privado")

        row_1 = st.columns(2)
        with row_1[0]:
            chart_spread_cdi_options = create_chart(
                data=spreads["persevera_anbima_debentures_spread_di"],
                columns=["median", "mean", "weighted_mean"],
                names=["Mediana", "Média", "Média Ponderada"],
                chart_type='line',
                title="Evolução do Spread CDI+",
                y_axis_title="Spread (%)",
                decimal_precision=3
            )
            hct.streamlit_highcharts(chart_spread_cdi_options)

        with row_1[1]:
            chart_spread_ipca_incent_options = create_chart(
                data=spreads["persevera_anbima_debentures_spread_ipca_incent"],
                columns=["median", "mean", "weighted_mean"],
                names=["Mediana", "Média", "Média Ponderada"],
                chart_type='line',
                title="Evolução do Spread IPCA+ Incentivado",
                y_axis_title="Spread (%)",
                decimal_precision=3
            )
            hct.streamlit_highcharts(chart_spread_ipca_incent_options)
