import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.chart_helpers import extract_codes_from_config, organize_charts_by_context, render_chart_group_with_context
from configs.pages.reuniao_estrategia import CHARTS_ESTRATEGIA
from utils.ui import display_logo, load_css
from utils.auth import check_authentication
from persevera_tools.data import get_series
from utils.table import get_performance_table, style_table

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

with st.spinner("Carregando indicadores...", show_time=True):
    data = load_data(CODES, start_date=start_date_str)

with st.spinner("Carregando dados de valuation...", show_time=True):
    data_valuation = load_data(CODES, start_date=start_date_str, field='price_to_earnings_fwd')

with st.spinner("Carregando cotações das moedas...", show_time=True):
    curr_codes = {
        "usd_twi": "TWI (DM - Trade Weighted)",
        "ars_usd": "ARS",
        "aud_usd": "AUD",
        "brl_usd": "BRL",
        "cad_usd": "CAD",  
        "chf_usd": "CHF",
        "clp_usd": "CLP",
        "cnh_usd": "CNH",
        "cny_usd": "CNY",
        "cop_usd": "COP",
        "dxy_index": "DXY (DM)",
        "eur_usd": "EUR",
        "gbp_usd": "GBP",
        "idr_usd": "IDR",
        "jpm_em_currency_index": "JPM EM Currency Index",
        "jpy_usd": "JPY",
        "mxn_usd": "MXN",
        "nzd_usd": "NZD",
        "zar_usd": "ZAR",
    }
    data_currencies = load_data(list(curr_codes.keys()), start_date=start_date_str)

    non_inverted = ["usd_twi", "dxy_index", "jpm_em_currency_index", "eur_usd", "gbp_usd", "nzd_usd", "aud_usd"]
    set_inverse = list(set(curr_codes.keys()) - set(non_inverted))

    data_currencies[set_inverse] = data_currencies[set_inverse].apply(lambda x: x**(-1))
    data_currencies = data_currencies.rename(columns=curr_codes)

if data.empty or data_valuation.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    # Organize charts by context and group
    charts_by_context = organize_charts_by_context(chart_configs)
        
    # Create tabs for different regions
    tabs = st.tabs(["Juros", "Moedas", "Commodities", "Equities", "Crédito Privado"])
    
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

    # Tab 2: Moedas
    with tabs[1]:
        moedas_context = charts_by_context.get("Moedas", {})

        if "Performance" in moedas_context:
            render_chart_group_with_context(data, chart_configs, "Moedas", "Performance", charts_by_context)

            # Tabela comparativa
            styled_performance_table = style_table(
                get_performance_table(data_currencies),
                numeric_cols_format_as_float=['mtd', 'ytd', '1m', '3m', '6m', '12m', '24m', '36m'],
                highlight_row_by_column='code',
                highlight_row_if_value_equals='BRL',
                highlight_color='lightblue'
            )
            st.dataframe(styled_performance_table, use_container_width=True, hide_index=True)

        if "Reservas Internacionais" in moedas_context:
            render_chart_group_with_context(data, chart_configs, "Moedas", "Reservas Internacionais", charts_by_context)

    # Tab 3: Commodities
    with tabs[2]:
        commodities_context = charts_by_context.get("Commodities", {})
        commodities_codes = {col: name for entry in commodities_context['Commodities'] for col, name in zip(entry[1]['chart_config']['columns'], entry[1]['chart_config']['names'])}
        data_commodities = data[list(commodities_codes.keys())].rename(columns=commodities_codes)
        if "Commodities" in commodities_context:
            render_chart_group_with_context(data, chart_configs, "Commodities", "Commodities", charts_by_context)

            # Tabela comparativa
            styled_performance_table = style_table(
                get_performance_table(data_commodities),
                numeric_cols_format_as_float=['mtd', 'ytd', '1m', '3m', '6m', '12m', '24m', '36m'],
            )
            st.dataframe(styled_performance_table, use_container_width=True, hide_index=True)

    # Tab 4: Equities
    with tabs[3]:
        equities_context = charts_by_context.get("Equities", {})
        
        if "Valuation" in equities_context:
            render_chart_group_with_context(data_valuation, chart_configs, "Equities", "Valuation", charts_by_context)

    # Tab 5: Crédito Privado
    with tabs[4]:
        credito_privado_context = charts_by_context.get("Crédito Privado", {})
        