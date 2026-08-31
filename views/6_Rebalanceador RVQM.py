import io
from datetime import datetime

import pandas as pd
import numpy as np
import streamlit as st
import requests

from utils.table import style_table

from services.position_service import (
    load_assets,
    load_equities_portfolio,
    load_portfolios_rvqm,
    load_positions,
)
from services.external_positions_service import (
    MATCH_AMBIGUOUS,
    MATCH_MATCHED,
    MATCH_UNMATCHED,
    enrich_external_positions,
    match_external_positions,
    match_summary,
    parse_external_positions_file,
    require_quantidade,
    template_csv_bytes,
)

RVQM_INSTRUMENTS = ("Ação", "BDR")
STANDARD_LOT_SIZE = 100
FRACTIONAL_LOT_SIZE = 1

ORIGEM_FIBERY = "Fibery"
ORIGEM_MANUAL = "Posição manual"

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

def instrument_lot_size(instrument: object) -> int:
    if instrument == "BDR":
        return FRACTIONAL_LOT_SIZE
    return STANDARD_LOT_SIZE

def safe_weight_pct(values: pd.Series) -> pd.Series:
    """Convert absolute values to portfolio weights (%). Returns zeros if sum is 0."""
    total = values.sum(skipna=True)
    if pd.isna(total) or total == 0:
        return pd.Series(0.0, index=values.index)
    return values / total * 100


def compute_rebalance_columns(
    df: pd.DataFrame,
    target_equity_balance: float,
) -> pd.DataFrame:
    """Calcula pesos, saldos-alvo e ordens em lote para a sleeve negociável."""
    out = df.copy()
    out["Saldo Atual"] = out["Quantidade"] * out["LAST_PRICE"]
    out["Peso Atual (%)"] = safe_weight_pct(out["Saldo Atual"])
    target_w = out["weight_pct"].fillna(0.0)
    weight_sum = float(target_w.sum(skipna=True))
    if weight_sum > 0:
        target_w = target_w / weight_sum * 100
    out["Peso Alvo (%)"] = target_w
    out["Saldo Alvo"] = target_equity_balance * out["Peso Alvo (%)"] / 100
    out["Valor Compra/Venda"] = out["Saldo Alvo"] - out["Saldo Atual"]
    qty_raw = pd.Series(
        np.where(
            out["LAST_PRICE"].gt(0),
            out["Valor Compra/Venda"] / out["LAST_PRICE"],
            np.nan,
        ),
        index=out.index,
    )
    out["Quantidade Compra/Venda"] = compute_lot_orders(
        qty_raw,
        out["LAST_PRICE"],
        out["Lote"],
        full_exit=out["Peso Alvo (%)"].eq(0),
    )
    qty_after = out["Quantidade"] + out["Quantidade Compra/Venda"].astype("float64")
    out["Peso Ex-Post (%)"] = safe_weight_pct(qty_after * out["LAST_PRICE"])
    out["Operação"] = np.select(
        [
            out["Quantidade Compra/Venda"].gt(0).fillna(False),
            out["Quantidade Compra/Venda"].lt(0).fillna(False),
        ],
        ["C", "V"],
        default="Manter",
    )
    return out


def mark_ignored_assets(df: pd.DataFrame) -> pd.DataFrame:
    """Mantém a posição visível, sem ordem e fora da sleeve negociável."""
    out = df.copy()
    out["Saldo Atual"] = out["Quantidade"] * out["LAST_PRICE"]
    out["Peso Atual (%)"] = np.nan
    out["Peso Alvo (%)"] = 0.0
    out["Peso Ex-Post (%)"] = np.nan
    out["Saldo Alvo"] = np.nan
    out["Valor Compra/Venda"] = 0.0
    out["Quantidade Compra/Venda"] = pd.Series(0, index=out.index, dtype="Int64")
    out["Operação"] = "Ignorar"
    return out

def prepare_equity_positions(positions: pd.DataFrame) -> pd.DataFrame:
    _empty = pd.DataFrame(
        columns=["Ativo", "code_key", "Nome Ativo", "Quantidade", "Classificação Instrumento"]
    )

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
        & (positions[instrument_column].isin(RVQM_INSTRUMENTS))
    ].copy()

    if equity_positions.empty:
        return _empty

    equity_positions["Ativo"] = equity_positions["Alias"].fillna(equity_positions["Nome Ativo"])
    equity_positions["code_key"] = equity_positions["Nome Ativo"]

    return (
        equity_positions.groupby(
            ["Ativo", "code_key", "Nome Ativo", instrument_column],
            dropna=False,
        )
        .agg(Quantidade=("Quantidade", "sum"))
        .reset_index()
        .rename(columns={instrument_column: "Classificação Instrumento"})
    )

