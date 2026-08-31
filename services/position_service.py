import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from utils.ui import track_data_load

from persevera_tools.data.providers import ComdinheiroProvider
from persevera_tools.db.fibery import read_fibery
from persevera_tools.db import read_sql
from persevera_tools.fixed_income import calculate_duration


# =============================================================================
# Constantes
# =============================================================================

_CACHE_TTL = 10800  # 3 horas

FILTER_OUT_CARTEIRA_STATES = ["Standby", "Encerrada", "Abandonada"]

ASSET_CLASSES_ORDER = [
    # Caixa e Equivalentes
    'Caixa e Equivalentes',

    # Renda Fixa
    'Renda Fixa Pós-Fixada',
    'Renda Fixa Pré-Fixada',
    'Renda Fixa Atrelada à Inflação',
    
    # Renda Variável
    'Renda Variável',
    
    # Alternativos
    'Retorno Total',
    'Investimentos Alternativos',
    'Ativos Reais',
    'Reserva de Valor',
]

INSTRUMENTOS_RF = [
    'CDB',
    'CRA',
    'CRI',
    'CDCA',
    'LC',
    'LCA',
    'LCD',
    'LCI',
    'LF',
    'LFS',
    'LH',
    'LIG',
    'Títulos Públicos Federais',
    'Debênture',
]

# Instrumentos cujo cronograma de pagamentos está cadastrado em
# 'Inv-Taxonomia/Evento Programado' (alimentado pelas securitizadoras).
# Demais instrumentos de RF não têm eventos e ficam fora do fluxo projetado.
INSTRUMENTOS_EVENTOS_PROGRAMADOS = [
    'CRA',
    'CRI',
    'Debênture',
]

# Instrumentos tipicamente bullet (juros + principal no vencimento).
INSTRUMENTOS_RF_BULLET = {
    'CDB',
    'LC',
    'LCA',
    'LCD',
    'LCI',
    'LF',
    'LFS',
    'LH',
    'LIG',
    'Título Público',    # Por enquanto, não tem duration
}

_POSITIONS_TABLE = "Inv-Asset Allocation/Posição Consolidada"

# Fields lidos de Posição Consolidada. Name (título) substitui Nome Ativo
# da database antiga; o normalize promove Name → Nome Ativo. Taxonomia e
# calendário de dias úteis vêm de cruzamento (Ativos e Dias Úteis).
_POSITIONS_QUERY_FIELDS = [
    "Data Posição", "Portfolio", "Custodiante Acronimo",
    "Name", "Ativo",
    "Quantidade", "Valor Unitário", "Saldo",
    "creation-date",
]

# Schema canônico devolvido por load_positions* (Posição Consolidada ⋉ Ativos).
_POSITIONS_COLUMNS = [
    "Data Posição", "Portfolio", "Custodiante Acronimo",
    "Nome Ativo", "Nome Ativo Completo", "Alias",
    "Classificação do Conjunto", "Classificação do Sub-Conjunto",
    "Classificação Instrumento",
    "Nome Emissor", "Nome Devedor",
    "Quantidade", "Valor Unitário", "Saldo",
    "Indexador",
    "Data Vencimento",
]

_ASSET_TO_POSITION_SOURCES = {
    "Nome Ativo Completo": ("Nome Completo",),
    "Alias": ("Alias",),
    "Classificação do Conjunto": ("Classificação Conjunto", "Classificação do Conjunto"),
    "Classificação do Sub-Conjunto": (
        "Classificação Sub-Conjunto",
        "Classificação do Sub-Conjunto",
    ),
    "Classificação Instrumento": (
        "Classificação Instrumento",
        "Classificação Instrumento-Relation",
    ),
    "Nome Emissor": ("Nome Emissor",),
    "Nome Devedor": ("Nome Devedor",),
    "Indexador": ("Indexador",),
    "_Data Vencimento Ativo": ("Data Vencimento",),
}

_POSITIONS_DEDUP_SUBSET = [
    'Data Posição', 'Portfolio', 'Nome Ativo', 'Custodiante Acronimo', 'Saldo',
]

# Allowlists de `read_fibery(fields=...)`. Cada lista é a união das colunas
# usadas pelos consumidores do loader (views + funções internas).
_ASSETS_FIELDS = [
    "Name",
    "Alias",
    "Nome Completo",
    "Indexador",
    "Data Vencimento",
    "Nome Emissor",
    "Nome Devedor",
    "Identificador do Emissor",
    "Identificador do Devedor",
    "Classificação Instrumento",
    "Classificação Conjunto",
    "Classificação Sub-Conjunto",
]
_ISSUERS_FIELDS = ["Name", "Nome Emissor", "Status do Emissor"]
_TARGET_ALLOCATIONS_BASE_FIELDS = [
    "Name",
    "Política de Investimento",
    "Alocação Target",
    "Target",
]
_TARGET_ALLOCATIONS_LIMIT_FIELDS = ["PL Min", "PL Max"]
_ACCOUNTS_FIELDS = ["Portfolio", "Titularidade Principal", "Custodiante", "Nr Conta"]
_INSTRUMENTS_FGC_FIELDS = ["Name", "Cobertura FGC"]
_BUSINESS_DAYS_FIELDS = ["Data"]
_SCHEDULED_EVENTS_FIELDS = [
    "Ativo",
    "Data do Pagamento",
    "Tipo do Evento",
    "Fonte",
    "Valor Unitário",
]

# Schema devolvido por `load_scheduled_events`.
_SCHEDULED_EVENT_COLUMNS = [
    "Ativo",
    "Data do Pagamento",
    "Tipo do Evento",
    "Fonte",
    "Valor Unitário Evento",
]

# Schema devolvido por `build_cash_flow_schedule`.
CASH_FLOW_SCHEDULE_COLUMNS = [
    "Data do Pagamento",
    "Mês",
    "Nome Ativo",
    "Alias",
    "Classificação Instrumento",
    "Tipo do Evento",
    "Fonte",
    "Quantidade",
    "Valor Unitário Evento",
    "Valor",
]
_PORTFOLIO_INFO_FIELDS = ["Name", "Officer Atual", "Tipo Cliente"]
_CARTEIRAS_ADM_OLD_FIELDS = ["state", "Name", "Data Início Gestão", "Data Fim Gestão"]
_ACTIVE_CARTEIRAS_FIELDS = ["Chave Match"]
_CLIENTES_CARTEIRA_MODELO_FIELDS = [
    "Ativa",
    "Carteira Modelo",
    "Conta",
    "Custodiante",
    "Nr Conta",
    "Percentual do PL",
]
_CONTA_PORTFOLIO_FIELDS = ["Name", "Portfolio Texto"]
_COMPOSICAO_CARTEIRA_FIELDS = ["Ativo", "Peso", "Evento"]
_EVENTO_REBALANCEAMENTO_FIELDS = [
    "Name",
    "Data de Implementação",
    "Carteira Modelo",
]
_PORTFOLIOS_RVQM_COLUMNS = [
    "Portfolio",
    "Conta",
    "Custodiante",
    "Nr Conta",
    "Percentual do PL",
    "Tipo",
]
_EQUITIES_PORTFOLIO_COLUMNS = ["date", "code", "weight", "tipo"]


# =============================================================================
# Funções Utilitárias
# =============================================================================

def get_latest_date_data(
    df: pd.DataFrame,
    level: int | str = 0,
    group_level: int | str | list | None = None,
) -> pd.DataFrame:
    """
    Retorna dados da data mais recente de um DataFrame com MultiIndex.
    
    Args:
        df: DataFrame com MultiIndex onde um dos níveis é a data.
        level: Nível do índice que contém as datas (padrão: 0).
        group_level: Se informado, obtém a data mais recente **por grupo**.
            Pode ser um único nível (int/str) ou lista de níveis.
            Exemplo: group_level='Portfolio' retorna, para cada portfolio,
            as linhas da sua data mais recente.
    
    Returns:
        DataFrame filtrado para a data mais recente (global ou por grupo).
        Retorna o próprio DataFrame (vazio) caso a entrada esteja vazia.
    """
    if df.empty:
        return df

    if group_level is None:
        latest_date = df.index.get_level_values(level=level).max()
        if pd.isna(latest_date):
            return df.iloc[0:0]
        return df.loc[latest_date]

    if not isinstance(group_level, list):
        group_level = [group_level]

    dates = df.index.get_level_values(level=level)
    groups = [df.index.get_level_values(level=g) for g in group_level]

    # Monta um DataFrame auxiliar — necessário porque Series.copy() + atribuição
    # por chave adiciona entradas no índice, não colunas (quebra o groupby).
    temp = pd.DataFrame(
        {f'__grp_{i}__': g for i, g in enumerate(groups)},
        index=df.index,
    )
    temp['__date__'] = dates
    grp_cols = [f'__grp_{i}__' for i in range(len(groups))]

    latest_per_group = temp.groupby(grp_cols, sort=False)['__date__'].transform('max')
    mask = temp['__date__'].to_numpy() == latest_per_group.to_numpy()
    return df.loc[mask]


