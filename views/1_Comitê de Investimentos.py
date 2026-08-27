import streamlit as st
import pandas as pd
from datetime import datetime
from persevera_tools.data import get_series
from utils.chart_helpers import extract_codes_from_config, organize_charts_by_context, render_chart_group_with_context
from configs.pages.comite_investimentos import CHARTS_INVESTIMENTOS_BR, CHARTS_INVESTIMENTOS_US

st.title('Comitê de Investimentos')

@st.cache_data(ttl=7200)
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def render_context_groups(data, chart_configs, charts_by_context, context):
    groups = list(charts_by_context.get(context, {}).keys())
    if not groups:
        return

    if len(groups) == 1:
        render_chart_group_with_context(data, chart_configs, context, groups[0], charts_by_context)
        return

    group_tabs = st.tabs(groups)
    for tab, group in zip(group_tabs, groups):
        with tab:
            render_chart_group_with_context(data, chart_configs, context, group, charts_by_context)

CHARTS_BY_REGION = {
    "Brasil": CHARTS_INVESTIMENTOS_BR,
    "Estados Unidos": CHARTS_INVESTIMENTOS_US,
}

with st.sidebar:
    st.header("Parâmetros")
    selected_region = st.radio("Região", list(CHARTS_BY_REGION.keys()), index=0, horizontal=True)
    start_date = st.date_input("Data Inicial", min_value=datetime(1990, 1, 1), value=datetime(2010, 1, 1), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

chart_configs = CHARTS_BY_REGION[selected_region]
CODES = extract_codes_from_config(chart_configs)

with st.spinner("Carregando dados...", show_time=True):
    data = load_data(CODES, start_date=start_date_str)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    charts_by_context = organize_charts_by_context(chart_configs)

    tabs = st.tabs(["Cockpit", "Temas", "Mercados", "Micro", "Teses", "Carteiras"])

    with tabs[0]:   # Tab 1: Cockpit
        pass

    with tabs[1]:   # Tab 2: Temas
        temas = ["Crescimento", "Inflação", "Fiscal", "Política Monetária", "Liquidez", "Posicionamento", "Oferta e Demanda"]
        tabs_temas = st.tabs(temas)

        for tab, tema in zip(tabs_temas, temas):
            with tab:
                render_context_groups(data, chart_configs, charts_by_context, tema)

    with tabs[2]:   # Tab 3: Mercados
        pass

    with tabs[3]:   # Tab 4: Micro
        pass

    with tabs[4]:   # Tab 5: Teses
        pass

    with tabs[5]:   # Tab 6: Carteiras
        pass
