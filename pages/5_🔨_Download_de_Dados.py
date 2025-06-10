import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from persevera_tools.data import get_series
from utils.chart_helpers import create_chart
import streamlit_highcharts as hct
import requests
import json
import io
from persevera_tools.data import FinancialDataService
from utils.ui import display_logo, load_css

st.set_page_config(
    page_title="Download de Dados | Persevera",
    page_icon=":hammer:",
    layout="wide"
)

display_logo()
load_css()

st.title('Download de Dados')

st.markdown("Abaixo estão os botões que executam os scripts de download de dados.")

# --- Inputs do Usuário --- 
st.sidebar.header("Configurações")

start_date = st.sidebar.date_input("Data de Início", value=datetime.now() - timedelta(days=365), min_value=datetime(1900, 1, 1), max_value=datetime.now(), format="DD/MM/YYYY")
start_date_str = start_date.strftime('%Y-%m-%d')

try:
    fds = FinancialDataService(start_date=start_date_str)
except Exception as e:
    st.error(f"Erro ao inicializar FinancialDataService: {e}")
    st.stop()

row_1 = st.columns(3)

# FRED
with row_1[0]:
    if st.button('Baixar dados do FRED', use_container_width=True):
        try:
            with st.spinner('Baixando dados do FRED...'):
                fred_data = fds.get_data(
                    source='fred',
                    save_to_db=True
                )
            st.success('Dados do FRED baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do FRED: {e}")

# ANBIMA
with row_1[1]:
    if st.button('Baixar dados da ANBIMA', use_container_width=True):
        try:
            with st.spinner('Baixando dados da ANBIMA...'):
                anbima_data = fds.get_data(
                    source='anbima',
                    save_to_db=True
                )
            st.success('Dados da ANBIMA baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados da ANBIMA: {e}")

# Simplify
with row_1[2]:
    if st.button('Baixar dados do Simplify', use_container_width=True):
        try:
            with st.spinner('Baixando dados do Simplify...'):
                simplify_data = fds.get_data(
                    source='simplify',
                    save_to_db=True,
                )
            st.success('Dados do Simplify baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do Simplify: {e}")

