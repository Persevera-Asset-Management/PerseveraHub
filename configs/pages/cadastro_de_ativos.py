import pandas as pd
from persevera_tools.db.operations import read_sql
from persevera_tools.data.funds import get_persevera_peers

def get_funds_groups():
    df = get_persevera_peers()
    return sorted(df["persevera_group"].unique().tolist())

def get_indicators_categories():
    df = read_sql(
        sql_query="""
            SELECT DISTINCT category FROM indicadores_definicoes
        """
    )
    return sorted(df["category"].unique().tolist())

def get_indicators_sources():
    df = read_sql(
        sql_query="""
            SELECT DISTINCT source FROM indicadores_definicoes
        """
    )
    return sorted(df["source"].unique().tolist())

INDICADORES_CATEGORIAS = get_indicators_categories()
GRUPOS_FUNDOS = get_funds_groups()
INDICADORES_SOURCES = get_indicators_sources()


ASSET_CONFIG = {
    "Fundo": {
        "form_name": "form_fundo",
        "table_name": "fundos_persevera_peers",
        "primary_keys": ["fund_cnpj", "persevera_group"],
        "update": True,
        "fields": [
            {"label": "CNPJ do Fundo", "id": "fund_cnpj", "type": "text_input"},
            {"label": "Nome do Fundo", "id": "short_name", "type": "text_input"},
            {
                "label": "Grupo do Fundo",
                "id": "persevera_group",
                "type": "selectbox",
                "options": GRUPOS_FUNDOS,
            },
        ],
    },
    "Indicador": {
        "form_name": "form_indicador",
        "table_name": "indicadores_definicoes",
        "primary_keys": None,
        "update": False,
        "fields": [
            {"label": "Código Bruto", "id": "raw_code", "type": "text_input"},
            {
                "label": "Código do Indicador (Mneumônico)",
                "id": "code",
                "type": "text_input",
            },
            {
                "label": "Categoria",
                "id": "category",
                "type": "selectbox",
                "options": INDICADORES_CATEGORIAS,
            },
            {
                "label": "Fonte",
                "id": "source",
                "type": "selectbox",
                "options": INDICADORES_SOURCES,
            },
        ],
    },
}