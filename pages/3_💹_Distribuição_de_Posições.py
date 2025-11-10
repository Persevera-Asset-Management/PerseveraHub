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
    df = df[["creation-date", "Name", "Portfolio", "Classificação do Conjunto", "Ativo Nome Completo", "Quantidade", "Valor Unitário", "Saldo"]]
    return df

if 'df' not in st.session_state:
    st.session_state.df = None

with st.spinner("Carregando dados...", show_time=True):
  st.session_state.df = load_positions()

df = st.session_state.df

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
    df_positions = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Portfolio', 'Name', 'Ativo Nome Completo', 'Classificação do Conjunto']).agg(
      **{
        'Quantidade': ('Quantidade', 'sum'),
        'Valor Unitário': ('Valor Unitário', 'mean'),
        'Saldo': ('Saldo', 'sum')
      }
    )
    df_positions_current = df_positions.loc[df_positions.index.get_level_values(level=0).max()].reset_index()

    # Saldo Total
    df_total_positions = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Portfolio']).agg(**{'Saldo': ('Saldo', 'sum')})
    df_total_positions_current = df_total_positions.loc[df_total_positions.index.get_level_values(level=0).max()]

    df_total_positions_by_asset_class = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Portfolio', 'Classificação do Conjunto'])['Saldo'].sum()
    df_total_positions_by_asset_class_current = df_total_positions_by_asset_class.loc[df_total_positions_by_asset_class.index.get_level_values(level=0).max()].reset_index()
    df_total_positions_by_asset_class_current = df_total_positions_by_asset_class_current.pivot(index='Classificação do Conjunto', columns='Portfolio', values='Saldo')
    df_total_positions_by_asset_class_current = df_total_positions_by_asset_class_current.reindex(asset_classes)
    df_total_positions_by_asset_class_current = df_total_positions_by_asset_class_current.div(df_total_positions_by_asset_class_current.sum(axis=0), axis=1) * 100

    st.markdown(f"##### Distribuição de Posições por Classe")
    st.dataframe(
      style_table(
        df_total_positions_by_asset_class_current,
        numeric_cols_format_as_float=list(df_total_positions_by_asset_class_current.columns),
      )
    )

    # Posições por Ativo e Classe
    for asset_class in asset_classes:
      df_asset_class_positions = df_positions_current[df_positions_current['Classificação do Conjunto'] == asset_class]
      df_asset_class_positions = df_asset_class_positions.pivot(index=['Name', 'Ativo Nome Completo'], columns='Portfolio', values='Saldo')

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
