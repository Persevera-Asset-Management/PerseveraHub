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
    _empty = pd.DataFrame(columns=["Ativo", "code_key", "Nome Ativo", "Quantidade"])

    if positions.empty:
        return _empty

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
        return _empty

    equity_positions["Ativo"] = equity_positions["Alias"].fillna(equity_positions["Nome Ativo"])
    equity_positions["code_key"] = equity_positions["Nome Ativo"]

    return (
        equity_positions.groupby(["Ativo", "code_key", "Nome Ativo"], dropna=False)
        .agg(Quantidade=("Quantidade", "sum"))
        .reset_index()
    )


def compute_lot_orders(qty_raw: pd.Series, prices: pd.Series) -> pd.Series:
    """
    Greedy portfolio-level lot optimization.

    Floors each raw quantity toward zero to the nearest standard lot (×100),
    then upgrades orders to improve portfolio tracking error subject to the
    net-cash constraint:
      1. Sell upgrades with abs(frac) > 50 are executed first — they free cash
         and reduce deviation simultaneously.
      2. Buy upgrades with abs(frac) > 50 are executed in descending fractional
         order (highest residual first) while net cash allows.

    Args:
        qty_raw: Raw (float) quantity per stock — positive = buy, negative = sell.
                 NaN-safe: stocks with NaN or non-positive price receive pd.NA.
        prices:  Last price per stock (must be aligned with qty_raw index).

    Returns:
        Int64 Series of lot quantities (all values are multiples of 100 or pd.NA).
    """
    valid = qty_raw.notna() & prices.notna() & prices.gt(0)

    qty = np.where(valid, qty_raw.astype(float), 0.0)
    price = np.where(valid, prices.astype(float), 0.0)

    # Step 1: Floor toward zero — +2.7 lots → +200, −2.7 lots → −200
    lot = np.sign(qty) * np.floor(np.abs(qty) / 100) * 100
    frac = qty - lot  # residual, same sign as qty, abs in [0, 100)

    # Step 2: Net cash after floor orders
    # Sells produce positive cash inflow; buys consume cash.
    net_cash = float(-(lot * price).sum())

    # Step 3: Sell upgrades — execute all where abs(frac) > 50
    # They free cash AND reduce tracking deviation.
    sell_upgrade = (qty < 0) & (np.abs(frac) > 50)
    for i in np.where(sell_upgrade)[0]:
        lot[i] -= 100
        net_cash += 100.0 * price[i]

    # Step 4: Buy upgrades — execute where abs(frac) > 50, highest frac first
    buy_upgrade = (qty > 0) & (frac > 50)
    buy_ix = np.where(buy_upgrade)[0]
    for i in buy_ix[np.argsort(-frac[buy_ix])]:
        cost = 100.0 * price[i]
        if net_cash >= cost:
            lot[i] += 100
            net_cash -= cost

    # Build Int64 result, preserving pd.NA for stocks without a valid price
    result = pd.array(lot.astype(int), dtype="Int64")
    for i in np.where(~valid.values)[0]:
        result[i] = pd.NA

    return pd.Series(result, index=qty_raw.index)


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

rvqm_row = portfolios_rvqm[portfolios_rvqm['Portfolio'] == selected_portfolio]
if rvqm_row.empty:
    st.error(f"Portfolio '{selected_portfolio}' não encontrado na tabela de clientes RVQM.")
    st.stop()

equity_position_to_total_portfolio = rvqm_row['Percentual do PL'].iloc[0]
equity_position_custodian = rvqm_row['Custodiante'].iloc[0]
equity_position_account = rvqm_row['Nr Conta'].iloc[0]

if equity_positions.empty:
    st.info(
        f"Nenhuma posição em Ações encontrada para {selected_portfolio}. "
        "Gerando ordens de abertura com base na carteira alvo."
    )

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

if positions_carteira.empty:
    if portfolio_total_balance_override == 0:
        st.error(
            f"O portfolio {selected_portfolio} não possui posições registradas. "
            "Informe o saldo total disponível no campo **Override Saldo Total** na barra lateral."
        )
        st.stop()
    calculated_portfolio_total_balance = 0.0
