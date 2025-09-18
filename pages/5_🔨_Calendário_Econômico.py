import streamlit as st
from persevera_tools.data import FinancialDataService
from utils.ui import display_logo, load_css
from utils.auth import check_authentication
from utils.table import style_table

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

with st.spinner("Carregando dados...", show_time=True):
    try:
        calendar_data = fds.get_investing_calendar_data(save_to_db=False)
        
        # Estados Unidos
        st.subheader('Estados Unidos')
        st.dataframe(style_table(
            calendar_data[calendar_data['country'] == 'United States'],
            highlight_row_by_column='Importância',
            highlight_row_if_value_equals='High',
            column_names=['Data','Id', 'País', 'Moeda', 'Nome', 'Importância', 'URL'],
        ), hide_index=True)

        # Brasil
        st.subheader('Brasil')
        st.dataframe(style_table(
            calendar_data[calendar_data['country'] == 'Brazil'],
            highlight_row_by_column='Importância',
            highlight_row_if_value_equals='High',
            column_names=['Data','Id', 'País', 'Moeda', 'Nome', 'Importância', 'URL'],
        ), hide_index=True)

    except Exception as e:
        st.error(f"Ocorreu um erro ao baixar os dados do Calendário Econômico: {e}")
