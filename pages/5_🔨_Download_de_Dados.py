import streamlit as st
from datetime import datetime, timedelta
from persevera_tools.data import FinancialDataService
from persevera_tools.data.funds import get_persevera_peers
from persevera_tools.data.sma import get_building_blocks
from utils.ui import display_logo, load_css
from utils.auth import check_authentication
import functools

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

def create_download_button(column, label: str, data_source_name: str, download_function: callable):
    """
    Cria um botão de download em uma coluna específica do Streamlit.

    Args:
        column: A coluna do Streamlit onde o botão será posicionado.
        label (str): O texto do botão.
        data_source_name (str): O nome da fonte de dados para as mensagens.
        download_function (callable): A função a ser executada ao clicar no botão.
    """
    with column:
        if st.button(label, use_container_width=True):
            try:
                with st.spinner(f'Baixando dados de {data_source_name}...'):
                    download_function()
                st.success(f'Dados de {data_source_name} baixados e salvos com sucesso!')
            except Exception as e:
                st.error(f"Ocorreu um erro ao baixar os dados de {data_source_name}: {e}")

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data de Início", value=datetime.now() - timedelta(days=365), min_value=datetime(1900, 1, 1), max_value=datetime.now(), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

try:
    fds = FinancialDataService(start_date=start_date_str)
except Exception as e:
    st.error(f"Erro ao inicializar FinancialDataService: {e}")
    st.stop()

# --- Dados Macroeconômicos ---
st.write("##### Dados Macroeconômicos")
macro_sources = [
    ("FRED", "FRED", "fred"),
    ("ANBIMA", "ANBIMA", "anbima"),
    ("SGS", "SGS", "sgs"),
    ("Focus (BCB)", "Focus (BCB)", "bcb_focus"),
    ("Sidra", "Sidra", "sidra"),
    ("MDIC", "MDIC", "mdic"),
]
rows_macro = [st.columns(3) for _ in range((len(macro_sources) + 2) // 3)]
for i, (label, name, source) in enumerate(macro_sources):
    download_func = functools.partial(fds.get_data, source=source, save_to_db=True)
    create_download_button(rows_macro[i // 3][i % 3], label, name, download_func)

# --- Fundos Sistemáticos (CTA) ---
st.write("##### Fundos Sistemáticos (CTA)")
cta_sources = [
    ("Simplify", "Simplify", "simplify"),
    ("Invesco", "Invesco", "invesco"),
    ("KraneShares", "KraneShares", "kraneshares"),
]
rows_cta = [st.columns(3) for _ in range((len(cta_sources) + 2) // 3)]
for i, (label, name, source) in enumerate(cta_sources):
    download_func = functools.partial(fds.get_data, source=source, save_to_db=True)
    create_download_button(rows_cta[i // 3][i % 3], label, name, download_func)

# --- Fundos de Investimento (CVM) --- 
st.write("##### Fundos de Investimento (CVM)")
row_cvm = st.columns(3)
try:
    cnpjs_peers = get_persevera_peers().fund_cnpj.drop_duplicates().tolist()
    cnpjs_building_blocks = get_building_blocks().query('instrument == "FI"').code.drop_duplicates().tolist()
    cnpjs = cnpjs_peers + cnpjs_building_blocks
    cvm_download_func = functools.partial(fds.get_cvm_data, cnpjs=cnpjs, save_to_db=True)
    create_download_button(row_cvm[0], "Todos os Fundos", "Fundos de Investimento", cvm_download_func)
except Exception as e:
    st.error(f"Ocorreu um erro ao obter a lista de CNPJs para os fundos: {e}")


# --- Crédito Privado ---
st.write("##### Crédito Privado")
row_credito = st.columns(3)

# Debentures.com.br
debentures_com_func = functools.partial(fds.get_debentures_com_data, save_to_db=True)
create_download_button(row_credito[0], "Debentures.com.br", "Debentures.com.br", debentures_com_func)

# ANBIMA (Debentures)
anbima_debentures_func = functools.partial(fds.get_anbima_debentures_data, save_to_db=True)
create_download_button(row_credito[1], "ANBIMA (Debentures)", "ANBIMA (Debentures)", anbima_debentures_func)
