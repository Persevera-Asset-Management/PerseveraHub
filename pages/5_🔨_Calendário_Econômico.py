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

try:
    fds = FinancialDataService(start_date="2025-01-01")
except Exception as e:
    st.error(f"Erro ao inicializar FinancialDataService: {e}")
    st.stop()

with st.spinner("Carregando dados..."):
    try:
        calendar_data = fds.get_investing_calendar_data(
            save_to_db=False
        )
        calendar_data.set_index('date', inplace=True)
        st.dataframe(calendar_data)
    except Exception as e:
        st.error(f"Ocorreu um erro ao baixar os dados do Calendário Econômico: {e}")
