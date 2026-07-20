import pandas as pd
from datetime import datetime, date

import streamlit as st

from utils.table import style_table
from configs.pages.carteiras_administradas import CODIGOS_CARTEIRAS_ADM

from services.position_service import (
    load_assets,
    load_issuers,
    get_emissor_column,
    load_portfolio_from_comdinheiro,
    prepare_comdinheiro_portfolio_positions_df,
)

DISPLAY_COLUMNS = [
    "Carteira",
    "Ticker",
    "Alias",
    "Cadastro Fibery",
    "Indexador",
    "Data Vencimento",
    "Nome Emissor",
    "Nome Devedor",
    "Status do Emissor",
    "Quantidade",
    "Preço Unitário",
    "Saldo Bruto",
    "Percentual",
    "Custodiante",
]

ASSET_COLUMNS = [
    "Name",
    "Alias",
    "Indexador",
    "Data Vencimento",
    "Nome Emissor",
    "Nome Devedor",
    "Emissor Geral",
    "Identificador do Emissor Geral",
]

st.title("Posições · Gerencial Completo")

for key in ("df_cd_raw", "df_assets", "df_issuers"):
    st.session_state.setdefault(key, None)

with st.sidebar:
    st.header("Parâmetros")
    selected_date = st.date_input(
        "Data",
        format="DD/MM/YYYY",
        value=pd.to_datetime(date.today()),
        min_value=datetime(2024, 1, 1),
        max_value=pd.to_datetime(date.today()),
    )
    selected_carteiras = st.multiselect(
        "Carteiras selecionadas",
        options=CODIGOS_CARTEIRAS_ADM,
        default=CODIGOS_CARTEIRAS_ADM,
    )
    btn_run = st.button("Executar")

    selected_status = []
    if st.session_state.df_issuers is not None:
        st.divider()
        st.subheader("Filtros")
        status_options = sorted(
            st.session_state.df_issuers["Status do Emissor"].dropna().unique()
        )
        # Inclui rótulos usados quando não há match completo com o Fibery.
        for extra in ("Sem cadastro", "Sem Classificação"):
            if extra not in status_options:
                status_options.append(extra)
        selected_status = st.multiselect(
            "Status do Emissor",
            options=status_options,
            default=status_options,
        )

if btn_run:
    with st.spinner("Carregando dados...", show_time=True):
        st.session_state.df_cd_raw = load_portfolio_from_comdinheiro(
            portfolios=tuple(sorted(selected_carteiras)),
            date_report=selected_date.strftime("%Y-%m-%d"),
        )
        st.session_state.df_assets = load_assets()
        st.session_state.df_issuers = load_issuers()
        st.rerun()

df_cd_raw = st.session_state.df_cd_raw
df_assets = st.session_state.df_assets
df_issuers = st.session_state.df_issuers

if df_cd_raw is not None and df_assets is not None and df_issuers is not None:
    try:
        df_cd = prepare_comdinheiro_portfolio_positions_df(df_cd_raw)

        # Fibery enriquece quando há match; left join preserva todas as posições do ComDinheiro.
        # Status do emissor: match por Identificador do Emissor Geral → Name (cadastro de emissores).
        df_assets = get_emissor_column(df_assets)
        if "Identificador do Emissor Geral" not in df_assets.columns:
            df_assets["Identificador do Emissor Geral"] = pd.NA

        asset_cols = [col for col in ASSET_COLUMNS if col in df_assets.columns]
        df = df_cd.merge(
            df_assets[asset_cols],
            left_on="Ticker",
            right_on="Name",
            how="left",
        )

        df = df.merge(
            df_issuers.set_index("Name").rename(
                columns={"Nome Emissor": "Nome Emissor Geral"}
            ),
            left_on="Identificador do Emissor Geral",
            right_index=True,
            how="left",
        )

        matched = df["Name"].notna()
        df["Cadastro Fibery"] = matched.map({True: "Cadastrado", False: "Sem cadastro"})
        df.loc[~matched, "Status do Emissor"] = "Sem cadastro"
        df.loc[matched, "Status do Emissor"] = (
            df.loc[matched, "Status do Emissor"].fillna("Sem Classificação")
        )

        saldo_carteiras = (
            df.groupby("Carteira")
            .agg({"Saldo Bruto": "sum"})
            .rename(columns={"Saldo Bruto": "Saldo Total"})
        )
        df = df.merge(saldo_carteiras, right_index=True, left_on="Carteira", how="left")
        df["Percentual"] = df["Saldo Bruto"] / df["Saldo Total"] * 100

        # Universo completo (diferença vs Controle de Estoque): remove apenas taxa administrativa.
        df = df[df["Ativo"] != "Taxa de Administração"].copy()

        if selected_status:
            df = df[df["Status do Emissor"].isin(selected_status)]

        df["Alias"] = df["Alias"].fillna(df["Ativo"])
        df = df.sort_values(["Carteira", "Saldo Bruto"], ascending=[True, False])

        df_clean = df[DISPLAY_COLUMNS].copy()
        df_clean.drop_duplicates(inplace=True)

        sem_cadastro = df_clean["Cadastro Fibery"] == "Sem cadastro"
        n_sem_cadastro = int(sem_cadastro.sum())
        if n_sem_cadastro > 0:
            tickers_sem_cadastro = df_clean.loc[sem_cadastro, "Ticker"].dropna().unique()
            st.warning(
                f"{n_sem_cadastro} posição(ões) sem cadastro no Fibery "
                f"({len(tickers_sem_cadastro)} ticker(s)). "
                "Campos de taxonomia/emissor ficam vazios; Alias/Saldo vêm do ComDinheiro."
            )

        st.dataframe(
            style_table(
                df_clean,
                date_cols=["Data Vencimento"],
                currency_cols=["Saldo Bruto", "Preço Unitário"],
                numeric_cols_format_as_float=["Quantidade"],
                percent_cols=["Percentual"],
                highlight_row_by_column="Cadastro Fibery",
                highlight_row_if_value_equals="Sem cadastro",
                highlight_color="#fff3cd",
            ),
            hide_index=True,
        )

    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.info("Selecione os parâmetros e clique em **Executar** para carregar os dados.")
