import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import streamlit_highcharts as hct
from persevera_tools.data import get_series
from utils.chart_helpers import extract_codes_from_config, create_chart
from configs.pages.fluxo_de_investimentos import FLUXO_DE_INVESTIMENTOS
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

st.set_page_config(
    page_title="Fluxo de Investimentos | Persevera",
    page_icon="🪙",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title('Fluxo de Investimentos')

@st.cache_data(ttl=3600)
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", min_value=datetime(1990, 1, 1), value=datetime(2015, 1, 1), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

data = load_data(list(FLUXO_DE_INVESTIMENTOS.keys()), start_date=start_date_str)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    st.header("Fluxo de Investimentos")

    cols = st.columns(2)
    with cols[0]:
        st.subheader("Saldo Diário")
        selected_group = st.selectbox("Selecione o grupo:", list(FLUXO_DE_INVESTIMENTOS.keys()))
        selected_group_name = FLUXO_DE_INVESTIMENTOS[selected_group]
        selected_group_data = data[selected_group].to_frame(selected_group_name)
        chart_options = create_chart(
            data=selected_group_data,
            columns=selected_group_name,
            names=selected_group_name,
            chart_type='column',
            title=f'Saldo Diário: {selected_group_name}',
            y_axis_title="Fluxo Diário (R$)",
            decimal_precision=0,
        )
        hct.streamlit_highcharts(chart_options)

    with cols[1]:
        st.subheader("Saldo Acumulado")
        latest_date = data.index.max()
        period_options = {
            "No Mês": f"{latest_date.strftime('%Y-%m')}",
            "No Ano": f"{latest_date.strftime('%Y')}",
            "30 Dias": f"{latest_date - timedelta(days=30)}",
            "1 Ano": f"{latest_date - timedelta(days=365)}",
            "2 Anos": f"{latest_date - timedelta(days=365*2)}",
        } 
        selected_period = st.selectbox("Selecione o período:", period_options.keys())
        selected_period = period_options[selected_period]
        selected_data = data.loc[selected_period:].expanding().sum()
        selected_data.rename(FLUXO_DE_INVESTIMENTOS, axis='columns', inplace=True)
        cumulative_chart_options = create_chart(
            data=selected_data,
            columns=selected_data.columns.tolist(),
            names=selected_data.columns.tolist(),
            chart_type='spline',
            title='Saldo Acumulado',
            y_axis_title="Fluxo Acumulado (R$)",
            decimal_precision=0,
        )
        hct.streamlit_highcharts(cumulative_chart_options)
