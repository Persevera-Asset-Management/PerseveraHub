import numpy as np
import pandas as pd
import streamlit as st

from persevera_tools.quant_research.allocation_engine import (
    AllocationConfig,
    AllocationEngine,
    Asset,
)

from services.position_service import (
    build_portfolio_snapshot,
    build_ticker_issuer_lookup,
    clients_from_snapshot,
    enrich_assets_with_issuers,
    enrich_snapshot_with_officers,
    get_emissor_column,
    issuer_lookup_from_snapshot,
    load_positions,
    load_target_allocations,
)
from utils.table import style_table
from utils.ui import show_data_freshness

st.title("Otimizador de Alocação")

ASSET_MODES = ("Cotas (discreto)", "Valor total (contínuo)")
ASSET_EDITOR_COLUMNS = [
    "Ticker",
    "Modo",
    "Cotas",
    "PU (R$)",
    "Valor total (R$)",
    "Emissor",
]
DEFAULT_ASSETS = pd.DataFrame([
    {
        "Ticker": "CRA022008NF",
        "Modo": ASSET_MODES[0],
        "Cotas": 18,
        "PU (R$)": 1059.38,
        "Valor total (R$)": np.nan,
        "Emissor": pd.NA,
    },
    {
        "Ticker": "M8CREDIT",
        "Modo": ASSET_MODES[1],
        "Cotas": np.nan,
        "PU (R$)": np.nan,
        "Valor total (R$)": 59850.30,
        "Emissor": pd.NA,
    },
])


def _coerce_assets_editor_df(state) -> pd.DataFrame:
    """Normaliza o estado do data_editor (dict ragged ou DataFrame) para colunas fixas."""
    if state is None:
        return DEFAULT_ASSETS.copy()

    if isinstance(state, pd.DataFrame):
        df = state.copy()
    elif isinstance(state, dict):
        try:
            df = pd.DataFrame(state)
        except ValueError:
            lengths = [
                len(v)
                for v in state.values()
                if isinstance(v, (list, tuple, pd.Series, np.ndarray))
            ]
            n = min(lengths) if lengths else 0
            trimmed = {}
            for key, value in state.items():
                if isinstance(value, (list, tuple, pd.Series, np.ndarray)):
                    trimmed[key] = list(value)[:n]
                else:
                    trimmed[key] = value
            df = pd.DataFrame(trimmed) if n > 0 else pd.DataFrame(columns=ASSET_EDITOR_COLUMNS)
    else:
        try:
            df = pd.DataFrame(state)
        except ValueError:
            return DEFAULT_ASSETS.copy()

    for col in ASSET_EDITOR_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[ASSET_EDITOR_COLUMNS].reset_index(drop=True)


