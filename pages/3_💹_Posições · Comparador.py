import streamlit as st
import pandas as pd
import numpy as np
import streamlit_highcharts as hct
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication
from utils.chart_helpers import create_chart
from services.position_service import (
    load_positions_for_portfolio,
    get_emissor_column,
    ASSET_CLASSES_ORDER,
    INSTRUMENTOS_RF,
)
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS_ADM

st.set_page_config(
    page_title="Posições · Comparador | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Posições · Comparador")

# =============================================================================
# Sidebar — seleção de portfolio
# =============================================================================
with st.sidebar:
    st.header("Parâmetros")
    selected_portfolio = st.selectbox(
        "Portfolio",
        options=sorted(CODIGOS_CARTEIRAS_ADM.keys()),
        index=None,
        placeholder="Selecione um portfolio...",
    )

if not selected_portfolio:
    st.info("Selecione um portfolio na barra lateral.")
    st.stop()

# =============================================================================
# Carregamento de dados
# =============================================================================
with st.spinner("Carregando histórico do portfolio...", show_time=True):
    df_raw = load_positions_for_portfolio(selected_portfolio)

df = df_raw.copy()
df.replace(' ', np.nan, inplace=True)
df.dropna(subset=['Nome Ativo', 'Classificação do Conjunto'], inplace=True)
df = get_emissor_column(df)

available_dates = sorted(df['Data Posição'].dt.normalize().unique(), reverse=True)
available_dates_fmt = [d.strftime('%Y-%m-%d') for d in available_dates]

if len(available_dates) < 2:
    st.warning("Dados insuficientes: é necessário ao menos duas datas disponíveis para comparação.")
    st.stop()

# =============================================================================
# Sidebar — seleção de datas
# =============================================================================
with st.sidebar:
    st.markdown("---")
    d2_label = st.selectbox("Data Final", options=available_dates_fmt, index=0)
    d1_label = st.selectbox("Data Inicial", options=available_dates_fmt, index=min(1, len(available_dates_fmt) - 1))

if d1_label == d2_label:
    st.warning("Selecione datas diferentes para comparar.")
    st.stop()

d1 = pd.Timestamp(d1_label)
d2 = pd.Timestamp(d2_label)

# Garante que D1 é sempre a data mais antiga
if d1 > d2:
    d1, d2 = d2, d1
    d1_label, d2_label = d2_label, d1_label

df_d1 = df[df['Data Posição'].dt.normalize() == d1].copy()
df_d2 = df[df['Data Posição'].dt.normalize() == d2].copy()

aum_d1 = df_d1['Saldo'].sum()
aum_d2 = df_d2['Saldo'].sum()

