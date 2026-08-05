import pandas as pd
import numpy as np
from datetime import datetime
import json

import streamlit as st

from utils.ui import show_data_freshness
from utils.table import style_table
from services.position_service import (
    load_positions,
    load_target_allocations,
    load_portfolio_info,
    get_latest_date_data,
    get_emissor_column,
    build_portfolio_snapshot,
    ASSET_CLASSES_ORDER,
    INSTRUMENTOS_RF,
)

st.title("Posições · Distribuição")

with st.spinner("Carregando dados...", show_time=True):
    st.session_state.df = load_positions()
    st.session_state.df_target_allocations = load_target_allocations(include_limits=False)
    st.session_state.df_portfolio_info = load_portfolio_info()

show_data_freshness("positions", label="Posições", ttl_minutes=60)

df_raw = st.session_state.df
df = df_raw.copy()
df.replace(' ', np.nan, inplace=True)
df.dropna(subset=['Nome Ativo', 'Classificação do Conjunto'], inplace=True)
df = get_emissor_column(df)
df_target_allocations = st.session_state.df_target_allocations
df_portfolio_info = st.session_state.df_portfolio_info

portfolio_meta = (
    df_portfolio_info.dropna(subset=['Name'])
    .drop_duplicates(subset=['Name'])
    .set_index('Name')
)
officer_series = (
    portfolio_meta['Officer Atual']
    if 'Officer Atual' in portfolio_meta.columns
    else pd.Series(dtype=object)
)

portfolios_in_df = set(df['Portfolio'].dropna().unique())
officer_options = sorted({
    str(officer_series[p])
    for p in portfolios_in_df
    if p in officer_series.index and pd.notna(officer_series[p])
})

with st.sidebar:
    selected_officers = st.multiselect(
        "Filtrar por officer",
        options=officer_options,
        default=[],
        help="Deixe vazio para incluir todos os officers.",
    )
    selected_visualization = st.radio(
        "Visualizar por",
        options=['Financeiro (R$)', 'Percentual da Classe (%)', 'Percentual do Total (%)'],
        index=0
    )

if selected_officers:
    allowed_portfolios = {
        p for p in portfolios_in_df
        if p in officer_series.index
        and pd.notna(officer_series[p])
        and str(officer_series[p]) in selected_officers
    }
    df = df[df['Portfolio'].isin(allowed_portfolios)]
    if not df_target_allocations.empty:
        df_target_allocations = df_target_allocations[
            df_target_allocations.index.get_level_values('Portfolio').isin(allowed_portfolios)
        ]

n_portfolios = int(df['Portfolio'].nunique()) if not df.empty else 0
filtro_label = ', '.join(selected_officers) if selected_officers else 'todos os officers'
st.caption(f"{n_portfolios} portfolios · filtro: {filtro_label}")

if df.empty:
    st.warning("Nenhum portfolio encontrado para o filtro selecionado.")
elif df is not None:
    try:
        # Composição Completa
        st.markdown("##### Distribuição por Classe")
        df_positions = df.groupby(
            [pd.Grouper(key='Data Posição', freq='D'), 'Portfolio', 'Nome Ativo',
             'Alias', 'Classificação do Conjunto']
        ).agg(**{
            'Quantidade': ('Quantidade', 'sum'),
            'Valor Unitário': ('Valor Unitário', 'mean'),
            'Saldo': ('Saldo', 'sum')
        })
        df_positions_current = get_latest_date_data(
            df_positions, level='Data Posição', group_level='Portfolio'
        ).reset_index()

        df_total_positions = df.groupby(
            [pd.Grouper(key='Data Posição', freq='D'), 'Portfolio']
        ).agg(**{'Saldo': ('Saldo', 'sum')})
        df_total_positions_current = get_latest_date_data(
            df_total_positions, level='Data Posição', group_level='Portfolio'
        )
        df_total_positions_current = (
            df_total_positions_current.reset_index().set_index('Portfolio')
        )

        df_total_positions_by_asset_class = df.groupby(
            [pd.Grouper(key='Data Posição', freq='D'), 'Portfolio', 'Classificação do Conjunto']
        ).agg(**{'Saldo': ('Saldo', 'sum')})
        df_total_positions_by_asset_class_current = get_latest_date_data(
            df_total_positions_by_asset_class, level='Data Posição', group_level='Portfolio'
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
            df_positions_emissor_devedor, level='Data Posição', group_level='Portfolio'
        ).reset_index().sort_values(by='Saldo', ascending=False)
        df_emissor_devedor_current = df_emissor_devedor_current.pivot(
            index='Emissor Geral', columns='Portfolio', values='Saldo'
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
                index=['Nome Ativo', 'Alias'], columns='Portfolio', values='Saldo'
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

        # Snapshot JSON para IA (canônico em position_service)
        st.markdown("---")
        st.markdown("##### Snapshot para IA")
        snapshot = build_portfolio_snapshot(
            df,
            df_target_allocations,
            active_carteiras_only=False,
        )
        st.download_button(
            label="⬇️ Download snapshot (JSON)",
            data=json.dumps(snapshot, ensure_ascii=False, indent=2),
            file_name=f"snapshot_portfolios_{datetime.now().strftime('%Y-%m-%d')}.json",
            mime="application/json",
        )

    except KeyError as e:
        st.error(f"Erro ao acessar dados: campo {e} não encontrado")
    except IndexError as e:
        st.error(f"Erro ao acessar dados: índice inválido - {e}")
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
