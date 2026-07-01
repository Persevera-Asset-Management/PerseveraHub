import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from configs.pages.market_breadth import INDICADORES

from utils.chart_helpers import create_chart
from utils.table import style_table

import streamlit_highcharts as hct

from persevera_tools.data import get_series

st.title('Market Breadth')

@st.cache_data(ttl=3600)
def load_data(codes, field, start_date):
    try:
        return get_series(codes, start_date=start_date, field=field)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", min_value=datetime(2010, 1, 1), value=datetime(2010, 1, 1), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

# Load data with progress indicator
with st.spinner("Carregando dados dos índices...", show_time=True):
    data = load_data(list(INDICADORES.keys()), field=['close', 'pct_members_above_50dma', 'pct_members_above_100dma', 'pct_members_above_150dma', 'pct_members_above_200dma'], start_date=start_date_str)
    data.ffill(inplace=True, limit=1)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    # Tabela consolidada
    st.subheader("Tabela Consolidada")
    st.markdown(f"Dado mais recente: `{data.index.max().date()}`")
    consolidated_data = data.iloc[-1].to_frame('value').reset_index()
    consolidated_data = consolidated_data.pivot(index='code', columns='field', values='value')
    consolidated_data.index = consolidated_data.index.map(lambda x: INDICADORES[x])
    
    st.dataframe(
        style_table(
            consolidated_data,
            column_names=['Fechamento', '% > 50DMA', '% > 100DMA', '% > 150DMA', '% > 200DMA'],
            numeric_cols_format_as_int=['Fechamento'],
            percent_cols=['% > 100DMA', '% > 150DMA', '% > 200DMA', '% > 50DMA']
        ),
    )

    # Por índice
    st.subheader("Por Índice")
    selected_index = st.columns(2)[0].selectbox("Selecione o índice:", list(consolidated_data.index))
    value_selected = [k for k,v in INDICADORES.items() if v == selected_index][0]
    selected_index_data = data[value_selected]
    
    chart_breadth = create_chart(
        data=selected_index_data,
        columns=(['close'], ['pct_members_above_50dma', 'pct_members_above_100dma', 'pct_members_above_150dma', 'pct_members_above_200dma']),
        names=(['Fechamento'], ['% > 50DMA', '% > 100DMA', '% > 150DMA', '% > 200DMA']),
        chart_type='dual_axis_line',
        title=f"Breadth de {selected_index}",
        y_axis_title=("Fechamento", "% de membros acima de"),
        y_axis_max=(None, 100),
    )
    hct.streamlit_highcharts(chart_breadth)
