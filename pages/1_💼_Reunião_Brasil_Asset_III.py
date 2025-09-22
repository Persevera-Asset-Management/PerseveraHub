import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from persevera_tools.data import get_series
from persevera_tools.data.private_credit import calculate_spread
from utils.chart_helpers import create_chart, extract_codes_from_config, organize_charts_by_context, render_chart_group_with_context
from configs.pages.reuniao_brasil_asset import CHARTS_BRASIL_ASSET
from utils.ui import display_logo, load_css
from utils.auth import check_authentication
import streamlit_highcharts as hct

st.set_page_config(
    page_title="Brasil Asset III | Persevera",
    page_icon="🗓️",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

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

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", pd.to_datetime(date.today() - timedelta(days=365)), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

with st.spinner("Carregando dados...", show_time=True):
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

    # Tab 4: Crédito Privado
    with tabs[3]:
        st.header("Crédito Privado")
        spread_cdi = calculate_spread("DI", deb_incent_lei_12431=False, start_date=start_date_str, calculate_distribution=False)
        spread_ipca_incent = calculate_spread("IPCA", deb_incent_lei_12431=True, start_date=start_date_str, calculate_distribution=False)

        row_1 = st.columns(2)
        with row_1[0]:
            chart_spread_cdi_options = create_chart(
                data=spread_cdi,
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
                data=spread_ipca_incent,
                columns=["median", "mean", "weighted_mean"],
                names=["Mediana", "Média", "Média Ponderada"],
                chart_type='line',
                title="Evolução do Spread IPCA+ Incentivado",
                y_axis_title="Spread (%)",
                decimal_precision=3
            )
            hct.streamlit_highcharts(chart_spread_ipca_incent_options)
