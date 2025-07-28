import streamlit as st
import pandas as pd
import os
from utils.auth import check_authentication
from utils.ui import display_logo, load_css
from persevera_tools.db.operations import to_sql
from configs.pages.cadastro_de_ativos import ASSET_CONFIG

st.set_page_config(
    page_title="Cadastro de Ativos",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="expanded",
)
display_logo()
load_css()
check_authentication()

st.title("Cadastro de Ativos")


def build_form(asset_type: str):
    """Gera um formulário dinâmico com base no tipo de ativo."""
    config = ASSET_CONFIG[asset_type]
    with st.form(config["form_name"], clear_on_submit=True):
        form_data = {}
        for field in config["fields"]:
            if field["type"] == "text_input":
                form_data[field["id"]] = st.text_input(field["label"])
            elif field["type"] == "selectbox":
                form_data[field["id"]] = st.selectbox(
                    field["label"], options=field["options"]
                )

        submitted = st.form_submit_button(f"Cadastrar {asset_type}")

        if submitted:
            # Validação dos campos
            empty_fields = [
                field["label"] for field_id, value in form_data.items() if not value for field in config["fields"] if field["id"] == field_id
            ]

            if empty_fields:
                st.warning(
                    f"Por favor, preencha os seguintes campos: {', '.join(empty_fields)}"
                )
            else:
                try:
                    df = pd.DataFrame({k: [v] for k, v in form_data.items()})
                    with st.spinner(f"Cadastrando {asset_type.lower()}..."):
                        to_sql(
                            data=df,
                            table_name=config["table_name"],
                            primary_keys=config["primary_keys"],
                            update=config["update"],
                        )
                        st.success(f"{asset_type} cadastrado com sucesso!")
                except Exception as e:
                    st.error(
                        f"Ocorreu um erro ao cadastrar o {asset_type.lower()}: {e}"
                    )


# Interface principal
tipo_ativo = st.radio(
    "Selecione o tipo de ativo a ser cadastrado:",
    options=list(ASSET_CONFIG.keys()),
    horizontal=True,
)

if tipo_ativo:
    build_form(tipo_ativo)
