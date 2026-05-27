import streamlit as st
import pandas as pd
import numpy as np
import functools
from datetime import datetime, timedelta, date

from utils.ui import display_logo, load_css
from utils.auth import check_authentication

from services.financial_data_service import (
    SafeFinancialDataService,
    SOURCE_TO_PROVIDER,
)
from persevera_tools.db.fibery import read_fibery

st.set_page_config(
    page_title="Download de Dados | Persevera",
    page_icon=":hammer:",
    layout="wide"
)
display_logo()
load_css()
check_authentication()

st.title('Download de Dados')

def load_cnpjs():
    df = read_fibery(
        table_name="Inv-Taxonomia/Ativos",
        include_fibery_fields=False
    )
    cnpjs = df[np.isin(df["Classificação Instrumento"], ["Fundo de Investimento", "Previdência Privada"])]["Name"].drop_duplicates().tolist()
    return cnpjs

def create_download_button(
    column,
    label: str,
    data_source_name: str,
    download_function: callable,
    disabled: bool = False,
    disabled_reason: str = "",
):
    """
    Cria um botão de download em uma coluna específica do Streamlit.

    Args:
        column: A coluna do Streamlit onde o botão será posicionado.
        label (str): O texto do botão.
        data_source_name (str): O nome da fonte de dados para as mensagens.
        download_function (callable): A função a ser executada ao clicar no botão.
        disabled (bool): Se ``True``, o botão é renderizado desabilitado.
        disabled_reason (str): Mensagem exibida como tooltip quando o botão
            está desabilitado.
    """
    with column:
        help_text = disabled_reason if disabled else None
        if st.button(label, use_container_width=True, disabled=disabled, help=help_text):
            try:
                with st.spinner(f'Baixando dados de {data_source_name}...'):
                    download_function()
                st.success(f'Dados de {data_source_name} baixados e salvos com sucesso!')
            except Exception as e:
                st.error(f"Ocorreu um erro ao baixar os dados de {data_source_name}: {e}")

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data de Início", value=pd.to_datetime(date.today() - timedelta(days=365)), min_value=datetime(1900, 1, 1), max_value=pd.to_datetime(date.today()), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

fds = SafeFinancialDataService(start_date=start_date_str)

if fds.provider_errors:
    with st.expander(
        f"⚠️ {len(fds.provider_errors)} provider(s) indisponível(is) — botões correspondentes estão desabilitados",
        expanded=False,
    ):
        for provider_attr, error_msg in fds.provider_errors.items():
            st.warning(f"**{provider_attr}**: {error_msg}")


def _source_button_kwargs(source: str) -> dict:
    """Constrói os kwargs de estado (disabled/help) para um botão baseado em ``source``."""
    if fds.is_source_available(source):
        return {"disabled": False, "disabled_reason": ""}
    provider_attr = SOURCE_TO_PROVIDER.get(source, source)
    error_msg = fds.get_source_error(source) or "Provider indisponível."
    return {
        "disabled": True,
        "disabled_reason": f"Provider '{provider_attr}' indisponível: {error_msg}",
    }


def _provider_button_kwargs(provider_attr: str) -> dict:
    """Constrói os kwargs de estado (disabled/help) para um botão baseado num provider."""
    if fds.is_provider_available(provider_attr):
        return {"disabled": False, "disabled_reason": ""}
    error_msg = fds.get_provider_error(provider_attr) or "Provider indisponível."
    return {
        "disabled": True,
        "disabled_reason": f"Provider '{provider_attr}' indisponível: {error_msg}",
    }


cnpjs_error = None
try:
    with st.spinner("Carregando CNPJs...", show_time=True):
        cnpjs = load_cnpjs()
        if cnpjs is None:
            cnpjs = []
except Exception as e:
    cnpjs = []
    cnpjs_error = str(e)