def compute_lot_orders(
    qty_raw: pd.Series,
    prices: pd.Series,
    lot_sizes: pd.Series | None = None,
    full_exit: pd.Series | None = None,
) -> pd.Series:
    """
    Greedy portfolio-level lot optimization.

    Floors each raw quantity toward zero to the nearest tradable lot, then
    upgrades orders to improve portfolio tracking error subject to the
    net-cash constraint:
      1. Sell upgrades with abs(frac) > lot_size / 2 are executed first —
         they free cash and reduce deviation simultaneously.
      2. Buy upgrades with abs(frac) > lot_size / 2 are executed in
         descending fractional order (highest residual first) while net cash
         allows.

    Rows flagged via `full_exit` skip lot rounding entirely: the order is set
    to the exact raw quantity so the resulting position is exactly zero,
    never selling more shares than currently held (e.g. holding 690 shares
    with a 100-share lot must generate a sell of exactly 690, not 700).

    Args:
        qty_raw: Raw (float) quantity per stock — positive = buy, negative = sell.
                 NaN-safe: stocks with NaN or non-positive price receive pd.NA.
        prices:  Last price per stock (must be aligned with qty_raw index).
        lot_sizes: Tradable lot size per stock (e.g. 100 for Ação, 1 for BDR).
                   Defaults to 100 for all rows when omitted.
        full_exit: Boolean Series aligned with qty_raw. True marks rows whose
                   target position is zero (full liquidation), which bypass
                   lot rounding to avoid over/under-selling the held quantity.

    Returns:
        Int64 Series of order quantities (multiples of each row's lot size or pd.NA).
    """
    valid = qty_raw.notna() & prices.notna() & prices.gt(0)

    qty = np.where(valid, qty_raw.astype(float), 0.0)
    price = np.where(valid, prices.astype(float), 0.0)
    if lot_sizes is None:
        lots = np.full(len(qty_raw), float(STANDARD_LOT_SIZE))
    else:
        lots = (
            lot_sizes.reindex(qty_raw.index)
            .fillna(STANDARD_LOT_SIZE)
            .astype(float)
            .values
        )
    if full_exit is None:
        full_exit_mask = np.zeros(len(qty_raw), dtype=bool)
    else:
        full_exit_mask = (
            full_exit.reindex(qty_raw.index).fillna(False).astype(bool).values
        )

    # Step 1: Floor toward zero — e.g. +270 with lot 100 → +200, +47.8 with lot 1 → +47
    lot = np.sign(qty) * np.floor(np.abs(qty) / lots) * lots
    frac = qty - lot  # residual, same sign as qty, abs in [0, lot_size)

    # Full-exit rows: sell/buy the exact raw quantity so the position lands
    # precisely on zero, ignoring lot-size rounding (and thus excluding them
    # from the upgrade steps below, since their residual is now zero).
    exit_ix = np.where(full_exit_mask & valid.values & (qty != 0))[0]
    lot[exit_ix] = qty[exit_ix]
    frac[exit_ix] = 0.0

    # Step 2: Net cash after floor orders
    # Sells produce positive cash inflow; buys consume cash.
    net_cash = float(-(lot * price).sum())

    # Step 3: Sell upgrades — execute all where abs(frac) > lot_size / 2
    # They free cash AND reduce tracking deviation.
    sell_upgrade = (qty < 0) & (np.abs(frac) > (lots / 2.0))
    for i in np.where(sell_upgrade)[0]:
        lot[i] -= lots[i]
        net_cash += lots[i] * price[i]

    # Step 4: Buy upgrades — execute where abs(frac) > lot_size / 2, highest frac first
    buy_upgrade = (qty > 0) & (frac > (lots / 2.0))
    buy_ix = np.where(buy_upgrade)[0]
    for i in buy_ix[np.argsort(-frac[buy_ix])]:
        cost = lots[i] * price[i]
        if net_cash >= cost:
            lot[i] += lots[i]
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
# Sidebar — seleção de portfolio e carteira-modelo
# =============================================================================
try:
    portfolios_rvqm = load_portfolios_rvqm()
except Exception as e:
    st.error(f"Erro ao carregar clientes com carteira-modelo: {e}")
    st.stop()