def _prepare_positions(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    df.replace(" ", np.nan, inplace=True)
    df.dropna(subset=["Nome Ativo", "Classificação do Conjunto"], inplace=True)
    df = get_emissor_column(df)
    return df


@st.cache_data(ttl=3600, show_spinner="Montando snapshot de portfólios...")
def _load_allocation_snapshot() -> dict:
    df_raw = load_positions()
    df = _prepare_positions(df_raw)
    df_target_allocations = load_target_allocations(include_limits=False)
    snapshot = build_portfolio_snapshot(df, df_target_allocations)
    return enrich_snapshot_with_officers(snapshot)


def _issuer_from_row(row: pd.Series) -> str | None:
    emissor = row.get("Emissor")
    if pd.isna(emissor) or not str(emissor).strip():
        return None
    return str(emissor).strip()


def _parse_assets(df_assets: pd.DataFrame) -> list[Asset]:
    assets: list[Asset] = []
    for _, row in df_assets.iterrows():
        ticker = str(row.get("Ticker", "")).strip()
        if not ticker or ticker.lower() == "nan":
            continue

        issuer = _issuer_from_row(row)
        modo = row.get("Modo", ASSET_MODES[0])
        if modo == ASSET_MODES[0]:
            cotas = row.get("Cotas")
            pu = row.get("PU (R$)")
            if pd.isna(cotas) or pd.isna(pu):
                raise ValueError(
                    f"Ativo '{ticker}': informe Cotas e PU (R$) para modo discreto."
                )
            assets.append(Asset(
                ticker,
                total_units=int(cotas),
                unit_price=float(pu),
                issuer=issuer,
            ))
        else:
            valor = row.get("Valor total (R$)")
            if pd.isna(valor):
                raise ValueError(
                    f"Ativo '{ticker}': informe Valor total (R$) para modo contínuo."
                )
            assets.append(Asset(ticker, total_value=float(valor), issuer=issuer))

    return assets


def _allocations_to_display_df(result) -> pd.DataFrame:
    rows = []
    for a in result.allocations:
        rows.append({
            "Cliente": a.client_code,
            "Ativo": a.ticker,
            "Emissor": a.issuer,
            "Cotas/Valor": a.units,
            "Valor (R$)": round(a.value, 2),
            "% PL (nova)": round(a.pct_pl * 100, 2),
            "Exposição Total (%)": round(a.total_exposure * 100, 2),
            "Emissor Antes (%)": (
                round(a.issuer_exposure_before_pct * 100, 2)
                if a.issuer_exposure_before_pct is not None else None
            ),
            "Emissor Após (%)": (
                round(a.issuer_exposure_after_pct * 100, 2)
                if a.issuer_exposure_after_pct is not None else None
            ),
            "Restrição": a.binding_constraint,
            "Caixa Após (R$)": round(a.cash_after, 2),
            "Caixa Após (%)": round(a.cash_pct_after * 100, 2),
        })
    return pd.DataFrame(rows)


with st.sidebar:
    st.header("Universo de clientes")

    snapshot = _load_allocation_snapshot()
    officer_options = sorted({
        data["officer_atual"]
        for data in snapshot.values()
        if data.get("officer_atual") is not None and pd.notna(data.get("officer_atual"))
    })
    selected_officers = st.multiselect(
        "Filtrar por officer",
        options=officer_options,
        default=[],
        help="Deixe vazio para incluir todos os officers.",
    )

    selected_tipos_cliente = st.multiselect(
        "Tipo de cliente",
        options=["PF", "PJ"],
        default=[],
        help="Deixe vazio para incluir todos os tipos. Fundo e PIC não entram nesta lista.",
    )

    custodian_options = sorted({
        custodiante
        for data in snapshot.values()
        for custodiante in (data.get("custodiantes") or [])
    })
    selected_custodians = st.multiselect(
        "Instituição (custodiante)",
        options=custodian_options,
        default=[],
        help=(
            "Deixe vazio para incluir todas as instituições. "
            "Considera o custodiante das posições atuais do cliente."
        ),
    )

    portfolio_codes = sorted(snapshot.keys())
    exclude = st.multiselect(
        "Excluir carteiras",
        options=portfolio_codes,
        default=[],
    )

    st.divider()
    st.header("Parâmetros de alocação")
    objective = st.selectbox(
        "Objetivo",
        options=["max_clients", "max_volume"],
        format_func=lambda x: "Maximizar clientes" if x == "max_clients" else "Maximizar volume",
        help=(
            "Maximizar clientes: oferta pequena, democratizar entre assessores/clientes. "
            "Maximizar volume: oferta grande, colocar volume nos clientes com maior capacidade."
        ),
    )
    min_pct = st.number_input("Exposição mínima (% PL)", min_value=0.0, max_value=100.0, value=1.5, step=0.1)
    max_pct = st.number_input("Exposição máxima (% PL)", min_value=0.0, max_value=100.0, value=2.0, step=0.1)
    max_issuer_pct = st.number_input(
        "Exposição máx. por emissor (% PL)",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=0.5,
        help="Teto de concentração em RF por emissor/devedor. Use 0 para desabilitar.",
    )
    min_cash_pct_after = st.number_input(
        "Caixa mínimo pós-alocação (% PL)", min_value=0.0, max_value=100.0, value=5.0, step=0.5
    )
    consider_existing = st.checkbox("Considerar posição existente", value=True)
    topup = st.checkbox("Distribuir remanescente (top-up)", value=True)
    topup_method = st.selectbox(
        "Método de top-up",
        options=["proportional", "equal"],
        format_func=lambda x: "Proporcional" if x == "proportional" else "Igualitário",
        disabled=not topup,
    )

show_data_freshness("positions", label="Posições", ttl_minutes=60)

clients_preview = clients_from_snapshot(
    snapshot,
    officer_filter=selected_officers or None,
    tipo_cliente_filter=selected_tipos_cliente or None,
    exclude=exclude or None,
    custodian_filter=selected_custodians or None,
)
st.caption(f"{len(clients_preview)} clientes no universo selecionado · {len(snapshot)} carteiras no snapshot")

cadastro_issuer_lookup = build_ticker_issuer_lookup()
snapshot_issuer_lookup = issuer_lookup_from_snapshot(snapshot)

assets_seed = (
    st.session_state.allocation_assets_editor
    if "allocation_assets_editor" in st.session_state
    else DEFAULT_ASSETS.copy()
)
editor_seed = enrich_assets_with_issuers(
    _coerce_assets_editor_df(assets_seed),
    cadastro_issuer_lookup,
    snapshot_issuer_lookup,
)

st.markdown("#### Ativos disponíveis para alocação")
st.caption(
    "Emissor é preenchido automaticamente pelo cadastro Fibery; edite manualmente se necessário."
)
assets_df = st.data_editor(
    editor_seed,
    num_rows="dynamic",
    width="stretch",
    key="allocation_assets_editor",
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", required=True),
        "Modo": st.column_config.SelectboxColumn("Modo", options=list(ASSET_MODES), required=True),
        "Cotas": st.column_config.NumberColumn("Cotas", min_value=1, step=1, format="%d"),
        "PU (R$)": st.column_config.NumberColumn("PU (R$)", min_value=0.01, format="%.2f"),
        "Valor total (R$)": st.column_config.NumberColumn("Valor total (R$)", min_value=0.01, format="%.2f"),
        "Emissor": st.column_config.TextColumn(
            "Emissor",
            help="Preenchido pelo cadastro; necessário para o limite por emissor.",
        ),
    },
    hide_index=True,
)
assets_df = enrich_assets_with_issuers(
    _coerce_assets_editor_df(assets_df),
    cadastro_issuer_lookup,
    snapshot_issuer_lookup,
)

