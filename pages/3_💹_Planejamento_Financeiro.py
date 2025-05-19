import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from persevera_tools.data import get_descriptors, get_securities_by_exchange, get_equities_info

st.set_page_config(
    page_title="Planejamento Financeiro | Persevera",
    page_icon="�",
    layout="wide"
)

st.title("Planejamento Financeiro")

st.sidebar.header("Parâmetros")

patrimonio_inicial = st.sidebar.number_input("Patrimônio Inicial (R$):", min_value=0.0, value=100000.0, step=10000.0, format=".0f")
horizonte_temporal = st.sidebar.number_input("Horizonte Temporal (anos):", min_value=1.0, value=10.0, step=1.0, format=".0f")
resgate_mensal = st.sidebar.number_input("Resgate Mensal (R$):", min_value=0.0, value=10000.0, step=1000.0, format=".0f")
aporte_mensal = st.sidebar.number_input("Aporte Mensal (R$):", min_value=0.0, value=10000.0, step=1000.0, format=".0f")
rentabilidade_anual_desejada = st.sidebar.number_input("Rentabilidade Anual Esperada (%):", min_value=0.0, value=10.0, step=0.1, format=".1f")
inflacao_anual_desejada = st.sidebar.number_input("Inflação Anual Esperada (%):", min_value=0.0, value=2.0, step=0.1, format=".1f")
aliquota_irrf = st.sidebar.number_input("Alíquota de Impostos (%):", min_value=0.0, value=15.0, step=0.1, format=".1f")






