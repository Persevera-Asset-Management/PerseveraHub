import streamlit as st
from datetime import datetime, timedelta
from persevera_tools.data import FinancialDataService
from persevera_tools.data.funds import get_persevera_peers
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

st.set_page_config(
    page_title="Download de Dados | Persevera",
    page_icon=":hammer:",
    layout="wide"
)
display_logo()
load_css()
check_authentication()

st.title('Download de Dados')

st.markdown("Abaixo estão os botões que executam os scripts de download de dados.")

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data de Início", value=datetime.now() - timedelta(days=365), min_value=datetime(1900, 1, 1), max_value=datetime.now(), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

try:
    fds = FinancialDataService(start_date=start_date_str)
except Exception as e:
    st.error(f"Erro ao inicializar FinancialDataService: {e}")
    st.stop()

st.write("#### Dados Macroeconômicos")
row_1 = st.columns(3)

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

# SGS
with row_1[2]:
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

row_2 = st.columns(3)

# Focus (BCB)
with row_2[0]:
    if st.button('Focus (BCB)', use_container_width=True):
        try:
            with st.spinner('Baixando dados do Focus (BCB)...'):
                focus_data = fds.get_data(
                    source='bcb_focus',
                    save_to_db=True,
                )
            st.success('Dados do Focus (BCB) baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do Focus (BCB): {e}")

# Sidra
with row_2[1]:
    if st.button('Sidra', use_container_width=True):
        try:
            with st.spinner('Baixando dados do Sidra...'):
                sidra_data = fds.get_data(
                    source='sidra',
                    save_to_db=True,
                )
            st.success('Dados do Sidra baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do Sidra: {e}")

st.write("#### Fundos Sistemáticos (CTA)")
row_3 = st.columns(3)

# Simplify
with row_3[0]:
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

# Invesco
with row_3[1]:
    if st.button('Invesco', use_container_width=True):
        try:
            with st.spinner('Baixando dados do Invesco...'):
                simplify_data = fds.get_data(
                    source='invesco',
                    save_to_db=True,
                )
            st.success('Dados do Invesco baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do Simplify: {e}")

# KraneShares
with row_3[2]:
    if st.button('KraneShares', use_container_width=True):
        try:
            with st.spinner('Baixando dados do KraneShares...'):
                simplify_data = fds.get_data(
                    source='kraneshares',
                    save_to_db=True,
                )
            st.success('Dados do KraneShares baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do KraneShares: {e}")

# --- CVM --- 
st.write("#### Fundos de Investimento (CVM)")
row_4 = st.columns(3)

# Fundos de Investimento
with row_4[0]:
    if st.button('Todos os Fundos', use_container_width=True):
        try:
            with st.spinner('Baixando dados dos Fundos de Investimento...'):
                cnpjs = get_persevera_peers().fund_cnpj.drop_duplicates().tolist()
                cvm_data = fds.get_cvm_data(
                    cnpjs=cnpjs,
                    save_to_db=True
                )
            st.success('Dados dos Fundos de Investimento baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados dos Fundos de Investimento: {e}")

st.write("#### Crédito Privado")
row_5 = st.columns(3)

# Simplify
with row_5[0]:
    if st.button('Debentures.com.br', use_container_width=True):
        try:
            with st.spinner('Baixando dados do Debentures.com.br...'):
                debentures_data = fds.get_debentures_com_data(
                    save_to_db=True,
                )
            st.success('Dados do Debentures.com.br baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do Debentures.com.br: {e}")

