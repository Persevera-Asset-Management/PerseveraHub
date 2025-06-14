import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
import streamlit_highcharts as hct
from persevera_tools.data import get_descriptors, get_securities_by_exchange
from configs.pages.carteira_rv import ACOES_RV

st.set_page_config(
    page_title="Carteira de RV | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()

st.title("Carteira de RV")

@st.cache_data(ttl=3600)
def load_active_securities():
    try:
        codes = get_securities_by_exchange(exchange='BZ')
        return list(codes.values())
    except Exception as e:
        st.error(f"Error loading active securities: {str(e)}")
        return []

def create_allocation_table(data):
    table = data.swaplevel(axis=1)['beta'].iloc[-1].to_frame("Bloomberg Beta")
    table['1 / Beta'] = 1.0 / table['Bloomberg Beta']
    table['Equal Weight (%)'] = 1.0 / len(table) * 100.0
    table['Final Weight (%)'] = table['1 / Beta'] / table['1 / Beta'].sum() * 100.0
    return table

active_securities = load_active_securities()

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_stocks = st.multiselect("Ações selecionadas", options=active_securities, default=ACOES_RV)

data = get_descriptors(selected_stocks, start_date=datetime.now() - timedelta(days=365), descriptors=['price_close', 'beta'])

if data.empty or len(selected_stocks) == 0:
    st.warning("Por favor, selecione ao menos uma ação para continuar.")
else:
    returns = data.swaplevel(axis=1)['price_close'].pct_change().dropna()

    st.subheader("Composição do Portfólio")
    allocation_table = create_allocation_table(data)
    st.dataframe(style_table(allocation_table, numeric_cols_format_as_float=['Bloomberg Beta', '1 / Beta'], percent_cols=['Equal Weight (%)', 'Final Weight (%)']))

    # st.subheader("Volatilidade do Portfólio")
    # st.metric("Volatilidade Anualizada Estimada", f"{portfolio_volatility:.2%}")

    # # Visualizações
    # st.subheader("Visualizações do Portfólio")

    # # Gráfico de Pizza dos Pesos
    # pie_data = [{'name': stock, 'y': weight} for stock, weight in weights.items()]
    # pie_chart = create_chart(
    #     series=[{'name': 'Pesos', 'data': pie_data, 'type': 'pie'}],
    #     title='Distribuição dos Pesos da Carteira',
    #     height=400
    # )
    # hct.streamlit_highcharts(pie_chart, height=400)

    # Mapa de Calor da Correlação
    correlation_matrix = returns.corr()
    correlation_matrix = correlation_matrix.where(np.tril(np.ones(correlation_matrix.shape)).astype(np.bool_))
    correlation_matrix = correlation_matrix.sort_index(ascending=False)

    heatmap = create_chart(
        data=correlation_matrix,
        chart_type='heatmap',
        title='Correlação dos Ativos',
    )
    hct.streamlit_highcharts(heatmap, height=500)