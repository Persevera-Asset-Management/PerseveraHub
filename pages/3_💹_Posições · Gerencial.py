import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from utils.chart_helpers import create_chart, render_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS_ADM
from utils.auth import check_authentication
from services.position_service import (
    load_positions,
    load_instruments_fgc,
    get_latest_date_data,
    get_emissor_column,
)

st.set_page_config(
    page_title="Posições · Gerencial | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Posições · Gerencial")


with st.spinner("Carregando dados...", show_time=True):
    st.session_state.df = load_positions()
    st.session_state.instruments_fgc = load_instruments_fgc()

df_raw = st.session_state.df
df = df_raw.copy()
df.replace(' ', np.nan, inplace=True)
df.dropna(subset=['Nome Ativo', 'Classificação do Conjunto'], inplace=True)
df = get_emissor_column(df)
df.rename(columns={'Emissor': 'Emissor Geral'}, inplace=True)


if df is not None:
    instruments_fgc = st.session_state.instruments_fgc

    tabs = st.tabs(["Posições Consolidadas", "Vencimentos", "Cobertura do FGC"])

    with tabs[0]: # Posições Consolidadas
        df_positions = df.copy()
        df_positions = df_positions.groupby(
            ['Portfolio', pd.Grouper(key='Data Posição', freq='D'), 'Nome Ativo', 'Nome Ativo Completo',
            'Emissor Geral', 'Classificação Instrumento']
        ).agg(**{
            'Quantidade': ('Quantidade', 'sum'),
            'Valor Unitário': ('Valor Unitário', 'mean'),
            'Saldo': ('Saldo', 'sum')
        })
        df_positions_current = get_latest_date_data(df_positions, level='Data Posição', group_level='Portfolio')
        df_positions_current = df_positions_current.reset_index().set_index(['Portfolio', 'Nome Ativo'])
        df_positions_current = df_positions_current.sort_values(by='Saldo', ascending=False)
        df_positions_current = df_positions_current[df_positions_current['Saldo'] > 0]
        df_positions_current.reset_index(inplace=True)

        st.dataframe(
            style_table(
                df_positions_current[[
                    'Portfolio', 'Nome Ativo', 'Nome Ativo Completo', 'Emissor Geral', 'Classificação Instrumento',
                    'Quantidade', 'Valor Unitário', 'Saldo'
                ]].set_index(['Portfolio', 'Nome Ativo']),
                numeric_cols_format_as_float=['Valor Unitário', 'Saldo'],
                numeric_cols_format_as_int=['Quantidade'],
            )
        )
        
    with tabs[1]: # Vencimentos
        df_data_vencimento_rf = df.copy()
        df_data_vencimento_rf = df_data_vencimento_rf.groupby(
            ['Portfolio', pd.Grouper(key='Data Posição', freq='D'), 'Nome Ativo', 'Nome Ativo Completo',
            'Classificação do Conjunto', 'Classificação Instrumento', 'Data de Vencimento RF']
        ).agg(**{
            'Quantidade': ('Quantidade', 'sum'),
            'Valor Unitário': ('Valor Unitário', 'mean'),
            'Saldo': ('Saldo', 'sum')
        })
        df_data_vencimento_rf_current = get_latest_date_data(
            df_data_vencimento_rf, level='Data Posição', group_level='Portfolio'
        ).copy()
        df_data_vencimento_rf_current = df_data_vencimento_rf_current.reset_index().set_index(['Portfolio', 'Nome Ativo'])
        df_data_vencimento_rf_current['Data de Vencimento'] = pd.to_datetime(
            df_data_vencimento_rf_current['Data de Vencimento RF']
        )
        df_data_vencimento_rf_current = df_data_vencimento_rf_current.sort_values(
            by='Data de Vencimento', ascending=True
        )

        df_data_vencimento_rf_current = df_data_vencimento_rf_current[df_data_vencimento_rf_current['Saldo'] > 0]
        # Calcular Dias para Vencimento como DIAS ÚTEIS entre a Data Posição e Data de Vencimento
        df_data_vencimento_rf_current['Dias para Vencimento'] = np.busday_count(
            df_data_vencimento_rf_current['Data Posição'].values.astype('datetime64[D]'),
            df_data_vencimento_rf_current['Data de Vencimento'].values.astype('datetime64[D]')
        )

        st.dataframe(
            style_table(
                df_data_vencimento_rf_current[[
                    'Nome Ativo Completo', 'Classificação do Conjunto', 'Classificação Instrumento',
                    'Data de Vencimento', 'Dias para Vencimento', 'Quantidade', 'Valor Unitário', 'Saldo'
                ]],
                date_cols=['Data de Vencimento'],
                numeric_cols_format_as_float=['Valor Unitário', 'Saldo'],
                numeric_cols_format_as_int=['Quantidade', 'Dias para Vencimento'],
                highlight_row_if_value_lower={'Dias para Vencimento': 15},
            )
        )
     
    with tabs[2]: # Cobertura do FGC
        df_fgc = df.copy()
        df_fgc = df_fgc[df_fgc['Classificação Instrumento'].isin(instruments_fgc)]

        df_fgc = df_fgc.groupby(
            ['Portfolio', pd.Grouper(key='Data Posição', freq='D'), 'Nome Emissor']
        ).agg(**{'Saldo': ('Saldo', 'sum')})

        df_fgc_current = get_latest_date_data(
            df_fgc, level='Data Posição', group_level='Portfolio'
        ).copy()
        df_fgc_current = df_fgc_current.reset_index().set_index(['Portfolio', 'Nome Emissor'])
        df_fgc_current = df_fgc_current.sort_values(by='Saldo', ascending=False)
        df_fgc_current = df_fgc_current[df_fgc_current['Saldo'] > 0]
        df_fgc_current['Saldo Não Coberto'] = np.where(df_fgc_current['Saldo'] < 250000, 0, df_fgc_current['Saldo'] - 250000)
        df_fgc_current.drop(columns=['Data Posição'], inplace=True)

        st.dataframe(
            style_table(
                df_fgc_current,
                numeric_cols_format_as_float=['Saldo', 'Saldo Não Coberto'],
                highlight_row_if_value_greater={'Saldo Não Coberto': 0},
            )
        )