if max_issuer_pct > 0:
    missing_issuers = [
        str(r["Ticker"]).strip()
        for _, r in assets_df.iterrows()
        if str(r.get("Ticker", "")).strip()
        and str(r.get("Ticker", "")).strip().lower() != "nan"
        and not _issuer_from_row(r)
    ]
    if missing_issuers:
        st.warning(
            "Limite por emissor ativo, mas sem emissor para: "
            + ", ".join(missing_issuers)
            + ". Esses ativos ignorarão o teto de emissor."
        )

run_allocation = st.button("Executar alocação", type="primary")

allocation_context = {
    "officer_filter": tuple(sorted(selected_officers)),
    "tipo_cliente_filter": tuple(sorted(selected_tipos_cliente)),
    "exclude": tuple(sorted(exclude)),
    "custodian_filter": tuple(sorted(selected_custodians)),
    "objective": objective,
    "min_pct": min_pct,
    "max_pct": max_pct,
    "max_issuer_pct": max_issuer_pct,
    "min_cash_pct_after": min_cash_pct_after,
    "consider_existing": consider_existing,
    "topup": topup,
    "topup_method": topup_method,
    "assets": tuple(
        (
            str(r["Ticker"]).strip(),
            r["Modo"],
            r.get("Cotas"),
            r.get("PU (R$)"),
            r.get("Valor total (R$)"),
            _issuer_from_row(r),
        )
        for _, r in assets_df.iterrows()
        if str(r.get("Ticker", "")).strip() and str(r.get("Ticker", "")).strip().lower() != "nan"
    ),
}

if run_allocation:
    try:
        assets = _parse_assets(assets_df)
        if not assets:
            st.error("Informe ao menos um ativo válido.")
            st.stop()

        if not clients_preview:
            st.warning("Nenhum cliente elegível com os filtros atuais.")
            st.stop()

        config = AllocationConfig(
            objective=objective,
            min_pct=min_pct / 100,
            max_pct=max_pct / 100,
            max_issuer_pct=max_issuer_pct / 100 if max_issuer_pct > 0 else None,
            min_cash_pct_after=min_cash_pct_after / 100,
            consider_existing=consider_existing,
            topup=topup,
            topup_method=topup_method,
        )

        with st.spinner("Calculando alocação..."):
            result = AllocationEngine(config).allocate(clients_preview, assets)

        st.session_state.allocation_result = result
        st.session_state.allocation_context = allocation_context

    except ValueError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Erro ao executar alocação: {exc}")

if (
    "allocation_result" in st.session_state
    and st.session_state.get("allocation_context") == allocation_context
):
    result = st.session_state.allocation_result

    st.markdown("---")
    st.markdown("#### Resultado")

    kpi_cols = st.columns(3)
    with kpi_cols[0]:
        st.metric("Clientes alocados", result.unique_clients)
    with kpi_cols[1]:
        st.metric("Volume alocado", f"R$ {result.total_value_allocated:,.2f}")
    with kpi_cols[2]:
        st.metric("Linhas de alocação", len(result.allocations))

    if result.warnings:
        for warning in result.warnings:
            st.warning(warning)

    st.code(result.summary(), language=None)

    df_result = _allocations_to_display_df(result)
    if not df_result.empty:
        st.dataframe(
            style_table(
                df_result,
                numeric_cols_format_as_float=["Cotas/Valor", "Valor (R$)", "Caixa Após (R$)"],
                percent_cols=[
                    "% PL (nova)",
                    "Exposição Total (%)",
                    "Emissor Antes (%)",
                    "Emissor Após (%)",
                    "Caixa Após (%)",
                ],
            ),
            hide_index=True,
            width="stretch",
            height="content"
        )

    else:
        st.info("Nenhuma alocação gerada com os parâmetros informados.")

elif "allocation_result" in st.session_state:
    st.info("Parâmetros alterados. Clique em **Executar alocação** para recalcular.")