else:
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

current_market_data["Quantidade"] = current_market_data["Quantidade"].fillna(0).astype(float)
current_market_data["Nome Ativo"] = current_market_data["Nome Ativo"].fillna(current_market_data["code_key"])
current_market_data["Saldo Atual"] = current_market_data["Quantidade"] * current_market_data["LAST_PRICE"]
current_market_data["Peso Atual (%)"] = current_market_data["Saldo Atual"] / current_market_data["Saldo Atual"].sum() * 100
current_market_data["Peso Alvo (%)"] = current_market_data["weight_pct"].fillna(0)
current_market_data["Saldo Alvo"] = target_equity_balance * current_market_data["Peso Alvo (%)"] / 100
current_market_data["Valor Compra/Venda"] = current_market_data["Saldo Alvo"] - current_market_data["Saldo Atual"]
qty_raw = pd.Series(
    np.where(
        current_market_data["LAST_PRICE"].gt(0),
        current_market_data["Valor Compra/Venda"] / current_market_data["LAST_PRICE"],
        np.nan,
    ),
    index=current_market_data.index,
)
current_market_data["Quantidade Compra/Venda"] = compute_lot_orders(
    qty_raw,
    current_market_data["LAST_PRICE"],
)
qty_after = (
    current_market_data["Quantidade"]
    + current_market_data["Quantidade Compra/Venda"].astype("float64")
)
saldo_after = qty_after * current_market_data["LAST_PRICE"]
current_market_data["Peso Ex-Post (%)"] = saldo_after / saldo_after.sum() * 100

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
    f"{equity_position_custodian} &nbsp;·&nbsp; "
    f"{equity_position_account} &nbsp;·&nbsp; "
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
    "Peso Atual (%)",
    "Peso Alvo (%)",
    "Peso Ex-Post (%)",
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
        percent_cols=["Peso Atual (%)", "Peso Alvo (%)", "Peso Ex-Post (%)"],
        numeric_cols_format_as_float=["Último Preço"],
        numeric_cols_format_as_int=["Quantidade", "Quantidade Compra/Venda"],
        currency_cols=["Saldo Atual", "Saldo Alvo", "Valor Compra/Venda"],
        color_negative_positive_cols=["Valor Compra/Venda", "Quantidade Compra/Venda"],
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

missing_targets = current_market_data[current_market_data["weight_pct"].isna()]["Nome Ativo"].tolist()
if missing_targets:
    st.info(
        "Ativos sem peso alvo na carteira RVQM atual: "
        + ", ".join(missing_targets)
    )

# =============================================================================
# Resumo das Operações
# =============================================================================

st.divider()
st.subheader("Resumo das Operações")

lot_financial = (
    current_market_data["Quantidade Compra/Venda"].astype("float64")
    * current_market_data["LAST_PRICE"]
)

buys_mask = current_market_data["Operação"] == "C"
sells_mask = current_market_data["Operação"] == "V"

n_buys = int(buys_mask.sum())
n_sells = int(sells_mask.sum())
val_buys = lot_financial[buys_mask].sum()
val_sells = lot_financial[sells_mask].abs().sum()
net_cash = -lot_financial.sum() if lot_financial.sum() < 0 else lot_financial.sum()

target_mask = current_market_data["Peso Alvo (%)"].gt(0)
_te_pre = (
    (current_market_data.loc[target_mask, "Peso Atual (%)"].fillna(0)
     - current_market_data.loc[target_mask, "Peso Alvo (%)"]).abs().mean()
)
te_pre = float(_te_pre) if pd.notna(_te_pre) else 0.0

_te_post = (
    (current_market_data.loc[target_mask, "Peso Ex-Post (%)"].fillna(0)
     - current_market_data.loc[target_mask, "Peso Alvo (%)"]).abs().mean()
)
te_post = float(_te_post) if pd.notna(_te_post) else 0.0

