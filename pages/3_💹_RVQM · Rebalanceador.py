import io

import pandas as pd
import numpy as np
import streamlit as st
import requests

from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication

from services.position_service import (
    load_equities_portfolio,
    load_portfolios_rvqm,
    load_positions_for_portfolio,
    load_positions,
)


st.set_page_config(
    page_title="RVQM · Rebalanceador | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("RVQM · Rebalanceador")

GOOGLE_SHEET_ID = "1aF-HUyj4GNwKCgS263e2IBzT1_fU_nztUirRAKKlsWo"
GOOGLE_SHEET_GID = "0"
GOOGLE_SHEET_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export"
    f"?format=csv&gid={GOOGLE_SHEET_GID}"
)

MARKET_DATA_COLUMNS = [
    "RT_PX_CHG_PCT_1D",
    "LAST_PRICE",
    "YEST_LAST_TRADE",
    "EQY_TURNOVER_REALTIME",
    "30_DAY_AVG_TURNOVER_AT_TIME_RT",
    "VOLUME",
    "BID",
    "ASK",
    "EXCH_TODAY_ALT_SETT_IN_PRICE_RT",
]


# =============================================================================
# Funções de carregamento
# =============================================================================

def normalize_asset_code(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    if text.startswith("BR_"):
        text = text[3:]
    return text.replace(".SA", "").split()[0]


def parse_google_number(value: object) -> float:
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.number)):
        return float(value)

    text = str(value).strip().replace("\xa0", "").replace("%", "")
    if not text:
        return np.nan

    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1 or len(text.rsplit(".", 1)[-1]) == 3:
        text = text.replace(".", "")

    return pd.to_numeric(text, errors="coerce")


def prepare_equity_positions(positions: pd.DataFrame) -> pd.DataFrame:
    if positions.empty:
        return positions

    instrument_column = (
        "Classificação Instrumento"
        if "Classificação Instrumento" in positions.columns
        else "Classificação Instrumento-Relation"
    )

    latest_date = positions["Data Posição"].max()
    equity_positions = positions[
        (positions["Data Posição"] == latest_date)
        & (positions[instrument_column] == "Ação")
    ].copy()

    if equity_positions.empty:
        return equity_positions

    equity_positions["Ativo"] = equity_positions["Alias"].fillna(equity_positions["Nome Ativo"])
    equity_positions["code_key"] = equity_positions["Nome Ativo"]

    return (
        equity_positions.groupby(["Ativo", "code_key", "Nome Ativo"], dropna=False)
        .agg(Quantidade=("Quantidade", "sum"))
        .reset_index()
    )


@st.cache_data(ttl=60)
def load_google_sheet_market_data() -> pd.DataFrame:
    response = requests.get(GOOGLE_SHEET_CSV_URL, timeout=20)
    response.raise_for_status()

    df = pd.read_csv(io.StringIO(response.text))
    df.columns = [str(column).strip() for column in df.columns]
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")

    if "index" not in df.columns:
        raise ValueError("Coluna 'index' não encontrada na planilha do Google Sheets.")

    df = df.rename(columns={"index": "ticker_bloomberg"})
    df["ticker_bloomberg"] = df["ticker_bloomberg"].astype(str).str.strip()
    df = df[df["ticker_bloomberg"].ne("")]
    df["code_key"] = df["ticker_bloomberg"].map(normalize_asset_code)

    for column in MARKET_DATA_COLUMNS:
        if column in df.columns:
            df[column] = df[column].map(parse_google_number)

    return df


# =============================================================================
# Sidebar — seleção de portfolio
# =============================================================================
portfolios_rvqm = load_portfolios_rvqm()

with st.sidebar:
    st.header("Parâmetros")
    selected_portfolio = st.selectbox(
        "Portfolio",
        options=sorted(portfolios_rvqm['Portfolio'].unique().tolist()),
        index=None,
        placeholder="Selecione um portfolio...",
    )
    portfolio_total_balance_override = st.number_input(
        "Override Saldo Total",
        min_value=0.0,
        value=0.0,
        step=10000.0,
        format="%.2f",
        help="Informe um valor maior que zero para substituir o saldo total calculado pelas posições.",
    )

if not selected_portfolio:
    st.info("Selecione um portfolio na barra lateral.")
    st.stop()

# =============================================================================
# Carregamento de dados
# =============================================================================

if st.button("Atualizar BLP Relay", type="primary"):
    load_google_sheet_market_data.clear()
    st.toast("Cache do BLP Relay limpo. Buscando dados atualizados...")

with st.spinner("Carregando composição da carteira..."):
    equities_portfolio = load_equities_portfolio()

with st.spinner("Carregando posições..."):
    df_positions = load_positions()

with st.spinner("Carregando posições do portfolio..."):
    if selected_portfolio:
        positions_carteira = df_positions[df_positions["Portfolio"] == selected_portfolio]
    else:
        st.error("Selecione um portfolio na barra lateral.")
        st.stop()

with st.spinner("Carregando dados de mercado do Google Sheets..."):
    try:
        market_data = load_google_sheet_market_data()
    except Exception as e:
        st.error(f"Erro ao carregar dados do BLP Relay: {str(e)}")
        st.stop()

if equities_portfolio.empty:
    st.warning("Nenhuma composição de carteira disponível para exibir.")
    st.stop()

if market_data.empty:
    st.warning("Nenhum dado de mercado disponível no BLP Relay.")
    st.stop()

if positions_carteira.empty:
    st.warning(f"Nenhuma posição disponível para o portfolio {selected_portfolio}.")
    st.stop()

# =============================================================================
# Composição Atual
# =============================================================================

