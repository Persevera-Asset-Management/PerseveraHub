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
    clients_from_snapshot,
    enrich_snapshot_with_officers,
    get_emissor_column,
    load_positions,
    load_target_allocations,
)
from utils.table import style_table
from utils.ui import show_data_freshness

st.title("Otimizador de Alocação")

ASSET_MODES = ("Cotas (discreto)", "Valor total (contínuo)")
DEFAULT_ASSETS = pd.DataFrame([
    {
        "Ticker": "CRA022008NF",
        "Modo": ASSET_MODES[0],
        "Cotas": 18,
        "PU (R$)": 1059.38,
        "Valor total (R$)": np.nan,
    },
    {
        "Ticker": "M8CREDIT",
        "Modo": ASSET_MODES[1],
        "Cotas": np.nan,
        "PU (R$)": np.nan,
        "Valor total (R$)": 59850.30,
    },
])


def _prepare_positions(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    df.replace(" ", np.nan, inplace=True)
    df.dropna(subset=["Nome Ativo", "Classificação do Conjunto"], inplace=True)
    df = get_emissor_column(df)
    df.rename(columns={"Emissor": "Emissor Geral"}, inplace=True)
    return df


@st.cache_data(ttl=3600, show_spinner="Montando snapshot de portfólios...")
def _load_allocation_snapshot() -> dict:
    df_raw = load_positions()
    df = _prepare_positions(df_raw)
    df_target_allocations = load_target_allocations(include_limits=False)
    snapshot = build_portfolio_snapshot(df, df_target_allocations)
    return enrich_snapshot_with_officers(snapshot)


def _parse_assets(df_assets: pd.DataFrame) -> list[Asset]:
    assets: list[Asset] = []
    for _, row in df_assets.iterrows():
        ticker = str(row.get("Ticker", "")).strip()
        if not ticker or ticker.lower() == "nan":
            continue

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
            ))
        else:
            valor = row.get("Valor total (R$)")
            if pd.isna(valor):
                raise ValueError(
                    f"Ativo '{ticker}': informe Valor total (R$) para modo contínuo."
                )
            assets.append(Asset(ticker, total_value=float(valor)))

    return assets


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
    exclude=exclude or None,
)
st.caption(f"{len(clients_preview)} clientes no universo selecionado · {len(snapshot)} carteiras no snapshot")

st.markdown("#### Ativos disponíveis para alocação")
assets_df = st.data_editor(
    DEFAULT_ASSETS,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", required=True),
        "Modo": st.column_config.SelectboxColumn("Modo", options=list(ASSET_MODES), required=True),
        "Cotas": st.column_config.NumberColumn("Cotas", min_value=1, step=1, format="%d"),
        "PU (R$)": st.column_config.NumberColumn("PU (R$)", min_value=0.01, format="%.2f"),
        "Valor total (R$)": st.column_config.NumberColumn("Valor total (R$)", min_value=0.01, format="%.2f"),
    },
    hide_index=True,
)

run_allocation = st.button("Executar alocação", type="primary")

allocation_context = {
    "officer_filter": tuple(sorted(selected_officers)),
    "exclude": tuple(sorted(exclude)),
    "objective": objective,
    "min_pct": min_pct,
    "max_pct": max_pct,
    "min_cash_pct_after": min_cash_pct_after,
    "consider_existing": consider_existing,
    "topup": topup,
    "topup_method": topup_method,
    "assets": tuple(
        (str(r["Ticker"]).strip(), r["Modo"], r.get("Cotas"), r.get("PU (R$)"), r.get("Valor total (R$)"))
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

    st.code(result.summary(), language=None)

    df_result = result.to_dataframe()
    if not df_result.empty:
        st.dataframe(
            style_table(
                df_result,
                numeric_cols_format_as_float=["Cotas/Valor", "Valor (R$)", "Caixa após (R$)"],
                percent_cols=["% PL (nova)", "Exposição total %", "Caixa após %"],
            ),
            hide_index=True,
            use_container_width=True,
            height="content"
        )

    else:
        st.info("Nenhuma alocação gerada com os parâmetros informados.")

elif "allocation_result" in st.session_state:
    st.info("Parâmetros alterados. Clique em **Executar alocação** para recalcular.")
