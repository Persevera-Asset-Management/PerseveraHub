import pandas as pd
import streamlit as st

from utils.auth import check_authentication
from utils.ui import display_logo, load_css
from utils.table import style_table

from services.position_service import get_emissor_column, load_assets, load_issuers


st.set_page_config(
    page_title="XPCV · XBridge | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

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
        use_container_width=True,
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
    df_issuers = st.session_state.df_issuers.copy()
    df_assets = df_assets.merge(df_issuers, left_on='Emissor', right_on='Nome Emissor', how='left')

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
    df["Aprovado"] = df["Status do Emissor"].astype(str).str.casefold().eq("aprovado")
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

    col_total, col_registered, col_approved, col_missing = st.columns(4)
    col_total.metric("Tickers no CSV", total_assets)
    col_registered.metric("Cadastrados no Fibery", total_registered)
    col_approved.metric("Aprovados para negociação", total_approved)
    col_missing.metric("Não cadastrados", total_missing)

    tabs = st.tabs(["Aprovados", "Não cadastrados", "Cadastrados não aprovados", "Base cruzada"])

    with tabs[0]:
        st.subheader("Ativos aprovados para negociação")
        st.dataframe(
            display_table(df_approved, DISPLAY_COLUMNS),
            hide_index=True,
            use_container_width=True,
        )

    with tabs[1]:
        st.subheader("Ativos ainda não cadastrados")
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
            use_container_width=True,
        )

    with tabs[2]:
        st.subheader("Cadastrados, mas fora do status Aprovado")
        st.dataframe(
            display_table(df_registered_not_approved, DISPLAY_COLUMNS),
            hide_index=True,
            use_container_width=True,
        )

    with tabs[3]:
        st.subheader("Base cruzada completa")
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
            use_container_width=True,
        )

except Exception as exc:
    st.error(f"Erro ao cruzar dados da XBridge com o Fibery: {exc}")