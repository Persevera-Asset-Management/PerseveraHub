import pandas as pd
import streamlit as st
import streamlit_highcharts as hct

from utils.table import style_table
from utils.chart_helpers import create_chart, render_chart

from services.position_service import get_emissor_column, load_assets, load_issuers

st.title("XPCV · XBridge")

REQUIRED_COLUMNS = [
    "Emissor / Risco",
    "Duration",
    "Indexador",
    "Juros",
    "Amortização",
    "Isento",
    "Rating",
    "Risco",
    "Vencimento",
    "Ticker",
    "Vol. BID",
    "Qtd. BID",
    "BID Mercado",
    "OFFER Mercado",
    "Qtd. OFFER",
    "Vol. OFFER",
    "Tax. Mín. / Tax. Máx.",
]

ASSET_STATUS_CANDIDATES = [
    "Status",
    "Status do Ativo",
    "Status Cadastro",
    "Status de Cadastro",
    "Status Aprovação",
    "Status da Aprovação",
]

ASSET_COLUMNS = [
    "Name",
    "Alias",
    "Indexador",
    "Data Vencimento",
    "Nome Emissor",
    "Nome Devedor",
    "Emissor",
    "Status do Emissor",
]

DISPLAY_COLUMNS = [
    "Ticker",
    "Emissor / Risco",
    "Emissor",
    "Status do Emissor",
    "Indexador XBridge",
    "Indexador Fibery",
    "Vencimento XBridge",
    "Data Vencimento",
    "Isento",
    "Rating",
    "Qtd. BID",
    "Vol. BID",
    "BID Mercado",
    "OFFER Mercado",
    "Qtd. OFFER",
    "Vol. OFFER",
    "Tax. Mín. / Tax. Máx.",
]

NUMERIC_COLUMNS = [
    "Duration",
    "Risco",
    "Vol. BID",
    "Qtd. BID",
    "BID Mercado",
    "OFFER Mercado",
    "Qtd. OFFER",
    "Vol. OFFER",
]

PERCENT_COLUMNS = ["BID Mercado", "OFFER Mercado"]
FLOAT_COLUMNS = ["Duration", "Vol. BID", "Vol. OFFER"]
INTEGER_COLUMNS = ["Risco", "Qtd. BID", "Qtd. OFFER"]
DATE_COLUMNS = ["Vencimento XBridge", "Data Vencimento"]

def normalize_text(value) -> str:
    """Normaliza texto para chaves de comparação determinísticas."""
    if pd.isna(value):
        return ""
    return str(value).strip().upper()

