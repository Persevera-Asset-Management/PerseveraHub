import pandas as pd
import numpy as np
import streamlit as st

from utils.ui import show_data_freshness
from utils.table import style_table

from configs.pages.carteiras_administradas import CODIGOS_CARTEIRAS_ADM
from services.position_service import (
    load_positions,
    get_latest_date_data,
    get_emissor_column,
)


RF_CLASSES = [
    "Renda Fixa Pós-Fixada",
    "Renda Fixa Atrelada à Inflação",
    "Renda Fixa Pré-Fixada",
    "Investimentos Alternativos",
]

KPI_THRESHOLDS = [15, 30, 90]


def prepare_base_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    df.replace(" ", np.nan, inplace=True)
    df.dropna(subset=["Nome Ativo", "Classificação do Conjunto"], inplace=True)
    df = get_emissor_column(df)
    df.rename(columns={"Emissor": "Emissor Geral"}, inplace=True)
    return df


def prepare_maturity_positions(df: pd.DataFrame) -> pd.DataFrame:
    df_maturity = df.groupby(
        [
            "Portfolio",
            pd.Grouper(key="Data Posição", freq="D"),
            "Nome Ativo",
            "Alias",
            "Classificação do Conjunto",
            "Classificação Instrumento",
            "Data Vencimento",
        ]
    ).agg(
        **{
            "Quantidade": ("Quantidade", "sum"),
            "Valor Unitário": ("Valor Unitário", "mean"),
            "Saldo": ("Saldo", "sum"),
        }
    )
    df_current = get_latest_date_data(
        df_maturity, level="Data Posição", group_level="Portfolio"
    ).copy()
    df_current = df_current.reset_index().set_index(["Portfolio", "Nome Ativo"])
    df_current["Data Vencimento"] = pd.to_datetime(df_current["Data Vencimento"])
    df_current = df_current[df_current["Saldo"] > 0]
    df_current["Dias para Vencimento"] = np.busday_count(
        df_current["Data Posição"].values.astype("datetime64[D]"),
        df_current["Data Vencimento"].values.astype("datetime64[D]"),
    )
    df_current["Anos para Vencimento"] = df_current["Dias para Vencimento"] / 252
    return df_current.sort_values(by="Dias para Vencimento", ascending=True)


def maturity_kpis(df: pd.DataFrame, thresholds: list[int]) -> dict[int, float]:
    return {
        threshold: float(df.loc[df["Dias para Vencimento"] <= threshold, "Saldo"].sum())
        for threshold in thresholds
    }


def format_currency(value: float) -> str:
    return f"R$ {value:,.0f}"


st.title("Posições · Controle de Vencimentos")

with st.spinner("Carregando dados...", show_time=True):
    st.session_state.df = load_positions()

show_data_freshness("positions", label="Posições", ttl_minutes=60)

df_base = prepare_base_df(st.session_state.df)
portfolio_options = sorted(
    set(CODIGOS_CARTEIRAS_ADM.keys()) & set(df_base["Portfolio"].dropna().unique())
)

with st.sidebar:
    st.header("Filtros")
    selected_carteiras = st.multiselect(
        "Carteiras",
        options=portfolio_options,
        default=portfolio_options,
        placeholder="Selecione uma ou mais carteiras...",
    )
    selected_conjuntos = st.multiselect(
        "Classificação do Conjunto",
        options=RF_CLASSES,
        default=RF_CLASSES,
    )
    alert_threshold = st.slider(
        "Alerta de vencimento (dias úteis)",
        min_value=1,
        max_value=90,
        value=15,
    )
    only_with_maturity = st.checkbox("Somente ativos com data de vencimento", value=True)

if not selected_carteiras:
    st.info("Selecione ao menos uma carteira na barra lateral.")
    st.stop()

df_filtered = df_base[df_base["Portfolio"].isin(selected_carteiras)].copy()
if selected_conjuntos:
    df_filtered = df_filtered[df_filtered["Classificação do Conjunto"].isin(selected_conjuntos)]
if only_with_maturity:
    df_filtered = df_filtered[df_filtered["Data Vencimento"].notna()]

df_maturity = prepare_maturity_positions(df_filtered)

if df_maturity.empty:
    st.info("Nenhum ativo com vencimento encontrado para os filtros selecionados.")
    st.stop()

kpis = maturity_kpis(df_maturity, KPI_THRESHOLDS)
kpi_cols = st.columns(len(KPI_THRESHOLDS))
for col, threshold in zip(kpi_cols, KPI_THRESHOLDS):
    col.metric(
        label=f"Vencendo em ≤ {threshold} dias úteis",
        value=format_currency(kpis[threshold]),
    )

st.subheader("Detalhamento por Ativo")
st.dataframe(
    style_table(
        df_maturity.reset_index()[
            [
                "Portfolio",
                "Nome Ativo",
                "Alias",
                "Classificação do Conjunto",
                "Classificação Instrumento",
                "Data Vencimento",
                "Dias para Vencimento",
                "Quantidade",
                "Valor Unitário",
                "Saldo",
            ]
        ].set_index(["Portfolio", "Nome Ativo"]),
        date_cols=["Data Vencimento"],
        numeric_cols_format_as_float=["Valor Unitário", "Saldo"],
        numeric_cols_format_as_int=["Quantidade", "Dias para Vencimento"],
        highlight_row_if_value_lower={"Dias para Vencimento": alert_threshold},
    )
)
