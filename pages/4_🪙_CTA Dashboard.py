import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from persevera_tools.data import get_series
from utils.chart_helpers import extract_codes_from_config, organize_charts_by_context, render_chart_group_with_context
from configs.pages.dashboard_cta import CTA_DASHBOARD
from utils.chart_helpers import create_chart
import streamlit_highcharts as hct
from utils.table import style_table

st.set_page_config(
    page_title="CTA Dashboard | Persevera",
    page_icon="🪙",
    layout="wide"
)

# Inclusão do CSS
assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
css_path = os.path.join(assets_dir, 'style.css')
with open(css_path) as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.title('CTA Dashboard')

@st.cache_data(ttl=3600)
def load_data(codes, field, start_date):
    try:
        return get_series(codes, start_date=start_date, field=field)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Chart configurations
chart_configs = CTA_DASHBOARD

# Extract all unique column codes
CODES = extract_codes_from_config(chart_configs)

# Date range selector
st.sidebar.header("Filtros")
start_date = st.sidebar.date_input("Data Inicial", min_value=datetime(2025, 1, 23), value=datetime(2025, 1, 23), format="DD/MM/YYYY")
start_date_str = start_date.strftime('%Y-%m-%d')

# Load data with progress indicator
with st.spinner("Carregando dados econômicos..."):
    data_cta_weight = load_data(CODES, field='cta_weight', start_date=start_date_str) * 100
    data_close = load_data(CODES, field='close', start_date=start_date_str)
    data_close = data_close.add_suffix('_close', axis=1)

if data_cta_weight.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:        
    st.header("$CTA (Simplify Managed Futures Strategy ETF)")

    # Create the table
    cta_table = data_cta_weight.iloc[[-1,-2,-21]].T.dropna(how='all')
    cta_table.columns = ['CTA Position Today (%)', 'CTA Position Yesterday (%)', 'CTA Position 21 Days Ago (%)']
    cta_table.sort_values(by='CTA Position Today (%)', ascending=False, inplace=True)

    st.write(f"Dado mais recente: {data_cta_weight.iloc[-1].name.date()}")
    st.dataframe(style_table(cta_table, numeric_cols_format_as_float=['CTA Position Today (%)', 'CTA Position Yesterday (%)', 'CTA Position 21 Days Ago (%)']))

    # Asset selection for the chart
    asset_list = ['Todos'] + sorted(list(data_cta_weight.columns))
    selected_asset = st.selectbox('Selecione um ativo:', asset_list)

    # Create the chart based on selection
    if selected_asset == 'Todos':
        cta_chart_options = create_chart(
            data=data_cta_weight,
            columns=list(data_cta_weight.columns),
            names=list(data_cta_weight.columns),
            chart_type='column',
            stacking='normal',
            title="Posições",
            y_axis_title="Peso (%)",
        )
    else:
        # Chart for a single selected asset
        cta_chart_options = create_chart(
            data=pd.merge(data_cta_weight, data_close, left_index=True, right_index=True, how='left'),
            columns=[selected_asset + '_close', selected_asset],
            names=["Preço ($)", "Peso (%)"],
            chart_type='dual_axis_line_area',
            stacking=None,
            title=f"Posição em {selected_asset.replace('_futures', '').replace('_', ' ').title()}",
            y_axis_title=("Preço ($)", "Peso (%)"),
        )
    
    hct.streamlit_highcharts(cta_chart_options)