def parse_brazilian_number(series: pd.Series) -> pd.Series:
    """Converte números em formato brasileiro para float."""
    normalized = (
        series.astype(str)
        .str.strip()
        .str.replace("%", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .replace({"": pd.NA, "-": pd.NA, "nan": pd.NA, "None": pd.NA})
    )
    return pd.to_numeric(normalized, errors="coerce")

def type_xbridge_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica tipos úteis às colunas vindas do CSV da XBridge."""
    df = df.copy()
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = parse_brazilian_number(df[column])

    df["Vencimento"] = pd.to_datetime(df["Vencimento"], format="%d/%m/%y", errors="coerce")
    return df

def display_table(df: pd.DataFrame, columns: list[str]):
    """Renderiza tabela com formatação compatível com os tipos tratados."""
    visible_columns = [col for col in columns if col in df.columns]
    return style_table(
        df[visible_columns],
        date_cols=[col for col in DATE_COLUMNS if col in visible_columns],
        percent_cols=[col for col in PERCENT_COLUMNS if col in visible_columns],
        numeric_cols_format_as_float=[col for col in FLOAT_COLUMNS if col in visible_columns],
        numeric_cols_format_as_int=[col for col in INTEGER_COLUMNS if col in visible_columns],
        left_align_cols=["Ticker", "Emissor / Risco", "Alias", "Emissor"],
    )

def read_xbridge_csv(uploaded_file) -> pd.DataFrame:
    """Lê o CSV exportado pela XBridge e valida seu layout esperado."""
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, sep=";", dtype=str, encoding="utf-8-sig")
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Colunas ausentes no CSV: {', '.join(missing_columns)}")

    df = df[REQUIRED_COLUMNS].copy()
    df["Ticker"] = df["Ticker"].map(normalize_text)
    df = df[df["Ticker"] != ""]
    df = type_xbridge_columns(df)
    return df.drop_duplicates(subset=["Ticker"], keep="first")

def find_asset_status_column(df_assets: pd.DataFrame) -> str | None:
    """Identifica a coluna de status do cadastro de ativos, se existir."""
    for column in ASSET_STATUS_CANDIDATES:
        if column in df_assets.columns:
            return column

    status_columns = [
        column
        for column in df_assets.columns
        if "status" in column.casefold() and "emissor" not in column.casefold()
    ]
    return status_columns[0] if status_columns else None

def load_data():
    """Carrega todos os dados necessários para a página."""
    with st.spinner("Carregando dados...", show_time=True):
        st.session_state.df_assets = load_assets()
        st.session_state.df_issuers = load_issuers()

for key in ("df_assets", "df_issuers"):
    st.session_state.setdefault(key, None)

with st.sidebar:
    st.header("Parâmetros")
    uploaded_file = st.file_uploader(
        "Upload CSV XBridge",
        type=["csv"],
        help="Arquivo exportado da XBridge no layout padrão separado por ponto e vírgula.",
    )
    btn_run = st.button(
        "Processar arquivo",
        width="stretch",
        disabled=uploaded_file is None,
    )

if btn_run:
    load_data()

st.markdown(
    "Faça upload do CSV exportado da XBridge para cruzar os tickers disponíveis "
    "com o cadastro de ativos e emissores do Fibery."
)

if uploaded_file is None:
    st.info("Envie um arquivo CSV para iniciar a análise.")
    st.stop()

try:
    df_xbridge = read_xbridge_csv(uploaded_file)
except Exception as exc:
    st.error(f"Não foi possível ler o CSV da XBridge: {exc}")
    st.stop()

if st.session_state.df_assets is None or st.session_state.df_issuers is None:
    st.warning("Clique em **Processar arquivo** para carregar os cadastros do Fibery e executar o cruzamento.")
    st.stop()

try:
    df_assets = get_emissor_column(st.session_state.df_assets)
    df_issuers = st.session_state.df_issuers[["Nome Emissor", "Status do Emissor"]].drop_duplicates(
        subset=["Nome Emissor"],
        keep="first",
    )
    df_assets = df_assets.merge(
        df_issuers,
        left_on="Emissor",
        right_on="Nome Emissor",
        how="left",
    )

    df_assets["Ticker Match"] = df_assets["Name"].map(normalize_text)
    asset_columns = [col for col in ASSET_COLUMNS if col in df_assets.columns]
    df_assets_match = df_assets[["Ticker Match", *asset_columns]].drop_duplicates(
        subset=["Ticker Match"],
        keep="first",
    )

    df = df_xbridge.merge(
        df_assets_match,
        left_on="Ticker",
        right_on="Ticker Match",
        how="left",
    )

    df["Status Cadastro"] = df["Name"].notna().map({True: "Cadastrado", False: "Não cadastrado"})
    df["Indexador XBridge"] = df.get("Indexador_x", df.get("Indexador"))
    df["Indexador Fibery"] = df.get("Indexador_y", pd.NA)
    if "Indexador_x" in df.columns:
        df["Indexador XBridge"] = df["Indexador_x"]
    df["Vencimento XBridge"] = df["Vencimento"]
    df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"], errors="coerce")
    df["Aprovado"] = df["Status do Emissor"].isin(["Aprovado", "Name Lending"])
    df["Isento"] = df["Isento"].astype(str).str.casefold().eq("sim")

    df_approved = df[df["Aprovado"]].copy()
    df_missing = df[df["Status Cadastro"].eq("Não cadastrado")].copy()
    df_registered_not_approved = df[
        df["Status Cadastro"].eq("Cadastrado") & ~df["Aprovado"]
    ].copy()

    total_assets = len(df)
    total_registered = int(df["Name"].notna().sum())
    total_approved = len(df_approved)
    total_missing = len(df_missing)

    cols = st.columns(4)
    cols[0].metric("Tickers no CSV", total_assets)
    cols[1].metric("Cadastrados no Fibery", total_registered)
    cols[2].metric("Aprovados para negociação", total_approved)
    cols[3].metric("Não cadastrados", total_missing)

    tabs = st.tabs(["Aprovados", "Não cadastrados", "Cadastrados não aprovados", "Base cruzada"])

    with tabs[0]:
        only_with_offer = st.checkbox("Apenas com OFFER disponível", value=True)
        df_display = df_approved.copy()
        if only_with_offer:
            has_offer = (
                df_display["Vol. OFFER"].fillna(0).gt(0)
                | df_display["Qtd. OFFER"].fillna(0).gt(0)
            )
            df_display = df_display[has_offer]

        if df_display.empty:
            st.info("Nenhum ativo aprovado encontrado com os filtros aplicados.")
        else:
            summary = (
                df_display.groupby("Indexador XBridge", dropna=False)
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
            )
            summary["label"] = summary["Indexador XBridge"].fillna("Sem indexador").astype(str)

            n_metric_cols = min(len(summary), 6)
            metric_cols = st.columns(n_metric_cols)
            for idx, (_, row) in enumerate(summary.iterrows()):
                metric_cols[idx % n_metric_cols].metric(row["label"], int(row["count"]))

            st.divider()

            tab_labels = ["Todos"] + summary["label"].tolist()
            subtabs = st.tabs(tab_labels)

            with subtabs[0]:
                st.dataframe(
                    display_table(df_display, DISPLAY_COLUMNS),
                    hide_index=True,
                    width="stretch",
                )

            for i, label in enumerate(summary["label"].tolist(), start=1):
                with subtabs[i]:
                    xbridge_val = summary.iloc[i - 1]["Indexador XBridge"]
                    if pd.isna(xbridge_val):
                        mask = df_display["Indexador XBridge"].isna()
                    else:
                        mask = df_display["Indexador XBridge"].astype(str).eq(str(xbridge_val))
                    st.dataframe(
                        display_table(df_display[mask].sort_values("OFFER Mercado", ascending=False), DISPLAY_COLUMNS),
                        hide_index=True,
                        width="stretch",
                    )

    with tabs[1]:
        missing_columns = [
            "Ticker",
            "Emissor / Risco",
            "Indexador XBridge",
            "Vencimento XBridge",
            "Isento",
            "Rating",
            "Qtd. BID",
            "Vol. BID",
            "BID Mercado",
            "OFFER Mercado",
            "Qtd. OFFER",
            "Vol. OFFER",
            "Tax. Mín. / Tax. Máx.",
        ]
        st.dataframe(
            display_table(df_missing, missing_columns),
            hide_index=True,
            width="stretch",
        )

    with tabs[2]:
        st.dataframe(
            display_table(df_registered_not_approved, DISPLAY_COLUMNS),
            hide_index=True,
            width="stretch",
        )

    with tabs[3]:
        st.dataframe(
            style_table(
                df[[col for col in ["Status Cadastro", *DISPLAY_COLUMNS] if col in df.columns]],
                date_cols=["Vencimento XBridge", "Data Vencimento"],
                percent_cols=["BID Mercado", "OFFER Mercado"],
                numeric_cols_format_as_float=["Duration", "Vol. BID", "Vol. OFFER"],
                numeric_cols_format_as_int=["Risco", "Qtd. BID", "Qtd. OFFER"],
                highlight_row_by_column="Status Cadastro",
                highlight_row_if_value_equals="Não cadastrado",
                highlight_color="#ffc7ce",
                left_align_cols=["Ticker", "Emissor / Risco", "Alias", "Emissor"],
            ),
            hide_index=True,
            width="stretch",
        )

except Exception as exc:
    st.error(f"Erro ao cruzar dados da XBridge com o Fibery: {exc}")