def _taxonomy_frame_for_positions(df_assets: pd.DataFrame) -> pd.DataFrame:
    """Seleciona e renomeia colunas de Ativos para o schema canônico de posições."""
    if "Name" not in df_assets.columns:
        return pd.DataFrame(columns=["Name"])

    tax = pd.DataFrame({"Name": df_assets["Name"].to_numpy()}, index=df_assets.index)
    for dest, sources in _ASSET_TO_POSITION_SOURCES.items():
        for src in sources:
            if src in df_assets.columns:
                tax[dest] = df_assets[src].to_numpy()
                break
    return tax.drop_duplicates(subset=["Name"])


def _enrich_positions_with_assets(
    df: pd.DataFrame,
    df_assets: pd.DataFrame,
) -> pd.DataFrame:
    """Cruza posições com Inv-Taxonomia/Ativos pelo código do ativo.

    Chave: ``Ativo`` (relação) com fallback em ``Nome Ativo``. Data Vencimento
    vem do cadastro; se a posição ainda trouxer o campo, ele só entra como
    fallback.
    """
    tax = _taxonomy_frame_for_positions(df_assets)
    if "Ativo" in df.columns:
        join_key = df["Ativo"].fillna(df["Nome Ativo"])
    else:
        join_key = df["Nome Ativo"]

    df = df.copy()
    df["_join_key"] = join_key
    df = df.merge(tax, how="left", left_on="_join_key", right_on="Name")

    if "_Data Vencimento Ativo" in df.columns:
        maturity_pos = (
            df["Data Vencimento"]
            if "Data Vencimento" in df.columns
            else pd.Series(pd.NA, index=df.index)
        )
        df["Data Vencimento"] = df["_Data Vencimento Ativo"].fillna(maturity_pos)
        df = df.drop(columns=["_Data Vencimento Ativo"])

    nome = df["Nome Ativo"] if "Nome Ativo" in df.columns else pd.Series(pd.NA, index=df.index)
    if "Ativo" in df.columns:
        nome = nome.fillna(df["Ativo"])
    if "Name" in df.columns:
        nome = nome.fillna(df["Name"])
    df["Nome Ativo"] = nome

    drop_cols = [col for col in ("Ativo", "_join_key", "Name") if col in df.columns]
    return df.drop(columns=drop_cols)


def _ensure_canonical_position_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Garante o schema canônico mesmo quando o cruzamento não preenche colunas."""
    out = df.copy()
    for col in _POSITIONS_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[_POSITIONS_COLUMNS]


def _filter_positions_to_business_days(
    df: pd.DataFrame,
    business_days: pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
    """Mantém apenas posições cuja data está em Ops-Portfolios/Dias Úteis."""
    if business_days is None:
        business_days = load_business_days()
    if business_days.empty:
        return df
    dates = pd.to_datetime(df["Data Posição"]).dt.normalize()
    return df.loc[dates.isin(business_days)]


def _normalize_positions_df(
    df: pd.DataFrame,
    df_assets: pd.DataFrame | None = None,
    business_days: pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
    """Normaliza DataFrame bruto de Posição Consolidada e cruza com a taxonomia."""
    if df.empty:
        return pd.DataFrame(columns=_POSITIONS_COLUMNS)

    df = df.copy()
    for col in _POSITIONS_QUERY_FIELDS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[_POSITIONS_QUERY_FIELDS]
    df["Nome Ativo"] = df["Name"].fillna(df["Ativo"])
    df = df.drop(columns=["Name"])
    df['Data Posição'] = pd.to_datetime(df['Data Posição'])
    df['creation-date'] = pd.to_datetime(df['creation-date'])
    df = _filter_positions_to_business_days(df, business_days)
    df = df.drop_duplicates(subset=_POSITIONS_DEDUP_SUBSET, keep='last')
    df = df.drop(columns=['creation-date'])

    if df_assets is None:
        df_assets = load_assets()
    df = _enrich_positions_with_assets(df, df_assets)
    df = _ensure_canonical_position_columns(df)

    df = df.dropna(subset=['Classificação do Conjunto'])
    df['Classificação do Sub-Conjunto'] = df['Classificação do Sub-Conjunto'].fillna('Sem Classificação')
    return df


# =============================================================================
# Funções de Carregamento de Dados
# =============================================================================

@st.cache_data(ttl=_CACHE_TTL)
def load_portfolio_from_comdinheiro(portfolios: tuple, date_report: str) -> pd.DataFrame:
    """
    Carrega posições de um portfolio do Comdinheiro.

    Args:
        portfolios: Tuple de portfolios.
        date_report: Data de report.

    Returns:
        DataFrame com as posições do portfolio.
    """
    provider = ComdinheiroProvider()
    df = provider.get_data(category='comdinheiro', data_type='portfolio_positions', portfolios=list(portfolios), date_report=date_report)
    track_data_load("portfolio_comdinheiro")
    return df


@st.cache_data(ttl=_CACHE_TTL)
def _load_historical_positions_one(portfolio: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Busca posições históricas de uma única carteira (unidade de cache)."""
    provider = ComdinheiroProvider()
    return provider.get_data(
        category='comdinheiro',
        data_type='portfolio_historical_positions',
        portfolios=[portfolio],
        start_date=start_date,
        end_date=end_date,
    )


