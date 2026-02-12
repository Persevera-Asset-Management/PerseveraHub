"""
Serviço centralizado para carregamento e processamento de posições de carteiras.

Este módulo contém funções compartilhadas entre as páginas:
- Controle de Posições
- Distribuição de Posições
"""

import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional
from persevera_tools.db.fibery import read_fibery


# =============================================================================
# Constantes
# =============================================================================

ASSET_CLASSES_ORDER = [
    'Caixa e Equivalentes',
    'Renda Fixa Pós-Fixada',
    'Renda Fixa Pré-Fixada',
    'Renda Fixa Atrelada à Inflação',
    'Renda Variável',
    'Retorno Total',
    'Fundos Imobiliários',
    'Investimentos Alternativos',
    'Criptomoedas',
    'Commodities',
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


# =============================================================================
# Funções Utilitárias
# =============================================================================

def get_latest_date_data(df: pd.DataFrame, level: int = 0) -> pd.DataFrame:
    """
    Retorna dados da data mais recente de um DataFrame com MultiIndex.
    
    Args:
        df: DataFrame com MultiIndex onde o primeiro nível é a data.
        level: Nível do índice que contém as datas (padrão: 0).
    
    Returns:
        DataFrame filtrado para a data mais recente.
    """
    latest_date = df.index.get_level_values(level=level).max()
    return df.loc[latest_date]


# =============================================================================
# Funções de Carregamento de Dados
# =============================================================================

@st.cache_data
def load_positions(
    include_custodiante: bool = False,
    include_vencimento_rf: bool = False,
    days_lookback: int = 5
) -> pd.DataFrame:
    """
    Carrega posições do Fibery.
    
    Args:
        include_custodiante: Se True, inclui coluna 'Custodiante Acronimo'.
        include_vencimento_rf: Se True, inclui coluna 'Data de Vencimento RF'.
        days_lookback: Número de dias para buscar posições (padrão: 5).
    
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
    
    columns = [
        "Data Posição", "Portfolio",
        "Nome Ativo", "Nome Ativo Completo",
        "Classificação do Conjunto", "Classificação Instrumento-Relation",
        "Nome Emissor", "Nome Devedor",
        "Quantidade", "Valor Unitário", "Saldo",
        "Dias Úteis"
    ]
    
    if include_custodiante:
        columns.append("Custodiante Acronimo")
    
    if include_vencimento_rf:
        columns.append("Data de Vencimento RF")
    
    df = df[columns]
    df['Data Posição'] = pd.to_datetime(df['Data Posição'])

    df = df[df['Dias Úteis'].notna()]
    df.drop(columns=['Dias Úteis'], inplace=True)

    df.dropna(subset=['Classificação do Conjunto'], inplace=True)
    df.rename(columns={'Classificação Instrumento-Relation': 'Classificação Instrumento'}, inplace=True)
    
    return df


@st.cache_data
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
    
    # Extrai informações do nome do documento
    df["Portfolio"] = np.where(
        df["Política de Investimento"].isna(),
        df["Alocação Target"].str.split("_").str[0],
        df["Política de Investimento"].str.split("_").str[0]
    )
    df["Tipo Documento"] = np.where(
        df["Política de Investimento"].isna(),
        df["Alocação Target"].str.split("_").str[1],
        df["Política de Investimento"].str.split("_").str[1]
    )
    df["Data Documento"] = np.where(
        df["Política de Investimento"].isna(),
        pd.to_datetime(df["Alocação Target"].str[-10:]),
        pd.to_datetime(df["Política de Investimento"].str[-10:])
    )
    
    # Seleciona colunas baseado no parâmetro
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
    
    # Agrupa por Portfolio, Data e Name
    df = df.groupby(['Portfolio', pd.Grouper(key='Data Documento', freq='D'), 'Name']).agg(**agg_dict)
    
    return df


@st.cache_data
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


@st.cache_data
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
