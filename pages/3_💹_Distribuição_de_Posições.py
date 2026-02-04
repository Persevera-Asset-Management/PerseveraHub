import streamlit as st
import pandas as pd
import numpy as np
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication
from services.position_service import (
    load_positions,
    load_target_allocations,
    get_latest_date_data,
    get_emissor_column,
    ASSET_CLASSES_ORDER,
    INSTRUMENTOS_RF,
)

st.set_page_config(
    page_title="Distribuição de Posições | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Distribuição de Posições")

with st.spinner("Carregando dados...", show_time=True):
    st.session_state.df = load_positions()
    st.session_state.df_target_allocations = load_target_allocations(include_limits=False)

df_raw = st.session_state.df
df = df_raw.copy()
df.replace(' ', np.nan, inplace=True)
df.dropna(subset=['Nome Ativo', 'Classificação do Conjunto'], inplace=True)
df = get_emissor_column(df)
df.rename(columns={'Emissor': 'Emissor Geral'}, inplace=True)
df_target_allocations = st.session_state.df_target_allocations

with st.sidebar:
    selected_visualization = st.radio(
        "Visualizar por",
        options=['Financeiro (R$)', 'Percentual da Classe (%)', 'Percentual do Total (%)'],
        index=0
    )

if df is not None:
    try:
        # Composição Completa
        st.markdown("##### Distribuição por Classe")
        df_positions = df.groupby(
            [pd.Grouper(key='Data Posição', freq='D'), 'Portfolio', 'Nome Ativo',
             'Nome Ativo Completo', 'Classificação do Conjunto']
        ).agg(**{
            'Quantidade': ('Quantidade', 'sum'),
            'Valor Unitário': ('Valor Unitário', 'mean'),
            'Saldo': ('Saldo', 'sum')
        })
        df_positions_current = get_latest_date_data(df_positions).reset_index()

        df_total_positions = df.groupby(
            [pd.Grouper(key='Data Posição', freq='D'), 'Portfolio']
        ).agg(**{'Saldo': ('Saldo', 'sum')})
        df_total_positions_current = get_latest_date_data(df_total_positions)

        df_total_positions_by_asset_class = df.groupby(
            [pd.Grouper(key='Data Posição', freq='D'), 'Portfolio', 'Classificação do Conjunto']
        )['Saldo'].sum()
        df_total_positions_by_asset_class_current = get_latest_date_data(
            df_total_positions_by_asset_class
        ).reset_index()
        df_total_positions_by_asset_class_current = df_total_positions_by_asset_class_current.pivot(
            index='Classificação do Conjunto', columns='Portfolio', values='Saldo'
        )
        df_total_positions_by_asset_class_current = df_total_positions_by_asset_class_current.reindex(
            ASSET_CLASSES_ORDER
        )
        df_total_positions_by_asset_class_current_pct = (
            df_total_positions_by_asset_class_current.div(
                df_total_positions_by_asset_class_current.sum(axis=0), axis=1
            ) * 100
        )

        st.dataframe(
            style_table(
                df_total_positions_by_asset_class_current_pct,
                numeric_cols_format_as_float=list(df_total_positions_by_asset_class_current_pct.columns),
            )
        )

        # Emissores e Devedores
        st.markdown("##### Distribuição por Emissores e Devedores (RF)")
        df_positions_emissor_devedor = df[df['Classificação Instrumento'].isin(INSTRUMENTOS_RF)].groupby(
            [pd.Grouper(key='Data Posição', freq='D'), 'Portfolio', 'Emissor Geral']
        ).agg(**{'Saldo': ('Saldo', 'sum')})
        df_emissor_devedor_current = get_latest_date_data(
            df_positions_emissor_devedor
        ).reset_index().sort_values(by='Saldo', ascending=False)
        df_emissor_devedor_current = df_emissor_devedor_current.pivot(
            index='Emissor Geral', columns='Portfolio', values='Saldo'
        )
        df_emissor_devedor_current = df_emissor_devedor_current.reindex(
            df_emissor_devedor_current.index.unique()
        )
        df_emissor_devedor_current = df_emissor_devedor_current.div(
            df_total_positions_current['Saldo']
        ) * 100

        st.dataframe(
            style_table(
                df_emissor_devedor_current,
                numeric_cols_format_as_float=list(df_emissor_devedor_current.columns),
            )
        )

        # Alocação vs Target
        selected_classes = [
            "Renda Fixa Pós-Fixada",
            "Renda Fixa Pré-Fixada",
            "Renda Fixa Atrelada à Inflação"
        ]
        df_target_allocations_current = df_target_allocations.query(
            "Name.isin(@selected_classes)"
        ).dropna(subset=['Target']).reset_index()
        idx = df_target_allocations_current.groupby(['Portfolio', 'Name'])['Data Documento'].idxmax()
        df_target_allocations_current = df_target_allocations_current.loc[idx].reset_index(drop=True)
        df_target_allocations_current = df_target_allocations_current.pivot(
            index='Portfolio', columns='Name', values='Target'
        )

        st.markdown("##### Alocação vs Target (RF)")
        row_1 = st.columns(len(selected_classes))
        for i, class_name in enumerate(selected_classes):
            with row_1[i]:
                df_class_positions = df_target_allocations_current[class_name].to_frame("Target (%)")
                df_class_positions['Target (R$)'] = (
                    df_class_positions["Target (%)"] * df_total_positions_current['Saldo']
                )
                df_class_positions['Atual (R$)'] = (
                    df_total_positions_by_asset_class_current.loc[class_name].fillna(0)
                )
                df_class_positions['Diferença (R$)'] = (
                    df_class_positions['Target (R$)'] - df_class_positions['Atual (R$)']
                )
                df_class_positions['Target (%)'] = df_class_positions['Target (%)'] * 100
                df_class_positions['Atual (%)'] = (
                    df_total_positions_by_asset_class_current.loc[class_name].fillna(0)
                    / df_total_positions_current['Saldo'] * 100
                )
                df_class_positions = df_class_positions.dropna(thresh=2)

                st.markdown(f"###### {class_name}")
                st.dataframe(
                    style_table(
                        df_class_positions[[
                            'Target (%)', 'Atual (%)', 'Target (R$)', 'Atual (R$)', 'Diferença (R$)'
                        ]],
                        numeric_cols_format_as_float=['Target (R$)', 'Atual (R$)', 'Diferença (R$)'],
                        percent_cols=['Target (%)', 'Atual (%)'],
                    )
                )

        # Posições por Ativo e Classe
        for asset_class in ASSET_CLASSES_ORDER:
            df_asset_class_positions = df_positions_current[
                df_positions_current['Classificação do Conjunto'] == asset_class
            ]
            df_asset_class_positions = df_asset_class_positions.pivot(
                index=['Nome Ativo', 'Nome Ativo Completo'], columns='Portfolio', values='Saldo'
            )

            if selected_visualization == 'Financeiro (R$)':
                df_asset_class_positions_visualization = df_asset_class_positions
            elif selected_visualization == 'Percentual da Classe (%)':
                df_asset_class_positions_visualization = (
                    df_asset_class_positions.div(df_asset_class_positions.sum(axis=0), axis=1) * 100
                )
            elif selected_visualization == 'Percentual do Total (%)':
                df_asset_class_positions_visualization = (
                    df_asset_class_positions.div(df_total_positions_current['Saldo'], axis=1) * 100
                )

            is_financial = selected_visualization == 'Financeiro (R$)'
            is_percent = selected_visualization in [
                'Percentual da Classe (%)', 'Percentual do Total (%)'
            ]

            with st.expander(f"{asset_class}", expanded=False):
                st.dataframe(
                    style_table(
                        df_asset_class_positions_visualization,
                        numeric_cols_format_as_float=(
                            list(df_asset_class_positions_visualization.columns) if is_financial else []
                        ),
                        percent_cols=(
                            list(df_asset_class_positions_visualization.columns) if is_percent else []
                        ),
                    )
                )

    except KeyError as e:
        st.error(f"Erro ao acessar dados: campo {e} não encontrado")
    except IndexError as e:
        st.error(f"Erro ao acessar dados: índice inválido - {e}")
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