# --- Dados Macroeconômicos ---
st.write("##### Dados Macroeconômicos")
macro_sources = [
    ("FRED", "FRED", "fred"),
    ("ANBIMA", "ANBIMA", "anbima_indices"),
    ("SGS", "SGS", "sgs"),
    ("Focus (BCB)", "Focus (BCB)", "bcb_focus"),
    ("Sidra", "Sidra", "sidra"),
    ("MDIC", "MDIC", "mdic"),
    ("B3 Flows (Investfy)", "B3 Flows (Investfy)", "investfy_investor_flow"),
]
rows_macro = [st.columns(3) for _ in range((len(macro_sources) + 2) // 3)]
for i, (label, name, source) in enumerate(macro_sources):
    download_func = functools.partial(fds.get_data, source=source, save_to_db=True)
    create_download_button(
        rows_macro[i // 3][i % 3],
        label,
        name,
        download_func,
        **_source_button_kwargs(source),
    )

# --- Fundos Sistemáticos (CTA) ---
st.write("##### Fundos Sistemáticos (CTA)")
cta_sources = [
    ("Simplify", "Simplify", "simplify"),
]
rows_cta = [st.columns(3) for _ in range((len(cta_sources) + 2) // 3)]
for i, (label, name, source) in enumerate(cta_sources):
    download_func = functools.partial(fds.get_data, source=source, save_to_db=True)
    create_download_button(
        rows_cta[i // 3][i % 3],
        label,
        name,
        download_func,
        **_source_button_kwargs(source),
    )

# --- Fundos de Investimento ---
st.write("##### Fundos de Investimento")
row_cvm = st.columns(3)

if cnpjs_error is not None:
    st.error(f"Ocorreu um erro ao obter a lista de CNPJs para os fundos: {cnpjs_error}")

cnpjs_disabled_reason = (
    f"Lista de CNPJs indisponível: {cnpjs_error}" if cnpjs_error else ""
)

def _fund_button_kwargs(provider_attr: str) -> dict:
    """Combina indisponibilidade do provider com falha no carregamento dos CNPJs."""
    if cnpjs_error is not None:
        return {"disabled": True, "disabled_reason": cnpjs_disabled_reason}
    return _provider_button_kwargs(provider_attr)


cvm_download_func = functools.partial(fds.get_cvm_data, source='cvm', cnpjs=cnpjs, save_to_db=True)
create_download_button(
    row_cvm[0],
    "CVM",
    "CVM",
    cvm_download_func,
    **_fund_button_kwargs('cvm'),
)

anbima_fundos_download_func = functools.partial(fds.get_anbima_fundos_serie_historica, cnpjs=cnpjs)
create_download_button(
    row_cvm[1],
    "Anbima Fundos",
    "Anbima Fundos",
    anbima_fundos_download_func,
    **_fund_button_kwargs('anbima_fundos'),
)

mais_retorno_download_func = functools.partial(fds.get_data, source='mais_retorno_fundos', primary_keys=['fund_cnpj', 'date'], save_to_db=True)
create_download_button(
    row_cvm[2],
    "Mais Retorno (FIDC)",
    "Mais Retorno (FIDC)",
    mais_retorno_download_func,
    **_fund_button_kwargs('mais_retorno'),
)


# --- Crédito Privado ---
st.write("##### Crédito Privado")
credito_privado_sources = [
    ("Debentures.com.br", "Debentures.com.br", "debentures_com", ["code"]),
    ("ANBIMA (Debentures)", "ANBIMA (Debentures)", "anbima_debentures", ["date", "code", "field", "source"]),
    ("ANBIMA (Títulos Públicos)", "ANBIMA (Títulos Públicos)", "anbima_titulos_publicos", ["date", "code", "field", "maturity"]),
    ("ANBIMA (CRI/CRA)", "ANBIMA (CRI/CRA)", "anbima_cri_cra", ["date", "code", "field", "source"]),
    ("B3 (BDI)", "B3 (BDI)", "b3_bdi", ["date", "code", "field", "source"]),
    ("Mais Retorno", "Mais Retorno", "mais_retorno_debentures", ["date", "code", "field", "source"]),
]
rows_credito_privado = [st.columns(3) for _ in range((len(credito_privado_sources) + 2) // 3)]
for i, (label, name, source, primary_keys) in enumerate(credito_privado_sources):
    download_func = functools.partial(fds.get_data, source=source, primary_keys=primary_keys, save_to_db=True)
    create_download_button(
        rows_credito_privado[i // 3][i % 3],
        label,
        name,
        download_func,
        **_source_button_kwargs(source),
    )
