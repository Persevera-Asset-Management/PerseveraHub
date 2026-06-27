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
    get_latest_date_data,
    get_emissor_column,
    ASSET_CLASSES_ORDER,
    INSTRUMENTOS_RF,
)

st.title("Posições · Distribuição")

def build_portfolio_snapshot(
    df_total_positions_current: pd.DataFrame,
    df_total_positions_by_asset_class_current: pd.DataFrame,
    df_target_allocations: pd.DataFrame,
    df_raw: pd.DataFrame,
) -> dict:
    """
    Constrói um snapshot JSON estruturado por portfolio com posições e targets,
    pronto para ser consumido por um modelo de IA para suporte a alocações.

    O snapshot inclui por portfolio:
    - data_referencia: data do snapshot mais recente disponível para o portfolio
    - patrimonio_brl: patrimônio total
    - metricas: indicadores sintéticos (n_ativos, maior posição, concentração, gaps críticos)
    - distribuicao_por_classe: alocação atual por classe de ativo
    - targets_e_gaps: target, posição atual e desvio para todas as classes com target definido
    - concentracao_emissores_rf: concentração de crédito por emissor/devedor (RF)
    - vencimentos_rf: saldo de RF segmentado por prazo de vencimento
    - posicoes_por_classe: posições individuais enriquecidas com instrumento, emissor,
      indexador, taxa e vencimento
    """
    portfolios = sorted(df_raw['Portfolio'].dropna().unique().tolist())

    df_targets = df_target_allocations.reset_index()
    idx = df_targets.groupby(['Portfolio', 'Name'])['Data Documento'].idxmax()
    df_targets_latest = df_targets.loc[idx].reset_index(drop=True)

    hoje = pd.Timestamp(datetime.now().date())

    snapshot = {}

    for portfolio in portfolios:
        patrimonio = float(df_total_positions_current.loc[portfolio, 'Saldo']) \
            if portfolio in df_total_positions_current.index else 0.0

        # Filtra dados brutos do portfolio na sua data mais recente
        df_port = df_raw[df_raw['Portfolio'] == portfolio].copy()
        latest_date = df_port['Data Posição'].max()
        data_referencia = str(latest_date.date()) if pd.notna(latest_date) else None
        df_port = df_port[df_port['Data Posição'] == latest_date].copy()

        df_port['Emissor Geral'] = df_port['Emissor Geral'].fillna('N/A')
        df_port['Nome Ativo Completo'] = df_port['Nome Ativo Completo'].fillna('')
        df_port['Classificação Instrumento'] = df_port['Classificação Instrumento'].fillna('')

        has_indexador = 'Indexador' in df_port.columns

        # === Posições individuais agrupadas por ativo (enriquecidas) ===
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

        # === Distribuição atual por classe ===
        dist_por_classe: dict = {}
        if portfolio in df_total_positions_by_asset_class_current.columns:
            for asset_class in ASSET_CLASSES_ORDER:
                saldo_classe = df_total_positions_by_asset_class_current.get(
                    portfolio, pd.Series()
                ).get(asset_class, np.nan)
                if pd.notna(saldo_classe) and saldo_classe > 0:
                    pct_classe = float(saldo_classe) / patrimonio * 100 if patrimonio else 0.0
                    dist_por_classe[asset_class] = {
                        'saldo_brl': round(float(saldo_classe), 2),
                        'pct_total': round(pct_classe, 4),
                    }

        # === Targets e gaps (todas as classes com target definido) ===
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

        # === Concentração por emissor/devedor (apenas RF) ===
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

        # === Buckets de vencimento (RF) ===
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

        # === Métricas sintéticas ===
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

with st.spinner("Carregando dados...", show_time=True):
    st.session_state.df = load_positions()
    st.session_state.df_target_allocations = load_target_allocations(include_limits=False)

show_data_freshness("positions", label="Posições", ttl_minutes=60)

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

        # Snapshot JSON para IA
        st.markdown("---")
        st.markdown("##### Snapshot para IA")
        snapshot = build_portfolio_snapshot(
            df_total_positions_current=df_total_positions_current,
            df_total_positions_by_asset_class_current=df_total_positions_by_asset_class_current,
            df_target_allocations=df_target_allocations,
            df_raw=df,
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
