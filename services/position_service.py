import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
from collections.abc import Iterable
from typing import Optional

from utils.ui import track_data_load

from persevera_tools.data.providers import ComdinheiroProvider
from persevera_tools.db.fibery import read_fibery


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

_POSITIONS_COLUMNS = [
    "Data Posição", "Portfolio", "Custodiante Acronimo",
    "Nome Ativo", "Nome Ativo Completo", "Alias",
    "Classificação do Conjunto", "Classificação Instrumento-Relation",
    "Nome Emissor", "Nome Devedor",
    "Quantidade", "Valor Unitário", "Saldo",
    "Indexador",
    "Dias Úteis", "creation-date",
    "Data Vencimento",
]

_POSITIONS_DEDUP_SUBSET = [
    'Data Posição', 'Portfolio', 'Nome Ativo', 'Custodiante Acronimo', 'Saldo',
]


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

    temp = df.copy()
    temp['__date__'] = dates
    for i, g in enumerate(groups):
        temp[f'__grp_{i}__'] = g
    grp_cols = [f'__grp_{i}__' for i in range(len(groups))]

    latest_per_group = temp.groupby(grp_cols)['__date__'].transform('max')
    mask = temp['__date__'] == latest_per_group
    result = df.loc[mask.values]
    return result


def _normalize_positions_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza DataFrame bruto de posições do Fibery."""
    df = df[_POSITIONS_COLUMNS].copy()
    df['Data Posição'] = pd.to_datetime(df['Data Posição'])
    df['creation-date'] = pd.to_datetime(df['creation-date'])
    df = df[df['Dias Úteis'].notna()]
    df = df.drop(columns=['Dias Úteis'])
    df = df.drop_duplicates(subset=_POSITIONS_DEDUP_SUBSET, keep='last')
    df = df.drop(columns=['creation-date'])
    df = df.dropna(subset=['Classificação do Conjunto'])
    df = df.rename(columns={'Classificação Instrumento-Relation': 'Classificação Instrumento'})
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


def prepare_comdinheiro_portfolio_positions_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renomeia colunas de posições do Comdinheiro e normaliza `Ticker` para match com cadastro.

    Args:
        df: DataFrame retornado por `load_portfolio_from_comdinheiro` (colunas em snake_case).

    Returns:
        Cópia com nomes amigáveis e sufixos de precificação/série removidos do ticker.
    """
    out = df.rename(columns=_COMDINHEIRO_PORTFOLIO_COLUMN_MAP).copy()
    strip_pattern = r'|'.join(_COMDINHEIRO_TICKER_STRIP_SUBSTRINGS)
    out['Ticker'] = out['Ticker'].str.replace(strip_pattern, '', regex=True)
    out['Ticker'] = out['Ticker'].str.replace(r'_@.*$', '', regex=True)
    return out


@st.cache_data(ttl=_CACHE_TTL)
def load_assets() -> pd.DataFrame:
    """
    Carrega ativos do Fibery.

    Returns:
        DataFrame com as ativos.
    """
    
    df = read_fibery(
        table_name="Inv-Taxonomia/Ativos",
        include_fibery_fields=False,
    )
    df = df.drop_duplicates(subset=['Name'])
    track_data_load("assets")
    return df


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
    )

    df['Status do Emissor'] = df['Status do Emissor'].fillna('Sem Classificação')
    df = df[["Nome Emissor", "Status do Emissor"]]
    track_data_load("issuers")
    return df


@st.cache_data(ttl=_CACHE_TTL)
def load_positions(days_lookback: int = 4) -> pd.DataFrame:
    """
    Carrega posições do Fibery.
    
    Args:
        days_lookback: Número de dias para buscar posições (padrão: 4).
    
    Returns:
        DataFrame com as posições.
    """
    data_recente = (datetime.now() - timedelta(days=days_lookback)).strftime('%Y-%m-%dT00:00:00Z')
    
    df = read_fibery(
        table_name="Inv-Asset Allocation/Posição",
        where_filter=[">=", ["Inv-Asset Allocation/Data Posição"], "$dataRecente"],
        params={"$dataRecente": data_recente},
        include_fibery_fields=False,
    )

    track_data_load("positions")
    return _normalize_positions_df(df)


@st.cache_data(ttl=_CACHE_TTL)
def load_positions_for_portfolio(portfolio: str) -> pd.DataFrame:
    """
    Carrega todo o histórico disponível de posições para um único portfolio.

    Args:
        portfolio: Código do portfolio (ex: 'ABCD').

    Returns:
        DataFrame com todas as posições históricas do portfolio.
    """
    df = read_fibery(
        table_name="Inv-Asset Allocation/Posição",
        where_filter=["=", ["Inv-Asset Allocation/Portfolio", "Ops-Portfolios/Name"], "$portfolio"],
        params={"$portfolio": portfolio},
        include_fibery_fields=False,
    )

    track_data_load("positions_portfolio")
    return _normalize_positions_df(df)


