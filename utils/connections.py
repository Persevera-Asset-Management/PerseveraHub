from persevera_tools.data import FinancialDataService
import streamlit as st

@st.cache_resource
def get_financial_data_service(start_date):
    """
    Inicializa e retorna uma instância única do FinancialDataService.
    Usa st.singleton para garantir que a conexão com a API (ex: Bloomberg)
    seja estabelecida apenas uma vez.
    """
    try:
        fds = FinancialDataService(start_date=start_date)
        return fds
    except Exception as e:
        st.error(f"Erro ao inicializar FinancialDataService: {e}")
        return None 