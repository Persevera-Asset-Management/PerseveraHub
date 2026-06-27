import pandas as pd
import numpy as np
import streamlit as st

from utils.ui import show_data_freshness
from utils.table import style_table

from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS_ADM
from services.position_service import (
    load_positions,
    load_instruments_fgc,
    load_issuers,
    get_latest_date_data,
    get_emissor_column,
)

FGC_LIMIT = 250_000
APPROVED_STATUSES = {"Aprovado", "Name Lending"}


def prepare_base_df(df_raw: pd.DataFrame, df_issuers: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    df.replace(" ", np.nan, inplace=True)
    df.dropna(subset=["Nome Ativo", "Classificação do Conjunto"], inplace=True)
    df = get_emissor_column(df)
    df = pd.merge(
        left=df,
        right=df_issuers.set_index("Nome Emissor"),
        left_on="Emissor",
        right_index=True,
        how="left",
        # suffixes=("", "_issuer"),
    )
    df["Status do Emissor"] = df["Status do Emissor"].fillna("Sem Classificação")
    return df


def prepare_current_positions(
    df: pd.DataFrame,
    instruments_fgc: list[str],
) -> pd.DataFrame:
    grouped = df.groupby(
        [
            "Portfolio",
            pd.Grouper(key="Data Posição", freq="D"),
            "Nome Ativo",
            "Alias",
            "Emissor",
            "Status do Emissor",
            "Classificação Instrumento",
        ]
    ).agg(
        **{
            "Quantidade": ("Quantidade", "sum"),
            "Valor Unitário": ("Valor Unitário", "mean"),
            "Saldo": ("Saldo", "sum"),
        }
    )
    current = get_latest_date_data(
        grouped, level="Data Posição", group_level="Portfolio"
    ).reset_index()
    current = current[current["Saldo"] > 0].copy()
    current["Aprovado"] = current["Status do Emissor"].isin(APPROVED_STATUSES)
    current["Coberto FGC"] = current["Classificação Instrumento"].isin(instruments_fgc)
    return current


def build_non_approved_client_summary(df: pd.DataFrame) -> pd.DataFrame:
    df_na = df[~df["Aprovado"]].copy()
    if df_na.empty:
        return pd.DataFrame(
            columns=[
                "Saldo Não Aprovado (FGC)",
                "Nº Emissores",
            ]
        )

    summary = (
        df_na.groupby("Portfolio", observed=True)
        .agg(
            **{
                "Saldo Não Aprovado (FGC)": ("Saldo", "sum"),
                "Nº Emissores": ("Emissor", "nunique"),
            }
        )
    )
    return summary.sort_values("Saldo Não Aprovado (FGC)", ascending=False)


def build_fgc_issuer_coverage(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["Portfolio", "Emissor", "Saldo", "Saldo Não Coberto"]
        )

    coverage = (
        df.groupby(["Portfolio", "Emissor"], observed=True)["Saldo"]
        .sum()
        .reset_index()
    )
    coverage["Saldo Não Coberto"] = np.where(
        coverage["Saldo"] < FGC_LIMIT,
        0,
        coverage["Saldo"] - FGC_LIMIT,
    )
    return coverage.sort_values(
        ["Portfolio", "Saldo Não Coberto", "Saldo"],
        ascending=[True, False, False],
    )


def build_fgc_client_summary(df_coverage: pd.DataFrame) -> pd.DataFrame:
    if df_coverage.empty:
        return pd.DataFrame(
            columns=[
                "Saldo FGC",
                "Saldo Não Coberto",
                "Emissores Acima do Limite",
            ]
        )

    summary = df_coverage.groupby("Portfolio", observed=True).agg(
        **{
            "Saldo FGC": ("Saldo", "sum"),
            "Saldo Não Coberto": ("Saldo Não Coberto", "sum"),
            "Emissores Acima do Limite": (
                "Saldo Não Coberto",
                lambda s: int((s > 0).sum()),
            ),
        }
    )
    return summary.sort_values("Saldo Não Coberto", ascending=False)


def build_client_overview(
    df_non_approved: pd.DataFrame,
    df_fgc_clients: pd.DataFrame,
) -> pd.DataFrame:
    overview = df_non_approved.join(df_fgc_clients, how="outer").fillna(0)
    overview = overview.sort_values(
        ["Saldo Não Coberto", "Saldo Não Aprovado (FGC)"],
        ascending=False,
    )
    return overview


def format_currency(value: float) -> str:
    return f"R$ {value:,.0f}"


st.title("Monitor FGC")

with st.spinner("Carregando dados...", show_time=True):
    st.session_state.df = load_positions()
    st.session_state.instruments_fgc = load_instruments_fgc()
    st.session_state.df_issuers = load_issuers()

show_data_freshness("positions", label="Posições", ttl_minutes=60)

df_base = prepare_base_df(st.session_state.df, st.session_state.df_issuers)
instruments_fgc = st.session_state.instruments_fgc
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
    show_only_alerts = st.checkbox(
        "Mostrar apenas clientes com alerta",
        value=False,
        help="Exibe somente carteiras com saldo FGC não aprovado ou exposição acima do limite.",
    )

if not selected_carteiras:
    st.info("Selecione ao menos uma carteira na barra lateral.")
    st.stop()

df_filtered = df_base[df_base["Portfolio"].isin(selected_carteiras)].copy()
df_current = prepare_current_positions(df_filtered, instruments_fgc)
df_current = df_current[df_current["Coberto FGC"]].copy()

if df_current.empty:
    st.info("Nenhum ativo coberto pelo FGC encontrado para os filtros selecionados.")
    st.stop()

df_non_approved_clients = build_non_approved_client_summary(df_current)
df_fgc_issuer = build_fgc_issuer_coverage(df_current)
df_fgc_clients = build_fgc_client_summary(df_fgc_issuer)
df_client_overview = build_client_overview(df_non_approved_clients, df_fgc_clients)
df_client_overview = df_client_overview.reindex(selected_carteiras, fill_value=0)

if show_only_alerts:
    df_client_overview = df_client_overview[
        (df_client_overview["Saldo Não Aprovado (FGC)"] > 0)
        | (df_client_overview["Saldo Não Coberto"] > 0)
    ]

total_na_fgc = float(df_non_approved_clients["Saldo Não Aprovado (FGC)"].sum())
total_excesso_fgc = float(df_fgc_clients["Saldo Não Coberto"].sum())
emissores_acima = int((df_fgc_issuer["Saldo Não Coberto"] > 0).sum())
total_fgc = float(df_fgc_clients["Saldo FGC"].sum())

kpi_cols = st.columns(4)
kpi_cols[0].metric("Saldo total FGC", format_currency(total_fgc))
kpi_cols[1].metric("Não aprovado (FGC)", format_currency(total_na_fgc))
kpi_cols[2].metric("Excesso FGC (agregado)", format_currency(total_excesso_fgc))
kpi_cols[3].metric("Emissores acima do limite", emissores_acima)

st.subheader("Resumo por Cliente")
st.caption(
    "Somente instrumentos cobertos pelo FGC. Consolida exposição a emissores não aprovados "
    "e o risco de estouro do teto FGC por emissor agregado."
)
if df_client_overview.empty:
    st.info("Nenhum cliente com alerta para os filtros selecionados.")
else:
    st.dataframe(
        style_table(
            df_client_overview,
            numeric_cols_format_as_float=[
                "Saldo Não Aprovado (FGC)",
                "Saldo FGC",
                "Saldo Não Coberto",
            ],
            numeric_cols_format_as_int=["Nº Emissores", "Emissores Acima do Limite"],
            highlight_row_if_value_greater={
                "Saldo Não Coberto": 0,
                "Saldo Não Aprovado (FGC)": 0,
            },
        ),
        width="stretch",
    )

st.subheader("Cobertura FGC por Emissor")
st.caption(f"Saldo agregado por emissor (limite de {format_currency(FGC_LIMIT)} por titular).")
if df_fgc_issuer.empty:
    st.info("Nenhum ativo coberto pelo FGC encontrado.")
else:
    st.dataframe(
        style_table(
            df_fgc_issuer.set_index(["Portfolio", "Emissor"]),
            numeric_cols_format_as_float=["Saldo", "Saldo Não Coberto"],
            highlight_row_if_value_greater={"Saldo Não Coberto": 0},
        ),
        width="stretch",
    )

st.subheader("Detalhamento · Ativos Não Aprovados (FGC)")
df_non_approved_detail = df_current[~df_current["Aprovado"]].copy()
if df_non_approved_detail.empty:
    st.info("Nenhum ativo FGC de emissor não aprovado encontrado.")
else:
    st.dataframe(
        style_table(
            df_non_approved_detail[
                [
                    "Portfolio",
                    "Nome Ativo",
                    "Alias",
                    "Emissor",
                    "Status do Emissor",
                    "Classificação Instrumento",
                    "Quantidade",
                    "Valor Unitário",
                    "Saldo",
                ]
            ].set_index(["Portfolio", "Nome Ativo"]),
            numeric_cols_format_as_float=["Valor Unitário", "Saldo"],
            numeric_cols_format_as_int=["Quantidade"],
        ),
        width="stretch",
    )
