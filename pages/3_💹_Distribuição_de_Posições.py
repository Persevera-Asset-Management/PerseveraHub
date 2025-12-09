import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime, date
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from persevera_tools.db.fibery import read_fibery
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS_ADM
from utils.auth import check_authentication

st.set_page_config(
    page_title="Distribuição de Posições | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Distribuição de Posições")

@st.cache_data
def load_positions():
  df = read_fibery(
    table_name="Inv-Asset Allocation/Posição",
    include_fibery_fields=False
  )
  df = df[[
    "creation-date", "Portfolio",
    "Nome Ativo", "Nome Ativo Completo",
    "Classificação do Conjunto", "Classificação Instrumento",
    "Nome Emissor", "Nome Devedor",
    "Quantidade", "Valor Unitário", "Saldo"
  ]]
  return df

@st.cache_data
def load_target_allocations():
  df = read_fibery(
    table_name="Ops-Portfolios/Parâmetro de PctPL Polinv",
    include_fibery_fields=False
  )
  df["Portfolio"] = np.where(df["Política de Investimento"].isna(), df["Alocação Target"].str.split("_").str[0], df["Política de Investimento"].str.split("_").str[0])
  df["Tipo Documento"] = np.where(df["Política de Investimento"].isna(), df["Alocação Target"].str.split("_").str[1], df["Política de Investimento"].str.split("_").str[1])
  df["Data Documento"] = np.where(df["Política de Investimento"].isna(), pd.to_datetime(df["Alocação Target"].str[-10:]), pd.to_datetime(df["Política de Investimento"].str[-10:]))
  df = df[["Portfolio", "Tipo Documento", "Data Documento", "Name", "Target"]]

  df = df.groupby(['Portfolio', pd.Grouper(key='Data Documento', freq='D'), 'Name']).agg(
    **{
      'Target': ('Target', 'mean')
    }
  )
  return df

if 'df' not in st.session_state:
    st.session_state.df = None

if 'df_target_allocations' not in st.session_state:
    st.session_state.df_target_allocations = None

with st.spinner("Carregando dados...", show_time=True):
  st.session_state.df = load_positions()
  st.session_state.df_target_allocations = load_target_allocations()

df = st.session_state.df
df['Emissor Geral'] = df['Nome Devedor'].fillna(df['Nome Emissor'])
df_target_allocations = st.session_state.df_target_allocations

asset_classes = [
  'Caixa e Equivalentes',
  'Renda Fixa Pós-Fixada',
  'Renda Fixa Pré-Fixada',
  'Renda Fixa Atrelada à Inflação',
  'Renda Fixa em Moeda Estrangeira',
  'Renda Variável Nacional',
  'Renda Variável Internacional',
  'Retorno Total',
  'Fundos Imobiliários',
  'Investimentos Alternativos',
  'Ativos Digitais',
  'Commodities',
]

with st.sidebar:
  selected_visualization = st.radio("Visualizar por", options=['Financeiro (R$)', 'Percentual da Classe (%)', 'Percentual do Total (%)'], index=0)