@st.cache_data(ttl=_CACHE_TTL)
def load_target_allocations(include_limits: bool = False) -> pd.DataFrame:
    """
    Carrega alocações target do Fibery.
    
    Args:
        include_limits: Se True, inclui colunas 'PL Min' e 'PL Max'.
    
    Returns:
        DataFrame com as alocações target indexado por Portfolio, Data e Name.
    """
    df = read_fibery(
        table_name="Ops-Portfolios/Parâmetro de PctPL Polinv",
        include_fibery_fields=False
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
    df = read_fibery(table_name="Ops-InstFin/Conta", include_fibery_fields=False)
    df = df[df["Status Habilitação"] == "Sob Gestão"]
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
        include_fibery_fields=False
    )
    df = df[["Name", "Cobertura FGC"]]
    instruments_list = df[df["Cobertura FGC"]]["Name"].tolist()
    return instruments_list


@st.cache_data(ttl=_CACHE_TTL)
def load_portfolio_info() -> pd.DataFrame:
    """
    Carrega informações dos portfolios do Fibery.

    Returns:
        DataFrame com os portfolios.
    """
    
    df = read_fibery(
        table_name="Ops-Portfolios/Portfolio",
        include_fibery_fields=True,
    )

    track_data_load("portfolio_info")
    return df


@st.cache_data(ttl=_CACHE_TTL)
def load_active_carteiras_adm() -> dict:
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


def active_carteira_codes() -> set[str]:
    """Retorna os códigos das carteiras administradas ativas."""
    return set(load_active_carteiras_adm().keys())


@st.cache_data(ttl=_CACHE_TTL)
def load_portfolios_rvqm() -> pd.DataFrame:
    """
    Carrega portfólios com carteira RVQM ativa do Fibery.
    
    Returns:
        DataFrame com os portfólios com carteira RVQM ativa.
    """
    df = read_fibery(table_name="Inv-Asset Allocation/Clientes com Carteira RVQM", include_fibery_fields=False)
    df = df[df["Carteira Ativa"]]
    df = df[["Portfolio", "Conta", "Custodiante", "Nr Conta", "Percentual do PL"]]
    return df


@st.cache_data(ttl=_CACHE_TTL)
def load_equities_portfolio() -> pd.DataFrame:
    """
    Carrega portfólio de ações do Fibery.
    
    Returns:
        DataFrame com o portfólio de ações.
    """
    df = read_fibery(table_name="Inv-Asset Allocation/Carteira RVQM", include_fibery_fields=False)
    df = df[["Data de Implementação", "Ativo", "Peso"]].copy()
    df['Data de Implementação'] = pd.to_datetime(df['Data de Implementação'])
    df = df.rename(columns={'Ativo': 'code', 'Data de Implementação': 'date', 'Peso': 'weight'})
    return df


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
    Adiciona coluna 'Emissor' preenchendo Nome Devedor ou Nome Emissor.
    
    Args:
        df: DataFrame com colunas 'Nome Devedor' e 'Nome Emissor'.
    
    Returns:
        DataFrame com coluna 'Emissor' adicionada.
    """
    df = df.copy()
    df['Emissor'] = df['Nome Devedor'].fillna(df['Nome Emissor'])
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
        }

    return snapshot


def enrich_snapshot_with_officers(
    snapshot: dict,
    df_portfolio_info: pd.DataFrame | None = None,
) -> dict:
    """Adiciona ``officer_atual`` a cada portfolio do snapshot."""
    if df_portfolio_info is None:
        df_portfolio_info = load_portfolio_info()

    officers = (
        df_portfolio_info.dropna(subset=['Name'])
        .drop_duplicates(subset=['Name'])
        .set_index('Name')['Officer Atual']
        .to_dict()
    )

    enriched: dict = {}
    for code, data in snapshot.items():
        entry = dict(data)
        officer = officers.get(code)
        if officer is not None and pd.notna(officer):
            entry['officer_atual'] = officer
        enriched[code] = entry
    return enriched


def clients_from_snapshot(
    snapshot: dict,
    officer_filter: str | list[str] | None = None,
    exclude: list[str] | None = None,
) -> list:
    """
    Converte snapshot de portfólios em lista de ``Client`` para o AllocationEngine.

    Espelha ``load_snapshot`` do allocation_engine, mas aceita dict em memória.

    officer_filter : string única (match parcial) ou lista de officers (match exato).
    """
    from persevera_tools.quant_research.allocation_engine import Client

    excluded = set(exclude or [])
    clients = []

    if isinstance(officer_filter, str):
        officer_filters = [officer_filter] if officer_filter else []
        partial_match = True
    else:
        officer_filters = list(officer_filter or [])
        partial_match = False

    allowed_officers = {str(o) for o in officer_filters}

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

        clients.append(Client(
            code=cod,
            pl=pl,
            cash=cash,
            existing_positions=existing,
            officer=officer,
        ))

    return clients
