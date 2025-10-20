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
    page_title="Controle de Posições | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Controle de Posições")

@st.cache_data
def load_positions():
    df = read_fibery(
      table_name="Inv-Asset Allocation/Posição",
      include_fibery_fields=False
    )
    df = df[["creation-date", "Name", "Portfolio", "Classificação do Conjunto", "Ativo Nome Completo", "Quantidade", "Valor Unitário", "Saldo"]]
    return df

@st.cache_data
def load_target_allocations():
  df = read_fibery(
    table_name="Ops-Portfolios/Parâmetro de PctPL Polinv",
    include_fibery_fields=False
  )
  df["Portfolio"] = np.where(df["Política de Investimento"].isna(), df["Alocação Target"].str.split("-").str[0], df["Política de Investimento"].str.split("-").str[0])
  df["Tipo Documento"] = np.where(df["Política de Investimento"].isna(), df["Alocação Target"].str.split("-").str[1], df["Política de Investimento"].str.split("-").str[1])
  df["Data Documento"] = np.where(df["Política de Investimento"].isna(), pd.to_datetime(df["Alocação Target"].str[-10:]), pd.to_datetime(df["Política de Investimento"].str[-10:]))
  df = df[["Portfolio", "Tipo Documento", "Data Documento", "Name", "PL Min", "PL Max", "Target"]]

  df = df.groupby(['Portfolio', pd.Grouper(key='Data Documento', freq='D'), 'Name']).agg(
    **{
      'PL Min': ('PL Min', 'mean'),
      'PL Max': ('PL Max', 'mean'),
      'Target': ('Target', 'mean')
    }
  )
  return df

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_carteira = st.selectbox("Carteira selecionada", options=sorted(CODIGOS_CARTEIRAS_ADM.keys()))
    btn_run = st.button("Executar")

if 'df' not in st.session_state:
    st.session_state.df = None

if 'df_target_allocations' not in st.session_state:
    st.session_state.df_target_allocations = None

if btn_run:
    with st.spinner("Carregando dados...", show_time=True):
      st.session_state.df_positions = load_positions()
      st.session_state.df_target_allocations = load_target_allocations()
      st.session_state.df = st.session_state.df_positions[st.session_state.df_positions['Portfolio'] == selected_carteira]

df = st.session_state.df
df_target_allocations = st.session_state.df_target_allocations

correct_order = [
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
  'Criptomoedas',
  'Commodities',
]

if df is not None:
    try:
      st.subheader(selected_carteira)
      
      # Composição Completa
      df_portfolio_positions = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Name', 'Ativo Nome Completo', 'Classificação do Conjunto']).agg(
        **{
          'Quantidade': ('Quantidade', 'sum'),
          'Valor Unitário': ('Valor Unitário', 'mean'),
          'Saldo': ('Saldo', 'sum')
        }
      )

      df_portfolio_positions_current = df_portfolio_positions.loc[df_portfolio_positions.index.get_level_values(level=0).max()]
      df_portfolio_positions_current['%'] = df_portfolio_positions_current['Saldo'] / df_portfolio_positions_current['Saldo'].sum() * 100
  
      with st.expander("Composição Completa", expanded=False):
        st.dataframe(
          style_table(
            df_portfolio_positions_current,
            numeric_cols_format_as_float=['Quantidade', 'Valor Unitário', 'Saldo', '%'],
          )
        )
      
      # Política de Investimentos
      if selected_carteira in df_target_allocations.index:
        df_policy_investments_current = df_target_allocations.loc[selected_carteira].dropna(subset=['PL Min', 'PL Max'])
        df_policy_investments_current = df_policy_investments_current.loc[df_policy_investments_current.index.get_level_values(level=0).max()]
        df_policy_investments_current = df_policy_investments_current.mul(100)
        df_policy_investments_current = df_policy_investments_current.reindex(correct_order)

        with st.expander("Política de Investimentos", expanded=False):
          st.dataframe(
            style_table(
              df_policy_investments_current.drop(columns='Target'),
              percent_cols=['PL Min', 'PL Max', 'Target'],
            )
          )
      else:
        st.warning("Política de Investimentos não cadastrada")

      st.markdown("Saldo Total: **R$ {0:,.2f}**".format(df_portfolio_positions_current['Saldo'].sum()))
      row_1 = st.columns(2)
      with row_1[0]:
        # Composição do Portfolio
        st.markdown("##### Alocação Atual")
        df_portfolio_composition = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Classificação do Conjunto']).agg(**{'Saldo': ('Saldo', 'sum')})
        df_portfolio_composition_current = df_portfolio_composition.loc[df_portfolio_composition.index.get_level_values(level=0).max()]
        df_portfolio_composition_current = df_portfolio_composition_current.reindex(correct_order).dropna()

        chart_portfolio_composition = create_chart(
          data=df_portfolio_composition_current,
          columns=['Saldo'],
          names=['Saldo'],
          chart_type='donut',
          title="",
          y_axis_title="%",
        )
        hct.streamlit_highcharts(chart_portfolio_composition)

      with row_1[1]:
        st.markdown("##### Alocação Alvo")

        if selected_carteira in df_target_allocations.index:
          df_target_allocations_current = df_target_allocations.loc[selected_carteira].dropna(subset=['Target'])
          df_target_allocations_current = df_target_allocations_current.loc[df_target_allocations_current.index.get_level_values(level=0).max()]
          df_target_allocations_current = df_target_allocations_current.mul(100)
          df_target_allocations_current = df_target_allocations_current.reindex(correct_order)

          chart_portfolio_composition_target = create_chart(
            data=df_target_allocations_current,
            columns=['Target'],
            names=['Target'],
            chart_type='donut',
            title="",
            y_axis_title="%",
          )
          hct.streamlit_highcharts(chart_portfolio_composition_target)
        else:
          st.warning("Alocação alvo não cadastrada")      

    except Exception as e:
      st.error(f"Ocorreu um erro ao carregar os dados: {e}")
