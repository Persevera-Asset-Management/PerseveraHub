import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date

import streamlit as st
import streamlit_highcharts as hct

from utils.chart_helpers import create_chart
from utils.table import style_table

from persevera_tools.fixed_income import get_emissions, calculate_spread
from persevera_tools.data import get_series


st.title("Spreads de Crédito")

@st.cache_data(ttl=7200)
def load_data(codes, start_date):
    try:
        fields = [
            'mean',
            'median',
            'weighted_mean',
            'count_above_mean',
            'count_under_mean',
            'count_yield_under_neg50bp',
            'count_yield_neg50_0bp',
            'count_yield_0_50bp',
            'count_yield_50_75bp',
            'count_yield_75_100bp',
            'count_yield_100_150bp',
            'count_yield_150_250bp',
            'count_yield_above_250bp',
            'volume_above_mean',
            'volume_under_mean'
        ]        
        return get_series(codes, start_date=start_date, field=fields)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()


with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", pd.to_datetime(date.today() - timedelta(days=4*365)), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

with st.spinner("Carregando dados de spreads...", show_time=True):
    codes = ['persevera_anbima_debentures_spread_di', 'persevera_anbima_debentures_spread_ipca_incent']
    data_spreads = load_data(codes, start_date=start_date_str)

if data_spreads.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    tabs = st.tabs(["CDI+", "IPCA+"])
    # Tab 1: Spread CDI+
    with tabs[0]:
        st.subheader("CDI+")

        row_1 = st.columns(2)
        with row_1[0]:
            chart_spread_cdi = create_chart(
                data=data_spreads["persevera_anbima_debentures_spread_di"],
                columns=["median", "mean", "weighted_mean"],
                names=["Mediana", "Média", "Média Ponderada"],
                chart_type='line',
                title="Evolução do Spread CDI+",
                y_axis_title="Spread (%)",
                decimal_precision=3
            )
            hct.streamlit_highcharts(chart_spread_cdi)

        with row_1[1]:
            chart_distribution_cdi = create_chart(
                data=data_spreads["persevera_anbima_debentures_spread_di"],
                columns=['count_yield_0_50bp', 'count_yield_50_75bp', 'count_yield_75_100bp',
                         'count_yield_100_150bp', 'count_yield_150_250bp',
                         'count_yield_above_250bp'],
                names=["0-50bp", "50-75bp", "75-100bp", "100-150bp", "150-250bp", "Acima de 250bp"],
                chart_type='area',
                stacking='percent',
                title="Distribuição do Spread CDI+ por Intervalo",
                y_axis_title="Percentual de Ativos (%)",
                decimal_precision=0
            )
            hct.streamlit_highcharts(chart_distribution_cdi)
    
        row_2 = st.columns(2)
        with row_2[0]:
            chart_average_count_cdi = create_chart(
                data=data_spreads["persevera_anbima_debentures_spread_di"],
                columns=['count_above_mean', 'count_under_mean'],
                names=["Acima da Média", "Abaixo da Média"],
                chart_type='area',
                stacking='percent',
                title="Distribuição do Spread CDI+ (Contagem de Ativos)",
                y_axis_title="Percentual de Ativos (%)",
                decimal_precision=0,
            )
            hct.streamlit_highcharts(chart_average_count_cdi)

        with row_2[1]:
            chart_average_volume_cdi = create_chart(
                data=data_spreads["persevera_anbima_debentures_spread_di"],
                columns=['volume_above_mean', 'volume_under_mean'],
                names=["Acima da Média", "Abaixo da Média"],
                chart_type='area',
                stacking='percent',
                title="Distribuição do Spread CDI+ (Volume Emitido)",
                y_axis_title="Percentual de Ativos (%)",
                decimal_precision=0,
            )
            hct.streamlit_highcharts(chart_average_volume_cdi)

    # Tab 3: Spread IPCA
    with tabs[1]:
        # Incentivado
        st.subheader("IPCA+ Incentivado")

        row_1 = st.columns(2)
        with row_1[0]:
            chart_spread_ipca_incent = create_chart(
                data=data_spreads["persevera_anbima_debentures_spread_ipca_incent"],
                columns=["median", "mean", "weighted_mean"],
                names=["Mediana", "Média", "Média Ponderada"],
                chart_type='line',
                title="Evolução do Spread IPCA+ Incentivado",
                y_axis_title="Spread (%)",
                decimal_precision=3
            )
            hct.streamlit_highcharts(chart_spread_ipca_incent)

        with row_1[1]:
            chart_distribution_ipca_incent = create_chart(
                data=data_spreads["persevera_anbima_debentures_spread_ipca_incent"],
                columns=['count_yield_under_neg50bp', 'count_yield_neg50_0bp',
                         'count_yield_0_50bp', 'count_yield_50_75bp', 'count_yield_75_100bp',
                         'count_yield_100_150bp', 'count_yield_150_250bp',
                         'count_yield_above_250bp'],
                names=["Abaixo de -50bp", "-50bp a 0bp", "0-50bp", "50-75bp", "75-100bp", "100-150bp", "150-250bp", "Acima de 250bp"],
                chart_type='area',
                stacking='percent',
                title="Distribuição do Spread IPCA+ Incentivado por Intervalo",
                y_axis_title="Percentual de Ativos (%)",
                decimal_precision=0
            )
            hct.streamlit_highcharts(chart_distribution_ipca_incent)
    
        row_2 = st.columns(2)
        with row_2[0]:
            chart_average_count_ipca_incent = create_chart(
                data=data_spreads["persevera_anbima_debentures_spread_ipca_incent"],
                columns=['count_above_mean', 'count_under_mean'],
                names=["Acima da Média", "Abaixo da Média"],
                chart_type='area',
                stacking='percent',
                title="Distribuição do Spread IPCA+ Incentivado (Contagem de Ativos)",
                y_axis_title="Percentual de Ativos (%)",
                decimal_precision=0,
            )
            hct.streamlit_highcharts(chart_average_count_ipca_incent)

        with row_2[1]:
            chart_average_volume_ipca_incent = create_chart(
                data=data_spreads["persevera_anbima_debentures_spread_ipca_incent"],
                columns=['volume_above_mean', 'volume_under_mean'],
                names=["Acima da Média", "Abaixo da Média"],
                chart_type='area',
                stacking='percent',
                title="Distribuição do Spread IPCA+ Incentivado (Volume Emitido)",
                y_axis_title="Percentual de Ativos (%)",
                decimal_precision=0,
            )
            hct.streamlit_highcharts(chart_average_volume_ipca_incent)
