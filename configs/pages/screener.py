import pandas as pd
import streamlit as st

from persevera_tools.db.fibery import read_fibery


@st.cache_data(ttl=3600)
def load_factor_definitions() -> pd.DataFrame:
    try:
        df = read_fibery(
            table_name="Inv-Rsrch-Quant/Definições dos Fatores",
            include_fibery_fields=False,
        )
        df = df[df["state"] == "Ativo"]
        return df[["Name", "Alias", "Descrição", "Maior Melhor", "Estilo"]]
    except Exception as e:
        st.error(f"Error loading factor definitions: {str(e)}")
        return pd.DataFrame(columns=["Name", "Alias", "Descrição", "Maior Melhor", "Estilo"])


FACTOR_DEFINITIONS = load_factor_definitions()


def get_factor_options(definitions: pd.DataFrame = FACTOR_DEFINITIONS) -> dict:
    """Return {Alias: Name} for every active factor."""
    if definitions.empty:
        return {}
    return definitions.set_index('Alias')['Name'].to_dict()


def get_factor_components(style: str, definitions: pd.DataFrame = FACTOR_DEFINITIONS) -> dict:
    """Return {Alias: Name} for factors tagged with the given style in the `Estilo` column."""
    if definitions.empty or 'Estilo' not in definitions.columns:
        return {}
    mask = definitions['Estilo'].apply(
        lambda styles: isinstance(styles, list) and style in styles
    )
    return definitions.loc[mask].set_index('Alias')['Name'].to_dict()


def get_higher_is_better_map(definitions: pd.DataFrame = FACTOR_DEFINITIONS) -> dict:
    """Return {Name: bool} indicating whether higher values are better for each factor."""
    if definitions.empty:
        return {}
    return definitions.set_index('Name')['Maior Melhor'].astype(bool).to_dict()