def load_historical_positions_from_comdinheiro(portfolios: tuple, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Carrega posições históricas do ComDinheiro.

    Faz fetch por carteira (cache individual) e, com várias carteiras, em paralelo.
    Assim, adicionar uma carteira à seleção não refetcha as que já estão em cache.

    Args:
        portfolios: Tuple de portfolios.
        start_date: Data de início.
        end_date: Data fim.

    Returns:
        DataFrame com as posições históricas do portfolio.
    """
    if not portfolios:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    max_workers = min(4, len(portfolios))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_load_historical_positions_one, portfolio, start_date, end_date): portfolio
            for portfolio in portfolios
        }
        for future in as_completed(futures):
            chunk = future.result()
            if chunk is not None and not chunk.empty:
                frames.append(chunk)

    track_data_load("portfolio_historical_positions_comdinheiro")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

_COMDINHEIRO_PORTFOLIO_COLUMN_MAP = {
    'date': 'Data',
    'carteira': 'Carteira',
    'ativo': 'Ativo',
    'descricao': 'Descrição',
    'quantidade': 'Quantidade',
    'preco_unitario': 'Preço Unitário',
    'saldo_bruto': 'Saldo Bruto',
    'instituicao_financeira': 'Custodiante',
    'tipo_ativo': 'Tipo de Ativo',
    'ticker': 'Ticker',
}

_COMDINHEIRO_TICKER_STRIP_SUBSTRINGS = [
    '.pu_med',
    '.pu_ref',
    '.pu_anb',
    '.lasto',
    'CETIP_',
    'COE_',
    '_unica',
    '_subordinadaJunior1',
    '_senior1',
    '_subclasseA',
    '_classeA',
    '_ClasseA',
    '_classeB',
    '_classeC',
    '_classe2',
    'DEB:',
]

# Prefixo de ativos offshore no Comdinheiro (ex.: US:DBMF, us:FWB:US02079KAD90).
_COMDINHEIRO_OFFSHORE_TICKER_PREFIX = 'US:'


def _normalize_comdinheiro_tickers(tickers: pd.Series) -> pd.Series:
    """Remove sufixos de precificação/série e normaliza tickers offshore do Comdinheiro."""
    strip_pattern = r'|'.join(_COMDINHEIRO_TICKER_STRIP_SUBSTRINGS)
    out = tickers.str.replace(strip_pattern, '', regex=True)
    out = out.str.replace(r'_@.*$', '', regex=True)
    offshore = out.str.upper().str.startswith(_COMDINHEIRO_OFFSHORE_TICKER_PREFIX)
    out = out.where(~offshore, out.str.split(':').str[-1])
    return out


def prepare_comdinheiro_portfolio_positions_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renomeia colunas de posições do Comdinheiro e normaliza `Ticker` para match com cadastro.

    Args:
        df: DataFrame retornado por `load_portfolio_from_comdinheiro` (colunas em snake_case).

    Returns:
        Cópia com nomes amigáveis e sufixos de precificação/série removidos do ticker.
    """
    out = df.rename(columns=_COMDINHEIRO_PORTFOLIO_COLUMN_MAP).copy()
    out['Ticker'] = _normalize_comdinheiro_tickers(out['Ticker'])
    return out


def prepare_comdinheiro_historical_positions_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara posições históricas do ComDinheiro (sem coluna `ticker` nativa).

    O endpoint histórico retorna `date`, `carteira`, `ativo`, `descricao`, `saldo_bruto`.
    Usa `ativo` como base do ticker e aplica a mesma normalização do snapshot.

    Args:
        df: DataFrame retornado por `load_historical_positions_from_comdinheiro`.

    Returns:
        DataFrame com colunas amigáveis e `Ticker` normalizado.
    """
    rename_map = {
        col: _COMDINHEIRO_PORTFOLIO_COLUMN_MAP[col]
        for col in df.columns
        if col in _COMDINHEIRO_PORTFOLIO_COLUMN_MAP
    }
    out = df.rename(columns=rename_map).copy()
    if 'Data' in out.columns:
        out['Data'] = pd.to_datetime(out['Data'])
    ticker_source = out['Ticker'] if 'Ticker' in out.columns else out['Ativo']
    out['Ticker'] = _normalize_comdinheiro_tickers(ticker_source.astype(str))
    return out


@st.cache_data(ttl=_CACHE_TTL)
def load_assets(
    instrumentos: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """
    Carrega ativos do Fibery.

    Args:
        instrumentos: Se informado, filtra por Classificação Instrumento no Fibery
            (ex: ``("Ação", "BDR")``). ``None`` retorna todos os ativos.

    Returns:
        DataFrame com os ativos.
    """
    read_kwargs: dict = {
        "table_name": "Inv-Taxonomia/Ativos",
        "include_fibery_fields": False,
        "fields": _ASSETS_FIELDS,
    }
    if instrumentos:
        read_kwargs["where_filter"] = [
            "q/in",
            ["Inv-Taxonomia/Classificação Instrumento", "Inv-Taxonomia/Name"],
            "$instrumentos",
        ]
        read_kwargs["params"] = {"$instrumentos": list(instrumentos)}

    df = read_fibery(**read_kwargs)
    df = df.drop_duplicates(subset=["Name"])
    track_data_load("assets")
    return df


@st.cache_data(ttl=_CACHE_TTL)
def load_business_days() -> pd.DatetimeIndex:
    """Carrega o calendário de dias úteis (Brasil) do Fibery."""
    df = read_fibery(
        table_name="Ops-Portfolios/Dias Úteis",
        include_fibery_fields=False,
        fields=_BUSINESS_DAYS_FIELDS,
    )
    dates = pd.to_datetime(df["Data"], errors="coerce").dropna().dt.normalize()
    track_data_load("business_days")
    return pd.DatetimeIndex(dates.unique()).sort_values()


@st.cache_data(ttl=_CACHE_TTL)
def load_issuers() -> pd.DataFrame:
    """
    Carrega emissores e devedores do Fibery.

    Returns:
        DataFrame com os emissores e devedores.
    """
    
    df = read_fibery(
        table_name="Inv-Taxonomia/Emissores e Devedores",
        include_fibery_fields=False,
        fields=_ISSUERS_FIELDS,
    )

    df['Status do Emissor'] = df['Status do Emissor'].fillna('Sem Classificação')
    df = df[["Name", "Nome Emissor", "Status do Emissor"]]
    track_data_load("issuers")
    return df


@st.cache_data(ttl=_CACHE_TTL)
def load_positions(days_lookback: int = 4) -> pd.DataFrame:
    """
    Carrega posições do Fibery e cruza com Inv-Taxonomia/Ativos.

    Args:
        days_lookback: Número de dias para buscar posições (padrão: 4).

    Returns:
        DataFrame no schema canônico de posições.
    """
    data_recente = (datetime.now() - timedelta(days=days_lookback)).strftime('%Y-%m-%dT00:00:00Z')
    
    df = read_fibery(
        table_name=_POSITIONS_TABLE,
        where_filter=[
            "q/and",
            [">=", ["Inv-Asset Allocation/Data Posição"], "$dataRecente"],
            ["q/not-equals-ignoring-case?", ["Inv-Asset Allocation/Fonte"], "$fonteExcluida"],
        ],
        params={"$dataRecente": data_recente, "$fonteExcluida": "ProventosXP"},
        include_fibery_fields=False,
        fields=_POSITIONS_QUERY_FIELDS,
    )

    track_data_load("positions")
    return _normalize_positions_df(df, load_assets(), load_business_days())


@st.cache_data(ttl=_CACHE_TTL)
def load_positions_for_portfolio(portfolio: str) -> pd.DataFrame:
    """
    Carrega todo o histórico disponível de posições para um único portfolio
    e cruza com Inv-Taxonomia/Ativos.

    Args:
        portfolio: Código do portfolio (ex: 'ABCD').

    Returns:
        DataFrame no schema canônico de posições.
    """
    df = read_fibery(
        table_name=_POSITIONS_TABLE,
        where_filter=["=", ["Inv-Asset Allocation/Portfolio", "Ops-Portfolios/Name"], "$portfolio"],
        params={"$portfolio": portfolio},
        include_fibery_fields=False,
        fields=_POSITIONS_QUERY_FIELDS,
    )

    track_data_load("positions_portfolio")
    return _normalize_positions_df(df, load_assets(), load_business_days())


@st.cache_data(ttl=_CACHE_TTL)
def load_target_allocations(include_limits: bool = False) -> pd.DataFrame:
    """
    Carrega alocações target do Fibery.
    
    Args:
        include_limits: Se True, inclui colunas 'PL Min' e 'PL Max'.
    
    Returns:
        DataFrame com as alocações target indexado por Portfolio, Data e Name.
    """
    fields = list(_TARGET_ALLOCATIONS_BASE_FIELDS)
    if include_limits:
        fields.extend(_TARGET_ALLOCATIONS_LIMIT_FIELDS)

    df = read_fibery(
        table_name="Ops-Portfolios/Parâmetro de PctPL Polinv",
        include_fibery_fields=False,
        fields=fields,
    )
    
    source = df["Política de Investimento"].fillna(df["Alocação Target"])
    df["Portfolio"] = source.str.split("_").str[0]
    df["Tipo Documento"] = source.str.split("_").str[1]
    df["Data Documento"] = pd.to_datetime(source.str[-10:])
    
    if include_limits:
        columns = ["Portfolio", "Tipo Documento", "Data Documento", "Name", "PL Min", "PL Max", "Target"]
        agg_dict = {
            'PL Min': ('PL Min', 'mean'),
            'PL Max': ('PL Max', 'mean'),
            'Target': ('Target', 'mean')
        }
    else:
        columns = ["Portfolio", "Tipo Documento", "Data Documento", "Name", "Target"]
        agg_dict = {
            'Target': ('Target', 'mean')
        }
    
    df = df[columns]
    
    df = df.groupby(['Portfolio', pd.Grouper(key='Data Documento', freq='D'), 'Name']).agg(**agg_dict)
    
    return df


@st.cache_data(ttl=_CACHE_TTL)
def load_accounts() -> pd.DataFrame:
    """
    Carrega contas do Fibery (apenas contas sob gestão).
    
    Returns:
        DataFrame com as contas e informações de titularidade.
    """
    df = read_fibery(
        table_name="Ops-InstFin/Conta",
        include_fibery_fields=False,
        fields=_ACCOUNTS_FIELDS,
        where_filter=["=", ["Ops-InstFin/Status Habilitação", "enum/name"], "$status"],
        params={"$status": "Sob Gestão"},
    )
    df = df[["Portfolio", "Titularidade Principal", "Custodiante", "Nr Conta"]]
    df = df.dropna(subset=["Portfolio"])
    df["Nome Completo"] = df["Titularidade Principal"].str.split("|").str[1].str.strip()
    return df


@st.cache_data(ttl=_CACHE_TTL)
def load_instruments_fgc() -> list:
    """
    Carrega lista de instrumentos com cobertura do FGC.
    
    Returns:
        Lista de nomes de instrumentos cobertos pelo FGC.
    """
    df = read_fibery(
        table_name="Inv-Taxonomia/Classificação Instrumento",
        include_fibery_fields=False,
        fields=_INSTRUMENTS_FGC_FIELDS,
    )
    df = df[["Name", "Cobertura FGC"]]
    instruments_list = df[df["Cobertura FGC"]]["Name"].tolist()
    return instruments_list


@st.cache_data(ttl=_CACHE_TTL)
def load_scheduled_events(start_date: Optional[str] = None) -> pd.DataFrame:
    """
    Carrega o cronograma de eventos programados (juros, amortizações) do Fibery.

    O cadastro cobre apenas os instrumentos de ``INSTRUMENTOS_EVENTOS_PROGRAMADOS``
    e guarda o valor **por unidade** do ativo, não o valor a receber.

    Args:
        start_date: Data mínima de pagamento no formato ``YYYY-MM-DD``. Quando
            informada, filtra no servidor. ``None`` traz todo o histórico.

    Returns:
        DataFrame com Ativo, Data do Pagamento, Tipo do Evento, Fonte e
        Valor Unitário Evento (renomeado para não colidir com o preço unitário
        das posições).
    """
    read_kwargs: dict = {
        "table_name": "Inv-Taxonomia/Evento Programado",
        "include_fibery_fields": False,
        "fields": _SCHEDULED_EVENTS_FIELDS,
    }
    if start_date:
        read_kwargs["where_filter"] = [
            ">=", ["Inv-Taxonomia/Data do Pagamento"], "$startDate",
        ]
        read_kwargs["params"] = {"$startDate": start_date}

    df = read_fibery(**read_kwargs)
    track_data_load("scheduled_events")

    if df.empty:
        return pd.DataFrame(columns=_SCHEDULED_EVENT_COLUMNS)

    df = df.rename(columns={"Valor Unitário": "Valor Unitário Evento"})
    for column in _SCHEDULED_EVENT_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    df["Data do Pagamento"] = pd.to_datetime(df["Data do Pagamento"], errors="coerce")
    df["Valor Unitário Evento"] = pd.to_numeric(
        df["Valor Unitário Evento"], errors="coerce"
    )
    df = df.dropna(subset=["Ativo", "Data do Pagamento", "Valor Unitário Evento"])
    return df[_SCHEDULED_EVENT_COLUMNS].reset_index(drop=True)


@st.cache_data(ttl=_CACHE_TTL)
def load_portfolio_info() -> pd.DataFrame:
    """
    Carrega informações dos portfolios do Fibery.

    Returns:
        DataFrame com os portfolios.
    """
    
    df = read_fibery(
        table_name="Ops-Portfolios/Portfolio",
        include_fibery_fields=False,
        fields=_PORTFOLIO_INFO_FIELDS,
    )

    track_data_load("portfolio_info")
    return df


@st.cache_data(ttl=_CACHE_TTL)
def load_active_carteiras_adm_old() -> dict:
    """
    Carrega carteiras administradas ativas do Fibery.

    Exclui estados Standby, Encerrada e Abandonada, exige data de início de
    gestão e descarta carteiras com data de fim de gestão preenchida.

    Returns:
        Dict indexado por código da carteira com metadados de gestão.
    """
    df = read_fibery(
        table_name="Estr-CartAdm/Carteira Administrada",
        include_fibery_fields=False,
        fields=_CARTEIRAS_ADM_OLD_FIELDS,
    )
    df = df[~np.isin(df["state"], FILTER_OUT_CARTEIRA_STATES)]
    df = df[["Name", "Data Início Gestão", "Data Fim Gestão"]]
    df = df.dropna(subset=["Data Início Gestão"])
    df = df[df["Data Fim Gestão"].isna()]
    df.drop(columns=["Data Fim Gestão"], inplace=True)
    df = df.rename(columns={"Name": "Código", "Data Início Gestão": "Data Início Gestão"})
    df["Código"] = df["Código"].str.split("-").str[0]
    df.set_index("Código", inplace=True)

    track_data_load("active_carteiras_adm")
    return df.to_dict("index")


@st.cache_data(ttl=_CACHE_TTL)
def load_active_carteiras_adm() -> list[str]:
    """
    Carrega códigos de carteiras administradas ativas do Fibery.

    Filtra mandatos ativos na tabela Codinome Relatório e retorna as chaves
    de match ordenadas alfabeticamente.

    Returns:
        Lista de códigos de carteira (Chave Match).
    """
    df = read_fibery(
        table_name="Inv-Asset Allocation/Série de Relatório",
        where_filter=["=", ["Inv-Asset Allocation/Mandato Ativo"], True],
        include_fibery_fields=False,
        fields=_ACTIVE_CARTEIRAS_FIELDS,
    )

    df.dropna(subset=["Chave Match"], inplace=True)

    track_data_load("active_carteiras_adm")
    return sorted(df["Chave Match"].tolist())


def active_carteira_codes() -> set[str]:
    """Retorna os códigos das carteiras administradas ativas."""
    return set(load_active_carteiras_adm())


def _normalize_strategy_name(series: pd.Series) -> pd.Series:
    """Normaliza o Name da Carteira Modelo (ex.: RVQM, MAGO) para join/filtro."""
    return (
        series.astype("string")
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
    )


@st.cache_data(ttl=_CACHE_TTL)
def load_portfolios_rvqm() -> pd.DataFrame:
    """
    Carrega portfólios com carteira-modelo de equities ativa no Fibery.

    Lê ``Cliente com Carteira Modelo`` e resolve o código do portfolio via
    ``Ops-InstFin/Conta`` (a tabela nova não tem o campo fórmula Portfolio).

    Returns:
        DataFrame com Portfolio, conta, custodiante e Tipo (Name da Carteira Modelo).
    """
    empty = pd.DataFrame(columns=_PORTFOLIOS_RVQM_COLUMNS)
    clientes = read_fibery(
        table_name="Inv-Asset Allocation/Cliente com Carteira Modelo",
        include_fibery_fields=False,
        fields=_CLIENTES_CARTEIRA_MODELO_FIELDS,
    )
    if clientes.empty or "Ativa" not in clientes.columns:
        return empty

    clientes = clientes.loc[clientes["Ativa"].fillna(False).astype(bool)].copy()
    if clientes.empty:
        return empty

    contas = read_fibery(
        table_name="Ops-InstFin/Conta",
        include_fibery_fields=False,
        fields=_CONTA_PORTFOLIO_FIELDS,
    )
    if contas.empty:
        return empty

    contas = contas.rename(columns={"Name": "Conta", "Portfolio Texto": "Portfolio"})
    df = clientes.merge(contas[["Conta", "Portfolio"]], on="Conta", how="left")
    df = df.rename(columns={"Carteira Modelo": "Tipo"})
    df["Tipo"] = _normalize_strategy_name(df["Tipo"])
    df = df.dropna(subset=["Portfolio"])
    missing = [col for col in _PORTFOLIOS_RVQM_COLUMNS if col not in df.columns]
    if missing:
        return empty
    return df[_PORTFOLIOS_RVQM_COLUMNS].copy()


@st.cache_data(ttl=_CACHE_TTL)
def load_equities_portfolio(tipo: str | None = None) -> pd.DataFrame:
    """
    Carrega a composição histórica das carteiras-modelo de equities do Fibery.

    Combina ``Composição de Carteira`` (ativo × peso) com ``Evento de
    Rebalanceamento`` (data de implementação e Carteira Modelo).

    Args:
        tipo: Se informado (ex.: ``"RVQM"`` ou ``"MAGO"``), filtra pela
            Carteira Modelo. ``None`` retorna todas as composições, com a
            coluna ``tipo``.

    Returns:
        DataFrame com date, code, weight e tipo.
    """
    empty = pd.DataFrame(columns=_EQUITIES_PORTFOLIO_COLUMNS)
    composicao = read_fibery(
        table_name="Inv-Asset Allocation/Composição de Carteira",
        include_fibery_fields=False,
        fields=_COMPOSICAO_CARTEIRA_FIELDS,
    )
    eventos = read_fibery(
        table_name="Inv-Asset Allocation/Evento de Rebalanceamento",
        include_fibery_fields=False,
        fields=_EVENTO_REBALANCEAMENTO_FIELDS,
    )
    if composicao.empty or eventos.empty:
        return empty

    eventos = eventos.rename(
        columns={
            "Name": "Evento",
            "Data de Implementação": "date",
            "Carteira Modelo": "tipo",
        }
    )
    df = composicao.merge(eventos[["Evento", "date", "tipo"]], on="Evento", how="inner")
    if df.empty:
        return empty

    df = df.rename(columns={"Ativo": "code", "Peso": "weight"})
    df["date"] = pd.to_datetime(df["date"])
    df["tipo"] = _normalize_strategy_name(df["tipo"])
    df = df.dropna(subset=["date", "code", "weight", "tipo"])
    df = df.drop_duplicates(subset=["date", "code", "tipo"], keep="last")
    if tipo is not None:
        df = df[df["tipo"] == str(tipo).strip()].copy()
    return df[_EQUITIES_PORTFOLIO_COLUMNS].copy()


def resolve_portfolio_strategy(
    portfolio: str,
    portfolios_rvqm: pd.DataFrame | None = None,
) -> str:
    """
    Infere a carteira-modelo aderida pelo portfolio/cliente.

    Raises:
        ValueError: Se o portfolio não existir ou não tiver Carteira Modelo preenchida.
    """
    clients = portfolios_rvqm if portfolios_rvqm is not None else load_portfolios_rvqm()
    row = clients.loc[clients["Portfolio"] == portfolio]
    if row.empty:
        raise ValueError(f"Portfolio '{portfolio}' não encontrado na tabela de clientes.")
    tipo = row["Tipo"].iloc[0]
    if pd.isna(tipo) or not str(tipo).strip() or str(tipo).strip().lower() in {"nan", "none", "<na>"}:
        raise ValueError(
            f"Portfolio '{portfolio}' sem Carteira Modelo definida no Fibery."
        )
    return str(tipo).strip()


@st.cache_data(ttl=_CACHE_TTL)
def load_indicator_catalog() -> list[str]:
    try:
        query = """
        SELECT DISTINCT code
        FROM indicadores
        ORDER BY code
        """
        result = read_sql(query)
        if isinstance(result, pd.DataFrame):
            col = "code" if "code" in result.columns else result.columns[0]
            return result[col].dropna().astype(str).tolist()
        return [str(c) for c in result] if result else []
    except Exception as e:
        st.error(f"Erro ao carregar códigos das séries: {str(e)}")
        return []


@st.cache_data(ttl=_CACHE_TTL)
def load_funds_catalog() -> pd.DataFrame:
    try:
        df = load_assets(("Fundo de Investimento", "Previdência Privada"))
        cols = [c for c in ["Name", "Nome Completo"] if c in df.columns]
        if not cols:
            return pd.DataFrame(columns=["Name", "Nome Completo"])
        return df[cols].drop_duplicates().sort_values(cols[0]).reset_index(drop=True)
    except Exception as e:
        st.error(f"Erro ao carregar catálogo de fundos: {e}")
        return pd.DataFrame(columns=["Name", "Nome Completo"])


# =============================================================================
# Funções de Agregação de Dados
# =============================================================================

def aggregate_positions_by_asset(
    df: pd.DataFrame,
    group_columns: Optional[list] = None
) -> pd.DataFrame:
    """
    Agrega posições por ativo.
    
    Args:
        df: DataFrame com posições.
        group_columns: Colunas adicionais para agrupamento além de 'Data Posição'.
    
    Returns:
        DataFrame agregado com Quantidade, Valor Unitário e Saldo.
    """
    if group_columns is None:
        group_columns = ['Nome Ativo', 'Nome Ativo Completo', 'Classificação do Conjunto']
    
    return df.groupby(
        [pd.Grouper(key='Data Posição', freq='D')] + group_columns
    ).agg(**{
        'Quantidade': ('Quantidade', 'sum'),
        'Valor Unitário': ('Valor Unitário', 'mean'),
        'Saldo': ('Saldo', 'sum')
    })


def aggregate_positions_by_classification(
    df: pd.DataFrame,
    classification_column: str = 'Classificação do Conjunto'
) -> pd.DataFrame:
    """
    Agrega posições por classificação.
    
    Args:
        df: DataFrame com posições.
        classification_column: Coluna de classificação para agrupamento.
    
    Returns:
        DataFrame agregado com Saldo por classificação.
    """
    return df.groupby(
        [pd.Grouper(key='Data Posição', freq='D'), classification_column]
    ).agg(**{'Saldo': ('Saldo', 'sum')})


def get_emissor_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona colunas de emissor preenchendo Nome Devedor ou Nome Emissor.

    Quando disponíveis, também preenche ``Identificador do Emissor Geral``
    a partir de ``Identificador do Devedor`` ou ``Identificador do Emissor``
    (presentes no cadastro de ativos, mas não nas posições).

    Args:
        df: DataFrame com colunas 'Nome Devedor' e 'Nome Emissor'.

    Returns:
        DataFrame com colunas 'Emissor', 'Emissor Geral' e, se aplicável,
        'Identificador do Emissor Geral'.
    """
    df = df.copy()
    df['Emissor Geral'] = df['Nome Devedor'].fillna(df['Nome Emissor'])
    df['Emissor'] = df['Emissor Geral']

    if 'Identificador do Devedor' in df.columns or 'Identificador do Emissor' in df.columns:
        devedor_id = (
            df['Identificador do Devedor']
            if 'Identificador do Devedor' in df.columns
            else pd.Series(pd.NA, index=df.index)
        )
        emissor_id = (
            df['Identificador do Emissor']
            if 'Identificador do Emissor' in df.columns
            else pd.Series(pd.NA, index=df.index)
        )
        df['Identificador do Emissor Geral'] = devedor_id.fillna(emissor_id)

    return df


def _map_indexador_to_indice(indexador) -> str:
    """Mapeia Indexador da posição para a convenção de day-count da duration."""
    if pd.isna(indexador):
        return 'DI'
    text = str(indexador).strip().upper()
    if not text:
        return 'DI'
    if 'DI' in text or 'CDI' in text:
        return 'DI'
    return 'IPCA'


def _coupon_rate_for_instrumento(instrumento) -> float | None:
    """
    Define cupom para o fallback analítico.

    Bullets (CDB/LCI/...) usam coupon_rate=0 → duration = prazo até o vencimento.
    Demais instrumentos deixam None para ANBIMA / YTM do banco.
    """
    if pd.isna(instrumento):
        return None
    if str(instrumento).strip() in INSTRUMENTOS_RF_BULLET:
        return 0.0
    return None


@st.cache_data(ttl=_CACHE_TTL)
def _calculate_durations_cached(
    codes: tuple[str, ...],
    maturity_dates: tuple[str, ...],
    indices: tuple[str, ...],
    coupon_rates: tuple[float | None, ...],
    settlement_date: str | None,
) -> pd.DataFrame:
    """Cacheia o cálculo em lote de duration por código.

    Duration ANBIMA vem em dias úteis; convertemos para anos (/252) para
    ficar na mesma unidade do fallback analítico (``calculated``).
    """
    maturity_by_code = dict(zip(codes, maturity_dates))
    indice_by_code = dict(zip(codes, indices))
    coupon_by_code = {
        code: rate for code, rate in zip(codes, coupon_rates) if rate is not None
    }

    result = calculate_duration(
        list(codes),
        maturity_date=maturity_by_code,
        settlement_date=settlement_date,
        coupon_rate=coupon_by_code or None,
        indice=indice_by_code,
        use_anbima=True,
    )
    if isinstance(result, dict):
        result = pd.DataFrame([result], index=[codes[0]])

    anbima_mask = result['source'] == 'anbima'
    if anbima_mask.any():
        result.loc[anbima_mask, 'macaulay_duration'] = (
            result.loc[anbima_mask, 'macaulay_duration'] / 252.0
        )
    return result


def enrich_dataframe_with_duration(
    df: pd.DataFrame,
    *,
    code_col: str = 'Nome Ativo',
    maturity_col: str = 'Data Vencimento',
    indexador_col: str = 'Indexador',
    instrumento_col: str = 'Classificação Instrumento',
    settlement_date=None,
) -> pd.DataFrame:
    """
    Acrescenta duration (Macaulay) às linhas de renda fixa do DataFrame.

    Calcula uma vez por ``Nome Ativo`` (código) e faz merge de volta. Instrumentos
    fora de ``INSTRUMENTOS_RF`` ou sem vencimento ficam com NaN.

    Colunas adicionadas:
        - Duration: Macaulay duration em anos (ANBIMA convertida de DU/252)
        - Duration Fonte: ``anbima``, ``calculated`` ou ``no_data``
        - Years to Maturity: prazo residual usado no fallback (quando disponível)
    """
    out = df.copy()
    out['Duration'] = np.nan
    out['Duration Fonte'] = pd.NA
    out['Years to Maturity'] = np.nan

    if out.empty or code_col not in out.columns or maturity_col not in out.columns:
        return out

    mask_rf = out[instrumento_col].isin(INSTRUMENTOS_RF) if instrumento_col in out.columns else True
    mask_maturity = out[maturity_col].notna()
    mask_code = out[code_col].notna() & (out[code_col].astype(str).str.strip() != '')
    eligible = out.loc[mask_rf & mask_maturity & mask_code].copy()
    if eligible.empty:
        return out

    eligible['_code'] = eligible[code_col].astype(str).str.strip()
    eligible['_maturity'] = pd.to_datetime(eligible[maturity_col], errors='coerce')
    eligible = eligible[eligible['_maturity'].notna()]
    if eligible.empty:
        return out

    if indexador_col in eligible.columns:
        eligible['_indice'] = eligible[indexador_col].map(_map_indexador_to_indice)
    else:
        eligible['_indice'] = 'DI'

    if instrumento_col in eligible.columns:
        eligible['_coupon'] = eligible[instrumento_col].map(_coupon_rate_for_instrumento)
    else:
        eligible['_coupon'] = None

    unique = (
        eligible
        .sort_values('_maturity')
        .drop_duplicates(subset=['_code'], keep='first')
    )

    settlement = None
    if settlement_date is not None and pd.notna(settlement_date):
        settlement = pd.Timestamp(settlement_date).strftime('%Y-%m-%d')

    try:
        durations = _calculate_durations_cached(
            tuple(unique['_code'].tolist()),
            tuple(unique['_maturity'].dt.strftime('%Y-%m-%d').tolist()),
            tuple(unique['_indice'].tolist()),
            tuple(None if pd.isna(v) else float(v) for v in unique['_coupon'].tolist()),
            settlement,
        )
    except Exception:
        return out

    duration_map = durations['macaulay_duration'] if 'macaulay_duration' in durations.columns else pd.Series(dtype=float)
    source_map = durations['source'] if 'source' in durations.columns else pd.Series(dtype=object)
    ytm_map = (
        durations['years_to_maturity']
        if 'years_to_maturity' in durations.columns
        else pd.Series(dtype=float)
    )

    codes = out[code_col].astype(str).str.strip()
    out['Duration'] = codes.map(duration_map)
    out['Duration Fonte'] = codes.map(source_map)
    out['Years to Maturity'] = codes.map(ytm_map)
    # Não atribuir duration a não-RF (map por código poderia contaminar se houvesse colisão).
    if instrumento_col in out.columns:
        non_rf = ~out[instrumento_col].isin(INSTRUMENTOS_RF)
        out.loc[non_rf, 'Duration'] = np.nan
        out.loc[non_rf, 'Duration Fonte'] = pd.NA
        out.loc[non_rf, 'Years to Maturity'] = np.nan
    return out


def weighted_average_duration(
    df: pd.DataFrame,
    *,
    duration_col: str = 'Duration',
    weight_col: str = 'Saldo',
) -> float | None:
    """Duration média ponderada pelo saldo; ignora linhas sem duration válida."""
    if df.empty or duration_col not in df.columns or weight_col not in df.columns:
        return None
    valid = df[df[duration_col].notna() & df[weight_col].notna()].copy()
    if valid.empty:
        return None
    weights = valid[weight_col].astype(float)
    total = weights.sum()
    if total <= 0:
        return None
    return float((valid[duration_col].astype(float) * weights).sum() / total)


RF_DURATION_CATEGORIES = (
    'Renda Fixa Pós-Fixada',
    'Renda Fixa Pré-Fixada',
    'Renda Fixa Atrelada à Inflação',
)

RF_DURATION_CATEGORY_LABELS = {
    'Renda Fixa Pós-Fixada': 'Pós-Fixada',
    'Renda Fixa Pré-Fixada': 'Pré-Fixada',
    'Renda Fixa Atrelada à Inflação': 'Inflação',
}


def weighted_average_duration_by_category(
    df: pd.DataFrame,
    *,
    category_col: str = 'Classificação do Conjunto',
    duration_col: str = 'Duration',
    weight_col: str = 'Saldo',
    categories: tuple[str, ...] = RF_DURATION_CATEGORIES,
) -> pd.Series:
    """
    Duration média ponderada por categoria de RF.

    Returns:
        Series indexada pelas categorias (na ordem de ``categories``), com
        ``None``/NaN quando a categoria não tem duration válida.
    """
    result = pd.Series(index=list(categories), dtype=float)
    if df.empty or category_col not in df.columns:
        return result

    for category in categories:
        subset = df[df[category_col] == category]
        result[category] = weighted_average_duration(
            subset,
            duration_col=duration_col,
            weight_col=weight_col,
        )
    return result


# =============================================================================
# Fluxo de Caixa (Eventos Programados)
# =============================================================================

def _latest_positions_by_asset(df_positions: pd.DataFrame) -> pd.DataFrame:
    """
    Consolida quantidade e saldo por ativo na data de posição mais recente.

    Soma as linhas do mesmo ativo em custodiantes/carteiras diferentes, já que
    o fluxo a receber é o total do recorte selecionado.
    """
    columns = ['Nome Ativo', 'Alias', 'Classificação Instrumento', 'Quantidade', 'Saldo']
    if df_positions.empty:
        return pd.DataFrame(columns=columns)

    latest_date = df_positions['Data Posição'].max()
    df_latest = df_positions[df_positions['Data Posição'] == latest_date]

    return (
        df_latest
        .groupby(['Nome Ativo', 'Alias', 'Classificação Instrumento'], dropna=False)
        .agg(**{
            'Quantidade': ('Quantidade', 'sum'),
            'Saldo': ('Saldo', 'sum'),
        })
        .reset_index()
    )


def _cash_flow_window(reference_date, horizon_months: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    """
    Janela ``[início, fim)`` do fluxo projetado.

    O fim é o primeiro dia do mês após ``horizon_months`` meses, de modo que o
    último mês do horizonte apareça completo no gráfico (o mês corrente entra
    parcial, apenas com o que ainda está por vir).
    """
    start = pd.Timestamp(reference_date or datetime.now()).normalize()
    end = (start.to_period('M') + horizon_months).to_timestamp()
    return start, end


def build_cash_flow_schedule(
    df_positions: pd.DataFrame,
    df_events: pd.DataFrame,
    *,
    reference_date=None,
    horizon_months: int = 12,
) -> pd.DataFrame:
    """
    Projeta os recebimentos futuros das posições a partir dos eventos programados.

    O cadastro guarda o valor por unidade do ativo, então o valor a receber é
    ``Quantidade`` da posição × ``Valor Unitário Evento``. Posições sem
    quantidade (comum em carteiras externas) não geram fluxo e ficam de fora;
    use ``scheduled_events_coverage`` para saber o que foi ignorado.

    Args:
        df_positions: Posições normalizadas (usa a data mais recente).
        df_events: Saída de ``load_scheduled_events``.
        reference_date: Início da projeção (padrão: hoje).
        horizon_months: Número de meses à frente (padrão: 12).

    Returns:
        DataFrame com uma linha por evento e ativo, ordenado por data de
        pagamento, no schema ``CASH_FLOW_SCHEDULE_COLUMNS``.
    """
    empty = pd.DataFrame(columns=CASH_FLOW_SCHEDULE_COLUMNS)
    if df_positions.empty or df_events.empty:
        return empty

    df_assets = _latest_positions_by_asset(df_positions)
    # Máscara explícita: com dtypes nullable, `NA > 0` vira NA e o filtro
    # passa a depender de como o pandas trata NA em máscara booleana.
    quantidade = pd.to_numeric(df_assets['Quantidade'], errors='coerce').fillna(0)
    df_assets = df_assets[quantidade > 0]
    if df_assets.empty:
        return empty

    start, end = _cash_flow_window(reference_date, horizon_months)

    df = df_assets.merge(
        df_events,
        left_on='Nome Ativo',
        right_on='Ativo',
        how='inner',
    )
    df = df[(df['Data do Pagamento'] >= start) & (df['Data do Pagamento'] < end)]
    if df.empty:
        return empty

    df['Valor'] = df['Quantidade'] * df['Valor Unitário Evento']
    df['Mês'] = df['Data do Pagamento'].dt.to_period('M').dt.to_timestamp()
    df = df.sort_values(['Data do Pagamento', 'Nome Ativo', 'Tipo do Evento'])
    return df[CASH_FLOW_SCHEDULE_COLUMNS].reset_index(drop=True)


def aggregate_cash_flow_by_month(
    df_schedule: pd.DataFrame,
    *,
    group_by: str = 'Tipo do Evento',
) -> pd.DataFrame:
    """
    Soma o fluxo por mês, com uma coluna por categoria de ``group_by``.

    Returns:
        DataFrame largo (pronto para gráfico de barras empilhadas) com 'Mês'
        formatado como ``mm/aaaa`` e já ordenado cronologicamente.
    """
    if df_schedule.empty:
        return pd.DataFrame()

    pivot = (
        df_schedule
        .groupby(['Mês', group_by], dropna=False)['Valor']
        .sum()
        .unstack(level=group_by)
        .fillna(0)
        .sort_index()
    )
    out = pivot.reset_index()
    out['Mês'] = out['Mês'].dt.strftime('%m/%Y')
    return out


def scheduled_events_coverage(
    df_positions: pd.DataFrame,
    df_events: pd.DataFrame,
    *,
    reference_date=None,
    horizon_months: int = 12,
    instrumentos: Optional[list] = None,
) -> pd.DataFrame:
    """
    Diagnostica a cobertura do cronograma nas posições que deveriam ter eventos.

    Considera apenas os instrumentos de ``INSTRUMENTOS_EVENTOS_PROGRAMADOS``
    (ou ``instrumentos``, se informado) e conta quantos eventos cada ativo tem
    na janela projetada. Ativos com zero eventos ou sem quantidade indicam
    cadastro incompleto, não ausência de fluxo.

    Returns:
        DataFrame com Nome Ativo, Alias, Classificação Instrumento, Quantidade,
        Saldo e Eventos Futuros, ordenado por saldo decrescente.
    """
    columns = [
        'Nome Ativo', 'Alias', 'Classificação Instrumento',
        'Quantidade', 'Saldo', 'Eventos Futuros',
    ]
    if df_positions.empty:
        return pd.DataFrame(columns=columns)

    esperados = instrumentos if instrumentos is not None else INSTRUMENTOS_EVENTOS_PROGRAMADOS
    df_assets = _latest_positions_by_asset(df_positions)
    df_assets = df_assets[df_assets['Classificação Instrumento'].isin(esperados)]
    saldo = pd.to_numeric(df_assets['Saldo'], errors='coerce').fillna(0)
    df_assets = df_assets[saldo > 0]
    if df_assets.empty:
        return pd.DataFrame(columns=columns)

    if df_events.empty:
        df_assets['Eventos Futuros'] = 0
        return df_assets[columns].sort_values(by='Saldo', ascending=False).reset_index(drop=True)

    start, end = _cash_flow_window(reference_date, horizon_months)
    df_window = df_events[
        (df_events['Data do Pagamento'] >= start) & (df_events['Data do Pagamento'] < end)
    ]
    event_counts = df_window.groupby('Ativo').size()

    df_assets['Eventos Futuros'] = (
        df_assets['Nome Ativo'].map(event_counts).fillna(0).astype(int)
    )
    return df_assets[columns].sort_values(by='Saldo', ascending=False).reset_index(drop=True)


@st.cache_data(ttl=_CACHE_TTL)
def build_ticker_issuer_lookup() -> dict[str, str]:
    """
    Mapa ticker (Name/Alias, uppercase) → emissor via cadastro Fibery.

    Usa a mesma regra de ``get_emissor_column`` (devedor, senão emissor).
    """
    df = get_emissor_column(load_assets())
    lookup: dict[str, str] = {}
    for _, row in df.iterrows():
        emissor = row.get('Emissor')
        if pd.isna(emissor) or not str(emissor).strip():
            continue
        emissor_str = str(emissor).strip()
        for key in (row.get('Name'), row.get('Alias')):
            if pd.notna(key) and str(key).strip():
                lookup[str(key).strip().upper()] = emissor_str
    return lookup


def issuer_lookup_from_snapshot(snapshot: dict) -> dict[str, str]:
    """Fallback: ticker → emissor a partir de posições no snapshot."""
    lookup: dict[str, str] = {}
    for data in snapshot.values():
        for posicoes in data.get('posicoes_por_classe', {}).values():
            for pos in posicoes:
                ticker = pos.get('nome') or pos.get('ticker') or pos.get('codigo')
                emissor = pos.get('emissor')
                if ticker and emissor:
                    lookup[str(ticker).strip().upper()] = str(emissor).strip()
    return lookup


def enrich_assets_with_issuers(
    df_assets: pd.DataFrame,
    cadastro_lookup: dict[str, str],
    snapshot_lookup: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Preenche coluna ``Emissor`` a partir do cadastro (e snapshot como fallback).

    Valores já preenchidos são preservados (override manual).
    """
    df = df_assets.copy()
    if 'Emissor' not in df.columns:
        df['Emissor'] = pd.NA

    fallback = snapshot_lookup or {}
    for idx, row in df.iterrows():
        current = row.get('Emissor')
        if pd.notna(current) and str(current).strip():
            continue
        ticker = str(row.get('Ticker', '')).strip().upper()
        if not ticker or ticker == 'NAN':
            continue
        emissor = cadastro_lookup.get(ticker) or fallback.get(ticker)
        if emissor:
            df.at[idx, 'Emissor'] = emissor
    return df


def build_portfolio_snapshot(
    df_positions: pd.DataFrame,
    df_target_allocations: pd.DataFrame,
    *,
    reference_date: datetime | None = None,
    active_carteiras_only: bool = True,
    portfolios: Iterable[str] | None = None,
) -> dict:
    """
    Constrói um snapshot JSON estruturado por portfolio com posições e targets,
    pronto para ser consumido por um modelo de IA para suporte a alocações.

    Espera posições normalizadas (com coluna ``Emissor Geral``) e targets
    retornados por ``load_target_allocations``. Usa a data de posição mais
    recente **por portfolio** como referência.

    Por padrão, inclui apenas carteiras administradas ativas
    (``load_active_carteiras_adm``). Use ``active_carteiras_only=False`` para
    incluir qualquer portfolio presente nas posições, ou ``portfolios`` para
    uma seleção explícita.

    O snapshot inclui por portfolio:
    - data_referencia: data do snapshot mais recente disponível para o portfolio
    - patrimonio_brl: patrimônio total
    - metricas: indicadores sintéticos (n_ativos, maior posição, concentração, gaps críticos)
    - distribuicao_por_classe: alocação atual por classe de ativo
    - targets_e_gaps: target, posição atual e desvio para todas as classes com target definido
    - concentracao_emissores_rf: concentração de crédito por emissor/devedor (RF)
    - vencimentos_rf: saldo de RF segmentado por prazo de vencimento
    - posicoes_por_classe: posições individuais enriquecidas com instrumento, emissor,
      indexador e vencimento
    - custodiantes: lista de custodiantes (acrônimo) com posição atual no portfolio
    """
    codes_in_positions = set(df_positions["Portfolio"].dropna().unique())

    if portfolios is not None:
        allowed = set(portfolios)
    elif active_carteiras_only:
        allowed = active_carteira_codes()
    else:
        allowed = codes_in_positions

    portfolio_list = sorted(codes_in_positions & allowed)

    df_targets = df_target_allocations.reset_index()
    idx = df_targets.groupby(['Portfolio', 'Name'])['Data Documento'].idxmax()
    df_targets_latest = df_targets.loc[idx].reset_index(drop=True)

    hoje = pd.Timestamp((reference_date or datetime.now()).date())

    snapshot = {}

    for portfolio in portfolio_list:
        df_port = df_positions[df_positions['Portfolio'] == portfolio].copy()
        latest_date = df_port['Data Posição'].max()
        data_referencia = str(latest_date.date()) if pd.notna(latest_date) else None
        df_port = df_port[df_port['Data Posição'] == latest_date].copy()

        patrimonio = float(df_port['Saldo'].sum()) if not df_port.empty else 0.0

        df_port['Emissor Geral'] = df_port['Emissor Geral'].fillna('N/A')
        df_port['Nome Ativo Completo'] = df_port['Nome Ativo Completo'].fillna('')
        df_port['Classificação Instrumento'] = df_port['Classificação Instrumento'].fillna('')

        has_indexador = 'Indexador' in df_port.columns

        group_cols = [
            'Nome Ativo', 'Nome Ativo Completo',
            'Classificação do Conjunto', 'Classificação Instrumento', 'Emissor Geral',
        ]
        agg_dict: dict = {
            'Saldo': ('Saldo', 'sum'),
            'Quantidade': ('Quantidade', 'sum'),
            'Data Vencimento': ('Data Vencimento', 'first'),
        }
        if has_indexador:
            agg_dict['Indexador'] = ('Indexador', 'first')

        df_pos = df_port.groupby(group_cols, dropna=False).agg(**agg_dict).reset_index()
        df_pos = df_pos.sort_values('Saldo', ascending=False)

        posicoes_por_classe: dict = {}
        for _, row in df_pos.iterrows():
            asset_class = row['Classificação do Conjunto']
            pct_total = (row['Saldo'] / patrimonio * 100) if patrimonio else 0.0
            dv = row['Data Vencimento']
            entry: dict = {
                'nome': row['Nome Ativo'],
                'nome_completo': row['Nome Ativo Completo'] or None,
                'instrumento': row['Classificação Instrumento'] or None,
                'emissor': row['Emissor Geral'] if row['Emissor Geral'] != 'N/A' else None,
                'saldo_brl': round(float(row['Saldo']), 2),
                'pct_total': round(pct_total, 4),
                'data_vencimento': str(dv)[:10] if pd.notna(dv) else None,
            }
            if has_indexador:
                ix = row.get('Indexador')
                entry['indexador'] = ix if pd.notna(ix) and ix else None
            posicoes_por_classe.setdefault(asset_class, []).append(entry)

        saldo_por_classe = df_port.groupby('Classificação do Conjunto')['Saldo'].sum()
        dist_por_classe: dict = {}
        for asset_class in ASSET_CLASSES_ORDER:
            saldo_classe = saldo_por_classe.get(asset_class, np.nan)
            if pd.notna(saldo_classe) and saldo_classe > 0:
                pct_classe = float(saldo_classe) / patrimonio * 100 if patrimonio else 0.0
                dist_por_classe[asset_class] = {
                    'saldo_brl': round(float(saldo_classe), 2),
                    'pct_total': round(pct_classe, 4),
                }

        df_port_targets = df_targets_latest[df_targets_latest['Portfolio'] == portfolio]
        targets: dict = {}
        for _, trow in df_port_targets.iterrows():
            classe = trow['Name']
            target_pct = float(trow['Target']) * 100 if pd.notna(trow['Target']) else None
            atual_info = dist_por_classe.get(classe)
            atual_pct = atual_info['pct_total'] if atual_info else 0.0
            gap_pp = round(target_pct - atual_pct, 4) if target_pct is not None else None
            gap_brl = round((target_pct - atual_pct) / 100 * patrimonio, 2) \
                if target_pct is not None and patrimonio else None
            targets[classe] = {
                'target_pct': round(target_pct, 4) if target_pct is not None else None,
                'atual_pct': round(atual_pct, 4),
                'gap_pp': gap_pp,
                'gap_brl': gap_brl,
            }

        df_rf = df_port[df_port['Classificação Instrumento'].isin(INSTRUMENTOS_RF)]
        emissores_rf = df_rf.groupby('Emissor Geral')['Saldo'].sum().sort_values(ascending=False)
        concentracao_emissores_rf = {
            emissor: {
                'saldo_brl': round(float(saldo), 2),
                'pct_total': round(float(saldo) / patrimonio * 100, 4) if patrimonio else 0.0,
            }
            for emissor, saldo in emissores_rf.items()
            if emissor != 'N/A' and saldo > 0
        }

        vencimentos_rf: dict = {}
        if 'Data Vencimento' in df_rf.columns:
            df_rf_venc = df_rf[df_rf['Data Vencimento'].notna()].copy()
            df_rf_venc['dias_venc'] = (
                pd.to_datetime(df_rf_venc['Data Vencimento']) - hoje
            ).dt.days
            buckets = {
                '0_90d': df_rf_venc[df_rf_venc['dias_venc'] <= 90]['Saldo'].sum(),
                '91_365d': df_rf_venc[
                    (df_rf_venc['dias_venc'] > 90) & (df_rf_venc['dias_venc'] <= 365)
                ]['Saldo'].sum(),
                '366d_mais': df_rf_venc[df_rf_venc['dias_venc'] > 365]['Saldo'].sum(),
            }
            vencimentos_rf = {
                k: {
                    'saldo_brl': round(float(v), 2),
                    'pct_total': round(float(v) / patrimonio * 100, 4) if patrimonio else 0.0,
                }
                for k, v in buckets.items()
                if v > 0
            }

        if not df_pos.empty:
            idx_max = df_pos['Saldo'].idxmax()
            maior_nome = df_pos.loc[idx_max, 'Nome Ativo']
            maior_pct = round(float(df_pos.loc[idx_max, 'Saldo']) / patrimonio * 100, 4) \
                if patrimonio else 0.0
        else:
            maior_nome = None
            maior_pct = 0.0

        top3_emissores_rf_pct = round(
            float(emissores_rf.head(3).sum()) / patrimonio * 100, 4
        ) if patrimonio and not emissores_rf.empty else 0.0

        gaps_criticos = [
            f"{cls}: {info['gap_pp']:+.2f}pp"
            for cls, info in targets.items()
            if info['gap_pp'] is not None and abs(info['gap_pp']) >= 2.0
        ]

        if 'Custodiante Acronimo' in df_port.columns:
            custodiantes = sorted({
                str(c).strip()
                for c in df_port['Custodiante Acronimo'].dropna().unique()
                if str(c).strip()
            })
        else:
            custodiantes = []

        metricas = {
            'n_ativos': int(len(df_pos)),
            'maior_posicao_nome': maior_nome,
            'maior_posicao_pct': maior_pct,
            'top3_emissores_rf_pct': top3_emissores_rf_pct,
            'gaps_criticos': gaps_criticos,
        }

        snapshot[portfolio] = {
            'data_referencia': data_referencia,
            'patrimonio_brl': round(patrimonio, 2),
            'metricas': metricas,
            'distribuicao_por_classe': dist_por_classe,
            'targets_e_gaps': targets,
            'concentracao_emissores_rf': concentracao_emissores_rf,
            'vencimentos_rf': vencimentos_rf,
            'posicoes_por_classe': posicoes_por_classe,
            'custodiantes': custodiantes,
        }

    return snapshot


def enrich_snapshot_with_officers(
    snapshot: dict,
    df_portfolio_info: pd.DataFrame | None = None,
) -> dict:
    """Adiciona ``officer_atual`` e ``tipo_cliente`` a cada portfolio do snapshot."""
    if df_portfolio_info is None:
        df_portfolio_info = load_portfolio_info()

    portfolio_meta = (
        df_portfolio_info.dropna(subset=['Name'])
        .drop_duplicates(subset=['Name'])
        .set_index('Name')
    )
    officers = (
        portfolio_meta['Officer Atual'].to_dict()
        if 'Officer Atual' in portfolio_meta.columns
        else {}
    )
    tipos_cliente = (
        portfolio_meta['Tipo Cliente'].to_dict()
        if 'Tipo Cliente' in portfolio_meta.columns
        else {}
    )

    enriched: dict = {}
    for code, data in snapshot.items():
        entry = dict(data)
        officer = officers.get(code)
        if officer is not None and pd.notna(officer):
            entry['officer_atual'] = officer
        tipo = tipos_cliente.get(code)
        if tipo is not None and pd.notna(tipo):
            entry['tipo_cliente'] = str(tipo).strip()
        enriched[code] = entry
    return enriched


def clients_from_snapshot(
    snapshot: dict,
    officer_filter: str | list[str] | None = None,
    tipo_cliente_filter: list[str] | None = None,
    exclude: list[str] | None = None,
    custodian_filter: list[str] | None = None,
) -> list:
    """
    Converte snapshot de portfólios em lista de ``Client`` para o AllocationEngine.

    Espelha ``load_snapshot`` do allocation_engine, mas aceita dict em memória.

    officer_filter : string única (match parcial) ou lista de officers (match exato).
    tipo_cliente_filter : lista de tipos (ex.: ``["PF", "PJ"]``); vazio/None = todos.
    custodian_filter : lista de custodiantes (ex.: ``["XPCV", "BTG CTVM"]``); inclui o
        cliente se ele tiver posição em ao menos um dos custodiantes selecionados.
        Baseado em ``custodiantes`` do snapshot (posições atuais). Vazio/None = todos.
    """
    from persevera_tools.quant_research.allocation_engine import Client, normalize_issuer

    excluded = set(exclude or [])
    clients = []

    if isinstance(officer_filter, str):
        officer_filters = [officer_filter] if officer_filter else []
        partial_match = True
    else:
        officer_filters = list(officer_filter or [])
        partial_match = False

    allowed_officers = {str(o) for o in officer_filters}
    allowed_tipos = {str(t).strip() for t in (tipo_cliente_filter or []) if str(t).strip()}
    allowed_custodians = {str(c).strip() for c in (custodian_filter or []) if str(c).strip()}

    for cod, data in snapshot.items():
        pl = data.get('patrimonio_brl', 0)
        if pl <= 0:
            continue

        if cod in excluded:
            continue

        officer = data.get('officer_atual')

        if officer_filters:
            if officer is None:
                continue
            officer_str = str(officer)
            if partial_match:
                if not any(f.lower() in officer_str.lower() for f in officer_filters):
                    continue
            elif officer_str not in allowed_officers:
                continue

        if allowed_tipos:
            tipo = data.get('tipo_cliente')
            if tipo is None or str(tipo).strip() not in allowed_tipos:
                continue

        if allowed_custodians:
            custodiantes = {str(c).strip() for c in (data.get('custodiantes') or [])}
            if not (custodiantes & allowed_custodians):
                continue

        cash = (
            data.get('distribuicao_por_classe', {})
            .get('Caixa e Equivalentes', {})
            .get('saldo_brl', 0.0)
        )

        existing: dict[str, float] = {}
        for posicoes in data.get('posicoes_por_classe', {}).values():
            for pos in posicoes:
                ticker = (
                    pos.get('nome')
                    or pos.get('ticker')
                    or pos.get('codigo')
                    or ''
                )
                if ticker:
                    existing[ticker] = existing.get(ticker, 0.0) + pos.get('saldo_brl', 0.0)

        existing_by_issuer: dict[str, float] = {}
        for emissor, info in data.get('concentracao_emissores_rf', {}).items():
            key = normalize_issuer(emissor)
            if key:
                existing_by_issuer[key] = (
                    existing_by_issuer.get(key, 0.0) + info.get('saldo_brl', 0.0)
                )

        clients.append(Client(
            code=cod,
            pl=pl,
            cash=cash,
            existing_positions=existing,
            existing_by_issuer=existing_by_issuer,
            officer=officer,
        ))

    return clients