summary_cols = st.columns(5)
summary_cols[0].metric(
    "Total de Compras",
    f"R$ {val_buys:,.0f}",
    delta=f"{n_buys:,.0f} ordens" if n_buys != 1 else f"{n_buys:,.0f} ordem",
    delta_arrow="off",
    help="Volume financeiro total das compras (lotes padrão)",
)
summary_cols[1].metric(
    "Total de Vendas",
    f"R$ {val_sells:,.0f}",
    delta=f"{n_sells:,.0f} ordens" if n_sells != 1 else f"{n_sells:,.0f} ordem",
    delta_arrow="off",
    help="Volume financeiro total das vendas (lotes padrão)",
)
summary_cols[2].metric(
    "Saldo Líquido",
    f"R$ {net_cash:,.0f}",
    height="stretch",
    help="Vendas - Compras em valor financeiro. Próximo de zero indica rebalanceamento neutro.",
)

summary_cols[3].metric(
    "Desvio Médio Atual",
    f"{te_pre:.2f} pp",
    height="stretch",
    help="Média do desvio absoluto |Peso Atual − Peso Alvo| sobre os ativos do target",
)
summary_cols[4].metric(
    "Desvio Médio Ex-Post",
    f"{te_post:.2f} pp",
    delta=f"{te_post - te_pre:+.2f} pp",
    delta_color="inverse",
    help="Média do desvio absoluto |Peso Ex-Post − Peso Alvo| após execução das ordens",
)


# =============================================================================
# Basket de Ordens
# =============================================================================

st.divider()
st.subheader("Basket de Ordens")

basket_orders = current_market_data[
    current_market_data["Operação"].isin(["C", "V"])
    & current_market_data["Quantidade Compra/Venda"].notna()
    & current_market_data["Quantidade Compra/Venda"].ne(0)
].copy()

if basket_orders.empty:
    st.info("Nenhuma ordem a executar — carteira já aderente ao target em lotes padrão.")
else:
    qty_abs = basket_orders["Quantidade Compra/Venda"].abs()
    tickers = basket_orders["code_key"]
    cv = basket_orders["Operação"]

    if equity_position_custodian == "BPCV":
        basket_df = pd.DataFrame({
            "Ativo": tickers,
            "C/V": cv,
            "Quantidade": qty_abs,
            "Preço": "M",
            "Conta": equity_position_account,
            "Validade": "DIA",
            "Obs": "TWAP",
        }).reset_index(drop=True)
        preview_int_cols = ["Quantidade"]
        preview_center_cols = ["C/V", "Preço", "Validade", "Obs"]

    elif equity_position_custodian == "XPCV":
        basket_df = pd.DataFrame({
            "Estratégia": "TWAP",
            "Cliente": equity_position_account,
            "Ativo": tickers,
            "C/V": cv,
            "Qtd. Total": qty_abs,
            "Financeiro": "",
            "Preço": "",
            "Preço Would": "",
            "Hora Inicial": "",
            "Hora Final": "",
        }).reset_index(drop=True)
        preview_int_cols = ["Qtd. Total"]
        preview_center_cols = ["Estratégia", "C/V"]

    else:
        st.warning(
            f"Custodiante '{equity_position_custodian}' sem formato de basket definido. "
            "Formatos suportados: BPCV, XPCV."
        )
        basket_df = pd.DataFrame()
        preview_int_cols = []
        preview_center_cols = []

    if not basket_df.empty:
        st.dataframe(
            style_table(
                basket_df,
                numeric_cols_format_as_int=preview_int_cols,
                left_align_cols=["Ativo"],
                center_align_cols=preview_center_cols,
            ),
            width="stretch",
            height="content",
            hide_index=True,
        )

        position_date = positions_carteira["Data Posição"].max().strftime("%Y%m%d")
        filename = f"basket_{selected_portfolio}_{equity_position_custodian}_{position_date}.csv"
        csv_bytes = basket_df.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")

        st.download_button(
            label=f"Download Basket · {equity_position_custodian}",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            type="primary",
        )
