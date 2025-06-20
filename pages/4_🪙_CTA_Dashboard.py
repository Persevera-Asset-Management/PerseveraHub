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
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

st.set_page_config(
    page_title="CTA Dashboard | Persevera",
    page_icon="🪙",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title('CTA Dashboard')

@st.cache_data(ttl=3600)
def load_data(codes, field, start_date):
    try:
        return get_series(codes, start_date=start_date, field=field)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", min_value=datetime(2025, 1, 23), value=datetime(2025, 1, 23), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

# Load data with progress indicator
with st.spinner("Carregando dados econômicos..."):
    data = load_data(list(CTA_DASHBOARD.keys()), field=['close', 'weight_cta_simplify', 'weight_cta_invesco'], start_date=start_date_str)
    data = data.swaplevel(axis=1)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    # $CTA (Simplify Managed Futures Strategy ETF)
    st.subheader("$CTA (Simplify Managed Futures Strategy ETF)")

    # Create the table
    cta_table = data['weight_cta_simplify'].dropna(how='all', axis=0).iloc[[-1,-2,-21]].T.dropna(how='all')
    cta_most_recent_date = data['weight_cta_simplify'].dropna(how='all', axis=0).index[-1].date()
    cta_table.columns = ['CTA Position Today (%)', 'CTA Position Yesterday (%)', 'CTA Position 21 Days Ago (%)']
    cta_table.sort_values(by='CTA Position Today (%)', ascending=False, inplace=True)
    cta_table.index = cta_table.index.map(lambda x: CTA_DASHBOARD[x])
    cta_table = cta_table.mul(100)

    st.write(f"Dado mais recente: {cta_most_recent_date}")
    st.dataframe(style_table(cta_table, numeric_cols_format_as_float=['CTA Position Today (%)', 'CTA Position Yesterday (%)', 'CTA Position 21 Days Ago (%)']))

    # Asset selection for the chart
    asset_list = ['Todos'] + sorted(list(cta_table.index))
    selected_asset = st.selectbox('Selecione um ativo:', asset_list)

    # Create the chart based on selection
    if selected_asset == 'Todos':
        cta_chart_data = data['weight_cta_simplify'].dropna(how='all', axis=0).dropna(how='all', axis=1).rename(columns=CTA_DASHBOARD)
        cta_chart_options = create_chart(
            data=cta_chart_data,
            columns=list(cta_chart_data.columns),
            names=list(cta_chart_data.columns),
            chart_type='column',
            stacking='normal',
            title="Posições",
            y_axis_title="Peso (%)",
        )
    else:
        # Chart for a single selected asset
        cta_chart_data = pd.merge(
            data['weight_cta_simplify'].rename(columns=lambda x: CTA_DASHBOARD[x]),
            data['close'].rename(columns=lambda x: CTA_DASHBOARD[x]).add_suffix('_close', axis=1),
            left_index=True,
            right_index=True,
            how='left'
        )
        cta_chart_options = create_chart(
            data=cta_chart_data,
            columns=[selected_asset + '_close', selected_asset],
            names=["Preço ($)", "Peso (%)"],
            chart_type='dual_axis_line_area',
            stacking=None,
            colors=["#19202a", "#cdb89b"],
            title=f"Posição em {selected_asset.replace('_futures', '').replace('_', ' ').title()}",
            y_axis_title=("Preço ($)", "Peso (%)"),
        )
    
    hct.streamlit_highcharts(cta_chart_options)

    # $IMF (Invesco Managed Futures Strategy ETF)
    st.subheader("$IMF (Invesco Managed Futures Strategy ETF)")

    # Create the table
    imf_table = data['weight_cta_invesco'].dropna(how='all', axis=0).iloc[-1].T.dropna(how='all')
    imf_most_recent_date = data['weight_cta_invesco'].dropna(how='all', axis=0).index[-1].date()
    imf_table.sort_values(ascending=False, inplace=True)
    imf_table.index = imf_table.index.map(lambda x: CTA_DASHBOARD[x])

    st.write(f"Dado mais recente: {imf_most_recent_date}")

    imf_chart_options = create_chart(
        data=imf_table.to_frame('Peso (%)'),
        columns=['Peso (%)'],
        names=['Peso (%)'],
        chart_type='bar',
        stacking=None,
        title="Posições",
        y_axis_title="Peso (%)",
        x_axis_title="Ativos",
        height=600,
    )
    hct.streamlit_highcharts(imf_chart_options, height=600)
