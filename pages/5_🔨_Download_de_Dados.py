import streamlit as st
from datetime import datetime, timedelta
from xbbg import blp
from utils.ui import display_logo, load_css
from utils.connections import get_financial_data_service

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

fds = get_financial_data_service(start_date=start_date_str)

if not fds:
    st.error("Não foi possível inicializar o serviço de dados financeiros. As operações de download estão desabilitadas.")
    st.stop()

# --- Fontes Independentes --- 
st.write("#### Fontes Independentes")
row_1 = st.columns(4)

# FRED
with row_1[0]:
    if st.button('FRED', use_container_width=True):
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
    if st.button('ANBIMA', use_container_width=True):
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
    if st.button('Simplify', use_container_width=True):
        try:
            with st.spinner('Baixando dados do Simplify...'):
                simplify_data = fds.get_data(
                    source='simplify',
                    save_to_db=True,
                )
            st.success('Dados do Simplify baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do Simplify: {e}")

# SGS
with row_1[3]:
    if st.button('SGS', use_container_width=True):
        try:
            with st.spinner('Baixando dados do SGS...'):
                sgs_data = fds.get_data(
                    source='sgs',
                    save_to_db=True,
                )
            st.success('Dados do SGS baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do SGS: {e}")

st.write("#### Bloomberg")
row_2 = st.columns(4)

# --- Bloomberg ---
# Commodity
with row_2[0]:
    if st.button('Commodity', use_container_width=True):
        try:
            with st.spinner('Baixando dados do Bloomberg...'):
                bloomberg_data = fds.get_bloomberg_data(
                    category='commodity',
                    data_type='market',
                    save_to_db=True
                )
            st.success('Dados do Bloomberg/Commodity baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do Bloomberg: {e}")

# Equity
with row_2[1]:
    if st.button('Equity', use_container_width=True):
        try:
            with st.spinner('Baixando dados do Bloomberg...'):
                bloomberg_data = fds.get_bloomberg_data(
                    category='equity',
                    data_type='market',
                    save_to_db=True
                )
            st.success('Dados do Bloomberg/Equity baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do Bloomberg: {e}")

# FX
with row_2[2]:
    if st.button('Currency', use_container_width=True):
        try:
            with st.spinner('Baixando dados do Bloomberg...'):
                bloomberg_data = fds.get_bloomberg_data(
                    category='currency',
                    data_type='market',
                    save_to_db=True
                )
            st.success('Dados do Bloomberg/Currency baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do Bloomberg: {e}")