if portfolios_rvqm.empty:
    st.warning("Nenhum cliente com carteira-modelo ativa no Fibery.")
    st.stop()

portfolio_options = sorted(portfolios_rvqm["Portfolio"].dropna().unique().tolist())

with st.sidebar:
    st.header("Parâmetros")
    selected_portfolio = st.selectbox(
        "Portfolio",
        options=portfolio_options,
        index=None,
        placeholder="Selecione um portfolio...",
    )

    selected_client_row = None
    if selected_portfolio:
        rvqm_row = portfolios_rvqm[portfolios_rvqm["Portfolio"] == selected_portfolio]
        if len(rvqm_row) == 1:
            selected_client_row = rvqm_row.iloc[0]
            st.caption(f"Carteira-modelo: **{selected_client_row['Tipo']}**")
        elif len(rvqm_row) > 1:
            model_labels = {
                idx: f"{row['Tipo']} · {row['Custodiante']} · {row['Nr Conta']}"
                for idx, row in rvqm_row.iterrows()
            }
            chosen_idx = st.selectbox(
                "Carteira-modelo",
                options=list(model_labels),
                format_func=model_labels.__getitem__,
                help="Este portfolio possui mais de uma carteira-modelo aderida.",
            )
            selected_client_row = rvqm_row.loc[chosen_idx]

    origem_posicao = st.radio(
        "Origem da posição",
        options=[ORIGEM_FIBERY, ORIGEM_MANUAL],
        index=0,
        help=(
            "Fibery: posição ingestada. Posição manual: upload CSV/Excel substitui "
            "integralmente a posição do cliente (útil quando a ingestão está atrasada)."
        ),
    )
    is_manual_position = origem_posicao == ORIGEM_MANUAL

    uploaded_positions = None
    manual_position_date = datetime.now().date()
    allow_partial_match = False

    if is_manual_position:
        manual_position_date = st.date_input(
            "Data da posição",
            value=datetime.now().date(),
            format="DD/MM/YYYY",
        )
        uploaded_positions = st.file_uploader(
            "Arquivo de posições (CSV ou Excel)",
            type=["csv", "xlsx", "xls"],
            help=(
                "Obrigatório: Ativo, Quantidade. "
                "Saldo recomendado para calcular o PL; sem Saldo use Override Saldo Total."
            ),
        )
        st.download_button(
            "Baixar template",
            data=template_csv_bytes(variant="rvqm"),
            file_name="template_posicao_manual_rvqm.csv",
            mime="text/csv",
            width="stretch",
        )
        allow_partial_match = st.checkbox(
            "Analisar apenas ativos com match",
            value=False,
            help="Se marcado, ignora unmatched/ambiguous e segue só com os matched.",
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

if is_manual_position and uploaded_positions is None:
    st.info(
        "Envie um arquivo CSV/Excel com **Ativo** e **Quantidade** "
        "(use o template na sidebar). A posição manual substitui integralmente o Fibery."
    )
    st.stop()

if selected_client_row is None:
    st.error(
        f"Portfolio '{selected_portfolio}' não encontrado em Cliente com Carteira Modelo."
    )
    st.stop()

strategy_tipo = str(selected_client_row["Tipo"]).strip()
if (
    pd.isna(selected_client_row["Tipo"])
    or not strategy_tipo
    or strategy_tipo.lower() in {"nan", "none", "<na>"}
):
    st.error(
        f"Portfolio '{selected_portfolio}' sem Carteira Modelo definida no Fibery."
    )
    st.stop()

equity_position_to_total_portfolio = selected_client_row["Percentual do PL"]
equity_position_custodian = selected_client_row["Custodiante"]
equity_position_account = selected_client_row["Nr Conta"]

# =============================================================================
# Carregamento de dados
# =============================================================================

if st.button("Atualizar BLP Relay", type="primary"):
    load_google_sheet_market_data.clear()
    st.toast("Cache do BLP Relay limpo. Buscando dados atualizados...")

with st.spinner(f"Carregando composição da carteira {strategy_tipo}..."):
    equities_portfolio = load_equities_portfolio(tipo=strategy_tipo)

with st.spinner("Carregando taxonomia de ativos..."):
    df_assets_full = load_assets()
    assets_taxonomy = df_assets_full[["Name", "Classificação Instrumento"]].rename(
        columns={"Name": "code_key"}
    )

if is_manual_position:
    try:
        df_upload = parse_external_positions_file(
            uploaded_positions,
            require_saldo=False,
        )
        df_upload = require_quantidade(df_upload)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    df_match_report = match_external_positions(df_upload, df_assets_full)
    summary = match_summary(df_match_report)
    has_match_issues = summary[MATCH_UNMATCHED] + summary[MATCH_AMBIGUOUS] > 0

    with st.expander("Qualidade do match", expanded=has_match_issues):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", summary["total"])
        m2.metric("Matched", summary[MATCH_MATCHED])
        m3.metric("Ambiguous", summary[MATCH_AMBIGUOUS])
        m4.metric("Unmatched", summary[MATCH_UNMATCHED])
        st.dataframe(
            style_table(
                df_match_report.drop(columns=["_asset_idx"], errors="ignore"),
                numeric_cols_format_as_float=["Saldo"],
                left_align_cols=["Ativo", "Status Match", "Nome Ativo", "Alias", "Candidatos"],
            ),
            hide_index=True,
        )

    try:
        positions_carteira, _ = enrich_external_positions(
            df_upload,
            df_assets_full,
            portfolio_label=selected_portfolio,
            position_date=datetime.combine(manual_position_date, datetime.min.time()),
            allow_partial=allow_partial_match,
        )
    except ValueError as e:
        st.warning(str(e))
        st.info(
            "Corrija os códigos no arquivo, cadastre os ativos no Fibery, "
            "ou marque **Analisar apenas ativos com match** na sidebar."
        )
        st.stop()

    if positions_carteira.empty:
        st.error(
            "Nenhuma posição enriquecida com Classificação do Conjunto. "
            "Verifique o cadastro dos ativos."
        )
        st.stop()

    st.info(
        f"**Posição manual** · {selected_portfolio} · "
        f"data {manual_position_date.strftime('%d/%m/%Y')} · "
        f"{len(positions_carteira)} linha(s) — substitui integralmente o Fibery."
    )
else:
    with st.spinner("Carregando posições..."):
        df_positions = load_positions()
    positions_carteira = df_positions[df_positions["Portfolio"] == selected_portfolio]

with st.spinner("Carregando dados de mercado do Google Sheets..."):
    try:
        market_data = load_google_sheet_market_data()
    except Exception as e:
        st.error(f"Erro ao carregar dados do BLP Relay: {str(e)}")
        st.stop()

if equities_portfolio.empty:
    st.warning(f"Nenhuma composição de carteira {strategy_tipo} disponível para exibir.")
    st.stop()

if market_data.empty:
    st.warning("Nenhum dado de mercado disponível no BLP Relay.")
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

if equity_positions.empty:
    st.info(
        f"Nenhuma posição em Ações ou BDRs encontrada para {selected_portfolio}. "
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
    .merge(
        assets_taxonomy,
        how="left",
        on="code_key",
        suffixes=("", "_taxonomy"),
    )
)

current_market_data["Classificação Instrumento"] = (
    current_market_data["Classificação Instrumento"]
    .fillna(current_market_data["Classificação Instrumento_taxonomy"])
    .fillna("Ação")
)
current_market_data = current_market_data.drop(
    columns=["Classificação Instrumento_taxonomy"],
    errors="ignore",
)
current_market_data["Lote"] = current_market_data["Classificação Instrumento"].map(instrument_lot_size)

saldo_series = (
    positions_carteira["Saldo"]
    if not positions_carteira.empty and "Saldo" in positions_carteira.columns
    else pd.Series(dtype=float)
)
saldo_completo = (
    not positions_carteira.empty
    and not saldo_series.empty
    and bool(saldo_series.notna().all())
)

if positions_carteira.empty:
    if portfolio_total_balance_override == 0:
        st.error(
            f"O portfolio {selected_portfolio} não possui posições registradas. "
            "Informe o saldo total disponível no campo **Override Saldo Total** na barra lateral."
        )
        st.stop()
    calculated_portfolio_total_balance = 0.0
elif not saldo_completo:
    if portfolio_total_balance_override == 0:
        st.error(
            "Há linhas sem **Saldo** na posição"
            + (" manual" if is_manual_position else "")
            + ". Inclua a coluna Saldo no arquivo ou informe o "
            "**Override Saldo Total** na barra lateral."
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

if positions_carteira.empty:
    position_date_label = "sem posição registrada"
elif is_manual_position:
    position_date_label = (
        f"posição manual em {manual_position_date.strftime('%d/%m/%Y')}"
    )
else:
    position_date_label = (
        f"posição em {positions_carteira['Data Posição'].max().strftime('%d/%m/%Y')}"
    )

origem_label = "manual" if is_manual_position else "Fibery"

st.markdown(
    f"<p style='color:#888; font-size:0.85rem; margin-bottom:6px;'>"
    f"{selected_portfolio} &nbsp;·&nbsp; "
    f"{strategy_tipo} &nbsp;·&nbsp; "
    f"{equity_position_custodian} &nbsp;·&nbsp; "
    f"{equity_position_account} &nbsp;·&nbsp; "
    f"{len(equity_positions)} ativos &nbsp;·&nbsp; "
    f"{origem_label} &nbsp;·&nbsp; "
    f"{position_date_label}"
    f"</p>",
    unsafe_allow_html=True,
)

metric_cols = st.columns(4)
metric_cols[0].metric(f"Ativos no Portfolio {strategy_tipo}", len(equity_positions))
metric_cols[1].metric(
    "Saldo Total" + (" (override)" if portfolio_total_balance_override > 0 else ""),
    f"R$ {portfolio_total_balance:,.0f}",
)
metric_cols[2].metric("Percentual do PL", f"{equity_position_to_total_portfolio*100:.1f}%")
metric_cols[3].metric(f"Saldo Alvo {strategy_tipo}", f"R$ {target_equity_balance:,.0f}")

current_market_data["Quantidade"] = current_market_data["Quantidade"].fillna(0).astype(float)
current_market_data["Nome Ativo"] = current_market_data["Nome Ativo"].fillna(
    current_market_data["code_key"]
)

ignore_options = sorted(
    code
    for code in current_market_data["code_key"].dropna().astype(str).str.strip().unique()
    if code
)
model_codes = set(
    current_portfolio["code_key"].dropna().astype(str).str.strip().tolist()
)
ignore_labels = {
    code: f"{code} · fora da carteira-modelo" if code not in model_codes else code
    for code in ignore_options
}

ignored_codes = st.multiselect(
    "Ignorar ativos",
    options=ignore_options,
    format_func=ignore_labels.__getitem__,
    key=f"rvqm_ignore_{selected_portfolio}_{strategy_tipo}",
    help=(
        "Posições excluídas da sleeve negociável: não geram compra/venda e o "
        "saldo atual é abatido do alvo da carteira-modelo. Use para papéis que "
        "não podem ser negociados."
    ),
)

ignored_mask = current_market_data["code_key"].astype(str).isin(ignored_codes)
ignored_holdings = current_market_data.loc[ignored_mask].copy()
tradable = current_market_data.loc[~ignored_mask].copy()

ignored_saldo = float(
    (ignored_holdings["Quantidade"] * ignored_holdings["LAST_PRICE"]).sum(skipna=True)
)
if pd.isna(ignored_saldo):
    ignored_saldo = 0.0
effective_target_equity_balance = max(float(target_equity_balance) - ignored_saldo, 0.0)

if tradable.empty:
    st.warning(
        "Todos os ativos foram ignorados. Desmarque algum para calcular o rebalanceamento."
    )
    st.stop()

tradable = compute_rebalance_columns(tradable, effective_target_equity_balance)
tradable = tradable.sort_values("Valor Compra/Venda", ascending=False)
if ignored_holdings.empty:
    current_market_data = tradable
else:
    ignored_holdings = mark_ignored_assets(ignored_holdings).sort_values("Nome Ativo")
    current_market_data = pd.concat(
        [tradable, ignored_holdings],
        ignore_index=True,
    )

if ignored_codes:
    st.caption(
        f"{len(ignored_codes)} ativo(s) ignorado(s) · "
        f"R$ {ignored_saldo:,.0f} fora da sleeve · "
        f"saldo alvo negociável R$ {effective_target_equity_balance:,.0f}."
    )

display_columns = [
    "TIME",
    "Nome Ativo",
    "Classificação Instrumento",
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
        left_align_cols=["Nome Ativo", "Ticker Bloomberg", "Classificação Instrumento"],
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

missing_targets = current_market_data.loc[
    current_market_data["weight_pct"].isna()
    & ~current_market_data["code_key"].astype(str).isin(ignored_codes),
    "Nome Ativo",
].tolist()
if missing_targets:
    st.info(
        f"Ativos sem peso alvo na carteira {strategy_tipo} atual: "
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
net_cash = val_sells - val_buys

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

        if positions_carteira.empty:
            position_date = pd.Timestamp.today().strftime("%Y%m%d")
        else:
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