if df is not None:
  try:
    # Composição Completa
    st.markdown("##### Distribuição por Classe")
    df_positions = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Portfolio', 'Nome Ativo', 'Nome Ativo Completo', 'Classificação do Conjunto']).agg(
      **{
        'Quantidade': ('Quantidade', 'sum'),
        'Valor Unitário': ('Valor Unitário', 'mean'),
        'Saldo': ('Saldo', 'sum')
      }
    )
    df_positions_current = df_positions.loc[df_positions.index.get_level_values(level=0).max()].reset_index()

    df_total_positions = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Portfolio']).agg(**{'Saldo': ('Saldo', 'sum')})
    df_total_positions_current = df_total_positions.loc[df_total_positions.index.get_level_values(level=0).max()]

    df_total_positions_by_asset_class = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Portfolio', 'Classificação do Conjunto'])['Saldo'].sum()
    df_total_positions_by_asset_class_current = df_total_positions_by_asset_class.loc[df_total_positions_by_asset_class.index.get_level_values(level=0).max()].reset_index()
    df_total_positions_by_asset_class_current = df_total_positions_by_asset_class_current.pivot(index='Classificação do Conjunto', columns='Portfolio', values='Saldo')
    df_total_positions_by_asset_class_current = df_total_positions_by_asset_class_current.reindex(asset_classes)
    df_total_positions_by_asset_class_current_pct = df_total_positions_by_asset_class_current.div(df_total_positions_by_asset_class_current.sum(axis=0), axis=1) * 100

    st.dataframe(
      style_table(
        df_total_positions_by_asset_class_current_pct,
        numeric_cols_format_as_float=list(df_total_positions_by_asset_class_current_pct.columns),
      )
    )

    # Emissores e Devedores
    st.markdown("##### Distribuição por Emissores e Devedores (RF)")
    instrumentos_rf = [
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
      'Debênture'
    ]
    df_positions_emissor_devedor = df[df['Classificação Instrumento'].isin(instrumentos_rf)].groupby([pd.Grouper(key='creation-date', freq='D'), 'Portfolio', 'Emissor Geral']).agg(**{'Saldo': ('Saldo', 'sum')})
    df_emissor_devedor_current = df_positions_emissor_devedor.loc[df_positions_emissor_devedor.index.get_level_values(level=0).max()].reset_index().sort_values(by='Saldo', ascending=False)
    df_emissor_devedor_current = df_emissor_devedor_current.pivot(index='Emissor Geral', columns='Portfolio', values='Saldo')
    df_emissor_devedor_current = df_emissor_devedor_current.reindex(df_emissor_devedor_current.index.unique())
    df_emissor_devedor_current = df_emissor_devedor_current.div(df_total_positions_current['Saldo']) * 100

    st.dataframe(
      style_table(
        df_emissor_devedor_current,
        numeric_cols_format_as_float=list(df_emissor_devedor_current.columns),
      )
    )

    # Alocação vs Target
    selected_classes = ["Renda Fixa Pós-Fixada", "Renda Fixa Pré-Fixada", "Renda Fixa Atrelada à Inflação"]
    df_target_allocations_current = df_target_allocations.query("Name.isin(@selected_classes)").dropna(subset=['Target']).reset_index()
    idx = df_target_allocations_current.groupby(['Portfolio', 'Name'])['Data Documento'].idxmax()
    df_target_allocations_current = df_target_allocations_current.loc[idx].reset_index(drop=True)
    df_target_allocations_current = df_target_allocations_current.pivot(index='Portfolio', columns='Name', values='Target')
    
    st.markdown("##### Alocação vs Target (RF)")
    row_1 = st.columns(len(selected_classes))
    for i, class_name in enumerate(selected_classes):
      with row_1[i]:
        df_class_positions = df_target_allocations_current[class_name].to_frame("Target (%)")
        df_class_positions['Target (R$)'] = df_class_positions["Target (%)"] * df_total_positions_current['Saldo']
        df_class_positions['Atual (R$)'] = df_total_positions_by_asset_class_current.loc[class_name]
        df_class_positions['Diferença (R$)'] = df_class_positions['Target (R$)'] - df_class_positions['Atual (R$)']
        df_class_positions['Target (%)'] = df_class_positions['Target (%)'] * 100
        df_class_positions = df_class_positions.dropna()

        st.markdown(f"###### {class_name}")
        st.dataframe(
          style_table(
            df_class_positions,
            numeric_cols_format_as_float=['Target (R$)', 'Atual (R$)', 'Diferença (R$)'],
            percent_cols=['Target (%)'],
          )
        )

    # Posições por Ativo e Classe
    for asset_class in asset_classes:
      df_asset_class_positions = df_positions_current[df_positions_current['Classificação do Conjunto'] == asset_class]
      df_asset_class_positions = df_asset_class_positions.pivot(index=['Nome Ativo', 'Nome Ativo Completo'], columns='Portfolio', values='Saldo')

      if selected_visualization == 'Financeiro (R$)':
        df_asset_class_positions_visualization = df_asset_class_positions
      elif selected_visualization == 'Percentual da Classe (%)':
        df_asset_class_positions_visualization = df_asset_class_positions.div(df_asset_class_positions.sum(axis=0), axis=1) * 100
      elif selected_visualization == 'Percentual do Total (%)':
        df_asset_class_positions_visualization = df_asset_class_positions.div(df_total_positions_current['Saldo'], axis=1) * 100
      
      with st.expander(f"{asset_class}", expanded=False):
        st.dataframe(
          style_table(
            df_asset_class_positions_visualization,
            numeric_cols_format_as_float=list(df_asset_class_positions_visualization.columns) if selected_visualization == 'Financeiro (R$)' else [],
            percent_cols=list(df_asset_class_positions_visualization.columns) if selected_visualization == 'Percentual da Classe (%)' or selected_visualization == 'Percentual do Total (%)' else [],
          )
        )

  except Exception as e:
    st.error(f"Ocorreu um erro ao carregar os dados: {e}")
