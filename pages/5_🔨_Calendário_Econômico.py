import streamlit as st
from datetime import datetime, timedelta
from persevera_tools.data import FinancialDataService
from persevera_tools.data.funds import get_persevera_peers
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

st.set_page_config(
    page_title="Calendário Econômico | Persevera",
    page_icon=":hammer:",
    layout="wide"
)
display_logo()
load_css()
check_authentication()

st.title('Calendário Econômico')

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data de Início", value=datetime.now() - timedelta(days=365), min_value=datetime(1900, 1, 1), max_value=datetime.now(), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')
    btn_run = st.button("Run")

try:
    fds = FinancialDataService(start_date=start_date_str)
except Exception as e:
    st.error(f"Erro ao inicializar FinancialDataService: {e}")
    st.stop()

if btn_run:
    with st.spinner("Carregando dados..."):
        try:
            calendar_data = fds.get_investing_calendar_data(
                save_to_db=False
            )
            st.success('Dados do Calendário Econômico baixados e salvos com sucesso!')
        except Exception as e:
            st.error(f"Ocorreu um erro ao baixar os dados do Calendário Econômico: {e}")

    st.write(calendar_data)