try:
    # =========================================================================
    # SEÇÃO 1 — KPIs
    # =========================================================================
    aum_delta = aum_d2 - aum_d1
    aum_delta_pct = (aum_d2 / aum_d1 - 1) * 100 if aum_d1 != 0 else 0
    n_pos_d1 = df_d1['Nome Ativo'].nunique()
    n_pos_d2 = df_d2['Nome Ativo'].nunique()

    st.subheader(f"{selected_portfolio}")
    st.caption(f"{d1_label}  →  {d2_label}")

    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.metric(f"AUM em {d1_label}", f"R$ {aum_d1:,.0f}")
    with kpi_cols[1]:
        st.metric(
            f"AUM em {d2_label}",
            f"R$ {aum_d2:,.0f}",
            delta=f"R$ {aum_delta:+,.0f} ({aum_delta_pct:+.2f}%)",
        )
    with kpi_cols[2]:
        st.metric(f"Nº Posições em {d1_label}", n_pos_d1)
    with kpi_cols[3]:
        st.metric(
            f"Nº Posições em {d2_label}",
            n_pos_d2,
            delta=int(n_pos_d2 - n_pos_d1),
        )

    # =========================================================================
    # SEÇÃO 2 — Alocação por Classe de Ativo
    # =========================================================================
    st.markdown("#### Alocação por Classe de Ativo")

    alloc_d1 = (
        df_d1.groupby('Classificação do Conjunto')['Saldo'].sum()
        .div(aum_d1) * 100
    )
    alloc_d2 = (
        df_d2.groupby('Classificação do Conjunto')['Saldo'].sum()
        .div(aum_d2) * 100
    )

    col_d1 = d1_label
    col_d2 = d2_label
    col_delta = 'Δ (pp)'

    df_alloc = pd.DataFrame({col_d1: alloc_d1, col_d2: alloc_d2})
    df_alloc = df_alloc.reindex([c for c in ASSET_CLASSES_ORDER if c in df_alloc.index])
    df_alloc[col_delta] = df_alloc[col_d2].fillna(0) - df_alloc[col_d1].fillna(0)
    df_alloc = df_alloc.fillna(0)

    alloc_cols = st.columns([1, 2])
    with alloc_cols[0]:
        st.dataframe(
            style_table(
                df_alloc,
                percent_cols=[col_d1, col_d2],
                numeric_cols_format_as_float=[col_delta],
                color_negative_positive_cols=[col_delta],
            ),
            use_container_width=True,
        )

    with alloc_cols[1]:
        chart_data = df_alloc[[col_d1, col_d2]].copy()
        chart_alloc = create_chart(
            data=chart_data,
            columns=[col_d1, col_d2],
            names=[d1_label, d2_label],
            chart_type='column',
            title='Alocação por Classe (%)',
            y_axis_title='%',
        )
        hct.streamlit_highcharts(chart_alloc)

    # =========================================================================
    # SEÇÃO 3 — Movimentações
    # =========================================================================
    st.markdown("#### Movimentações")

    assets_d1 = set(df_d1['Nome Ativo'].dropna().unique())
    assets_d2 = set(df_d2['Nome Ativo'].dropna().unique())
    added = assets_d2 - assets_d1
    removed = assets_d1 - assets_d2

    pos_d1 = df_d1.groupby('Nome Ativo')['Saldo'].sum()
    pos_d2 = df_d2.groupby('Nome Ativo')['Saldo'].sum()

    df_common = pd.DataFrame({'D1 (R$)': pos_d1, 'D2 (R$)': pos_d2}).dropna()
    df_common['Δ (R$)'] = df_common['D2 (R$)'] - df_common['D1 (R$)']
    df_common['Δ (%)'] = (df_common['D2 (R$)'] / df_common['D1 (R$)'] - 1) * 100

    threshold_abs = max(aum_d1, aum_d2) * 0.005
    df_changed = df_common[df_common['Δ (R$)'].abs() > threshold_abs].sort_values('Δ (R$)')

    alias_map = (
        pd.concat([
            df_d1[['Nome Ativo', 'Nome Ativo Completo']].drop_duplicates(),
            df_d2[['Nome Ativo', 'Nome Ativo Completo']].drop_duplicates(),
        ])
        .drop_duplicates('Nome Ativo')
        .set_index('Nome Ativo')['Nome Ativo Completo']
    )

    mv_cols = st.columns(3)

    with mv_cols[0]:
        st.markdown(f"**Adicionadas** ({len(added)})")
        if added:
            df_added = (
                df_d2[df_d2['Nome Ativo'].isin(added)]
                .groupby(['Nome Ativo', 'Nome Ativo Completo', 'Classificação do Conjunto'])['Saldo']
                .sum()
                .reset_index()
                .sort_values('Saldo', ascending=False)
            )
            df_added['% Portfolio'] = df_added['Saldo'] / aum_d2 * 100
            st.dataframe(
                style_table(
                    df_added.set_index(['Nome Ativo', 'Nome Ativo Completo']),
                    numeric_cols_format_as_float=['Saldo'],
                    percent_cols=['% Portfolio'],
                ),
                use_container_width=True,
            )
        else:
            st.info("Nenhuma posição adicionada.")

    with mv_cols[1]:
        st.markdown(f"**Removidas** ({len(removed)})")
        if removed:
            df_removed = (
                df_d1[df_d1['Nome Ativo'].isin(removed)]
                .groupby(['Nome Ativo', 'Nome Ativo Completo', 'Classificação do Conjunto'])['Saldo']
                .sum()
                .reset_index()
                .sort_values('Saldo', ascending=False)
            )
            df_removed['% Portfolio'] = df_removed['Saldo'] / aum_d1 * 100
            st.dataframe(
                style_table(
                    df_removed.set_index(['Nome Ativo', 'Nome Ativo Completo']),
                    numeric_cols_format_as_float=['Saldo'],
                    percent_cols=['% Portfolio'],
                ),
                use_container_width=True,
            )
        else:
            st.info("Nenhuma posição removida.")

    with mv_cols[2]:
        st.markdown(f"**Alteradas significativamente** ({len(df_changed)})")
        if not df_changed.empty:
            df_changed_display = df_changed.copy().reset_index()
            df_changed_display.insert(1, 'Nome Ativo Completo', df_changed_display['Nome Ativo'].map(alias_map))
            df_changed_display = df_changed_display.set_index(['Nome Ativo', 'Nome Ativo Completo'])
            st.dataframe(
                style_table(
                    df_changed_display,
                    numeric_cols_format_as_float=['D1 (R$)', 'D2 (R$)', 'Δ (R$)'],
                    percent_cols=['Δ (%)'],
                    color_negative_positive_cols=['Δ (R$)', 'Δ (%)'],
                ),
                use_container_width=True,
            )
        else:
            st.info("Nenhuma alteração significativa (> 0,5% do portfolio).")

    # =========================================================================
    # SEÇÃO 4 — Tabela completa de posições
    # =========================================================================
    with st.expander("Posições Completas", expanded=False):
        df_d1_full = (
            df_d1.groupby(['Nome Ativo', 'Nome Ativo Completo', 'Classificação do Conjunto'])['Saldo']
            .sum()
            .reset_index()
        )
        df_d2_full = (
            df_d2.groupby(['Nome Ativo', 'Nome Ativo Completo', 'Classificação do Conjunto'])['Saldo']
            .sum()
            .reset_index()
        )

        df_full = pd.merge(
            df_d1_full.rename(columns={'Saldo': 'D1 (R$)'}),
            df_d2_full.rename(columns={'Saldo': 'D2 (R$)'}),
            on=['Nome Ativo', 'Nome Ativo Completo', 'Classificação do Conjunto'],
            how='outer',
        ).fillna(0)

        df_full['D1 (%)'] = df_full['D1 (R$)'] / aum_d1 * 100
        df_full['D2 (%)'] = df_full['D2 (R$)'] / aum_d2 * 100
        df_full['Δ (R$)'] = df_full['D2 (R$)'] - df_full['D1 (R$)']
        df_full['Δ (pp)'] = df_full['D2 (%)'] - df_full['D1 (%)']

        df_full = df_full.sort_values('D2 (R$)', ascending=False)
        df_full = df_full.set_index(['Nome Ativo', 'Nome Ativo Completo', 'Classificação do Conjunto'])

        st.dataframe(
            style_table(
                df_full,
                numeric_cols_format_as_float=['D1 (R$)', 'D2 (R$)', 'Δ (R$)'],
                percent_cols=['D1 (%)', 'D2 (%)', 'Δ (pp)'],
                color_negative_positive_cols=['Δ (R$)', 'Δ (pp)'],
            ),
            use_container_width=True,
        )

    # =========================================================================
    # SEÇÃO 5 — Emissores RF (condicional)
    # =========================================================================
    df_rf_d1 = df_d1[df_d1['Classificação Instrumento'].isin(INSTRUMENTOS_RF)]
    df_rf_d2 = df_d2[df_d2['Classificação Instrumento'].isin(INSTRUMENTOS_RF)]

    if len(df_rf_d1) > 0 or len(df_rf_d2) > 0:
        st.markdown("#### Emissores de Renda Fixa")

        em_d1 = (
            df_rf_d1.groupby('Emissor')['Saldo'].sum().div(aum_d1) * 100
            if len(df_rf_d1) > 0 else pd.Series(dtype=float)
        )
        em_d2 = (
            df_rf_d2.groupby('Emissor')['Saldo'].sum().div(aum_d2) * 100
            if len(df_rf_d2) > 0 else pd.Series(dtype=float)
        )

        df_emitters = pd.DataFrame({col_d1: em_d1, col_d2: em_d2}).fillna(0)
        df_emitters[col_delta] = df_emitters[col_d2] - df_emitters[col_d1]
        df_emitters = df_emitters.sort_values(col_d2, ascending=False)

        st.dataframe(
            style_table(
                df_emitters,
                percent_cols=[col_d1, col_d2],
                numeric_cols_format_as_float=[col_delta],
                color_negative_positive_cols=[col_delta],
            ),
            use_container_width=True,
        )

except KeyError as e:
    st.error(f"Erro ao acessar dados: campo {e} não encontrado.")
except IndexError as e:
    st.error(f"Erro ao acessar dados: índice inválido — {e}")
except Exception as e:
    st.error(f"Ocorreu um erro ao carregar os dados: {e}")
