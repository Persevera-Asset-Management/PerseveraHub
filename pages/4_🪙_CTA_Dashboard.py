import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from persevera_tools.data import get_series
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
    start_date = st.date_input("Data Inicial", min_value=datetime(2023, 1, 3), value=datetime(2023, 1, 3), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

# Load data with progress indicator
with st.spinner("Carregando dados econômicos..."):
    data = load_data(list(CTA_DASHBOARD.keys()), field=['close', 'weight_cta_simplify', 'weight_cta_invesco', 'weight_cta_kraneshares'], start_date=start_date_str)
    data = data.swaplevel(axis=1)
    data = data.apply(lambda col: col * 100 if 'close' not in col.name else col)
    data.sort_index(axis=1, inplace=True)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    tab_etf, tab_consolidado = st.tabs(["Análise por ETF", "Consolidado"])

    with tab_etf:
        etf_options = {
            "Simplify (CTA)": "weight_cta_simplify",
            "Invesco (IMF)": "weight_cta_invesco",
            "KraneShares (KMLM)": "weight_cta_kraneshares"
        }
        selected_etf_name = st.selectbox("Selecione o ETF para análise:", list(etf_options.keys()))
        selected_etf_col = etf_options[selected_etf_name]

        # Create the table
        etf_table_data = data[selected_etf_col].dropna(how='all', axis=0)

        if not etf_table_data.empty and not etf_table_data.iloc[[-1]].isnull().all().all():
            etf_table = etf_table_data.iloc[[-1, -2, -21]].T.dropna(how='all')
            etf_most_recent_date = etf_table_data.index[-1].date()
            etf_table.columns = ['Posição Hoje (%)', 'Posição Ontem (%)', 'Posição 21 dias atrás (%)']
            etf_table.sort_values(by='Posição Hoje (%)', ascending=False, inplace=True)
            etf_table.index = etf_table.index.map(lambda x: CTA_DASHBOARD.get(x, x))

            st.write(f"Dado mais recente: {etf_most_recent_date}")
            st.dataframe(style_table(etf_table, numeric_cols_format_as_float=['Posição Hoje (%)', 'Posição Ontem (%)', 'Posição 21 dias atrás (%)']))

            # Asset selection for the chart
            asset_list = ['Todos'] + sorted(list(etf_table.index))
            selected_asset = st.selectbox('Selecione um ativo:', asset_list, key=f'asset_select_{selected_etf_name}')

            # Create the chart based on selection
            if selected_asset == 'Todos':
                etf_chart_data = data[selected_etf_col].dropna(how='all', axis=0).dropna(how='all', axis=1).rename(columns=CTA_DASHBOARD)
                etf_chart_options = create_chart(
                    data=etf_chart_data,
                    columns=list(etf_chart_data.columns),
                    names=list(etf_chart_data.columns),
                    chart_type='column',
                    stacking='normal',
                    title="Posições",
                    y_axis_title="Peso (%)",
                )
            else:
                # Chart for a single selected asset
                chart_data_single_asset = pd.merge(
                    data[selected_etf_col].rename(columns=lambda x: CTA_DASHBOARD.get(x, x)),
                    data['close'].rename(columns=lambda x: CTA_DASHBOARD.get(x, x)).add_suffix('_close'),
                    left_index=True,
                    right_index=True,
                    how='left'
                )
                etf_chart_options = create_chart(
                    data=chart_data_single_asset,
                    columns=[selected_asset + '_close', selected_asset],
                    names=["Preço ($)", "Peso (%)"],
                    chart_type='dual_axis_line_area',
                    stacking=None,
                    colors=["#19202a", "#cdb89b"],
                    title=f"Posição em {selected_asset.replace('_futures', '').replace('_', ' ').title()}",
                    y_axis_title=("Preço ($)", "Peso (%)"),
                )
            
            hct.streamlit_highcharts(etf_chart_options)
        else:
            st.warning(f"Não há dados de peso para o ETF {selected_etf_name}.")

    with tab_consolidado:
        st.subheader("Consolidado")

        all_cta_data = data.drop(columns='close').dropna(axis=0, how='all').iloc[-1]
        all_cta_most_recent_date = all_cta_data.name.date()
        all_cta_data = all_cta_data.to_frame('value').reset_index()
        all_cta_data = all_cta_data.pivot(index='code', columns='field', values='value')
        all_cta_data.index = all_cta_data.index.map(lambda x: CTA_DASHBOARD[x])

        all_cta_data['total'] = all_cta_data.mean(axis=1)
        all_cta_data.sort_values('total', ascending=False, inplace=True)
        all_cta_data.dropna(axis=0, subset='total', inplace=True)
        all_cta_data.drop('total', axis=1, inplace=True)

        st.write(f"Dado mais recente: {all_cta_most_recent_date}")
        st.dataframe(style_table(all_cta_data, numeric_cols_format_as_float=['weight_cta_invesco', 'weight_cta_kraneshares', 'weight_cta_simplify']))
        all_cta_chart_options = create_chart(
            data=all_cta_data.fillna(0),
            columns=['weight_cta_invesco', 'weight_cta_kraneshares', 'weight_cta_simplify'],
            names=['Invesco (IMF)', 'KraneShares (KMLM)', 'Simplify (CTA)'],
            chart_type='bar',
            stacking=None,
            title="Posições",
            y_axis_title="Peso (%)",
            x_axis_title="Ativos",
            height=800,
        )
        hct.streamlit_highcharts(all_cta_chart_options, height=800)