current_date = equities_portfolio['date'].max()
current_portfolio = (
    equities_portfolio[equities_portfolio['date'] == current_date]
    .copy()
    .sort_values('weight', ascending=False)
    .reset_index(drop=True)
)
total_weight = current_portfolio['weight'].sum()
current_portfolio['weight_pct'] = current_portfolio['weight'] / total_weight * 100
current_portfolio["code_key"] = current_portfolio["code"]

equity_positions = prepare_equity_positions(positions_carteira)
equity_position_to_total_portfolio = portfolios_rvqm[portfolios_rvqm['Portfolio'] == selected_portfolio]['Percentual do PL'].values[0]

if equity_positions.empty:
    st.warning(f"Nenhuma posição de Ação encontrada para o portfolio {selected_portfolio}.")
    st.stop()

current_market_data = (
    equity_positions.merge(
        current_portfolio[["code_key", "weight_pct"]],
        how="outer",
        on="code_key",
    )
    .merge(
        market_data,
        how="left",
        on="code_key",
        suffixes=("", "_market"),
    )
)

calculated_portfolio_total_balance = (
    positions_carteira
    .groupby("Data Posição")["Saldo"]
    .sum()
    .sort_index()
    .iloc[-1]
)
portfolio_total_balance = (
    portfolio_total_balance_override
    if portfolio_total_balance_override > 0
    else calculated_portfolio_total_balance
)
target_equity_balance = portfolio_total_balance * equity_position_to_total_portfolio

current_market_data["Quantidade"] = current_market_data["Quantidade"].fillna(0)
current_market_data["Nome Ativo"] = current_market_data["Nome Ativo"].fillna(current_market_data["code_key"])
current_market_data["Saldo Atual"] = current_market_data["Quantidade"] * current_market_data["LAST_PRICE"]
current_market_data["Peso Alvo (%)"] = current_market_data["weight_pct"].fillna(0)
current_market_data["Saldo Alvo"] = target_equity_balance * current_market_data["Peso Alvo (%)"] / 100
current_market_data["Valor Compra/Venda"] = current_market_data["Saldo Alvo"] - current_market_data["Saldo Atual"]
current_market_data["Quantidade Compra/Venda"] = np.where(
    current_market_data["LAST_PRICE"].gt(0),
    current_market_data["Valor Compra/Venda"] / current_market_data["LAST_PRICE"],
    np.nan,
)
current_market_data["Quantidade Compra/Venda"] = current_market_data["Quantidade Compra/Venda"].round().astype("Int64")
current_market_data["Operação"] = np.select(
    [
        current_market_data["Quantidade Compra/Venda"].gt(0).fillna(False),
        current_market_data["Quantidade Compra/Venda"].lt(0).fillna(False),
    ],
    ["C", "V"],
    default="Manter",
)
current_market_data = current_market_data.sort_values("Valor Compra/Venda", ascending=False)

st.markdown(
    f"<p style='color:#888; font-size:0.85rem; margin-bottom:6px;'>"
    f"{selected_portfolio} &nbsp;·&nbsp; "
    f"{len(equity_positions)} ações &nbsp;·&nbsp; "
    f"posição em {positions_carteira['Data Posição'].max().strftime('%d/%m/%Y')}"
    f"</p>",
    unsafe_allow_html=True,
)

metric_cols = st.columns(4)
metric_cols[0].metric("Ações no Portfolio RVQM", len(equity_positions))
metric_cols[1].metric(
    "Saldo Total" + (" (override)" if portfolio_total_balance_override > 0 else ""),
    f"R$ {portfolio_total_balance:,.0f}",
)
metric_cols[2].metric("Percentual do PL", f"{equity_position_to_total_portfolio*100:.1f}%")
metric_cols[3].metric("Saldo Alvo RVQM", f"R$ {target_equity_balance:,.0f}")

display_columns = [
    "TIME",
    "Nome Ativo",
    "LAST_PRICE",
    "Quantidade",
    "Saldo Atual",
    "Peso Alvo (%)",
    "Saldo Alvo",
    "Valor Compra/Venda",
    "Quantidade Compra/Venda",
    "Operação",
]
display_columns = [column for column in display_columns if column in current_market_data.columns]
display_df = (
    current_market_data[display_columns]
    .rename(
        columns={
            "ticker_bloomberg": "Ticker Bloomberg",
            "LAST_PRICE": "Último Preço",
            "TIME": "Horário",
        }
    )
    .reset_index(drop=True)
)

st.dataframe(
    style_table(
        display_df,
        percent_cols=["Peso Alvo (%)"],
        numeric_cols_format_as_float=["Último Preço"],
        numeric_cols_format_as_int=["Quantidade", "Quantidade Compra/Venda"],
        currency_cols=["Saldo Atual", "Saldo Alvo", "Valor Compra/Venda"],
        color_negative_positive_cols=["Valor Compra/Venda"],
        left_align_cols=["Nome Ativo", "Ticker Bloomberg"],
        center_align_cols=["Horário", "Operação"],
    ),
    width="stretch",
    height="content",
    hide_index=True,
)

missing_prices = display_df[display_df["Último Preço"].isna()]["Nome Ativo"].tolist()
if missing_prices:
    st.warning(
        "Ativos da carteira sem correspondência de preço no BLP Relay: "
        + ", ".join(missing_prices)
    )

missing_targets = display_df[display_df["Peso Alvo (%)"].isna()]["Nome Ativo"].tolist()
if missing_targets:
    st.info(
        "Ativos sem peso alvo na carteira RVQM atual: "
        + ", ".join(missing_targets)
    )
