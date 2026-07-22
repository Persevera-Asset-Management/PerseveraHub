import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime

from utils.chart_helpers import create_chart, render_chart
from utils.ui import show_data_freshness
from utils.table import style_table
from configs.pages.carteiras_administradas import CODIGOS_CARTEIRAS_ADM

from services.position_service import (
    load_positions,
    load_target_allocations,
    load_accounts,
    load_instruments_fgc,
    load_issuers,
    get_latest_date_data,
    get_emissor_column,
    INSTRUMENTOS_RF,
    ASSET_CLASSES_ORDER,
)

EMISSOR_STATUS_ALERTAS = ("Não Aprovável", "Reprovado")

st.title("Controle de Posições")

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_carteiras = st.multiselect(
        "Carteiras selecionadas",
        options=CODIGOS_CARTEIRAS_ADM,
        default=None,
        placeholder="Selecione uma ou mais carteiras..."
    )

def load_data(carteiras):
    """Carrega todos os dados necessários para a página."""
    with st.spinner("Carregando dados...", show_time=True):
        df_positions = load_positions()
        st.session_state.df_positions = df_positions
        st.session_state.instruments_fgc = load_instruments_fgc()
        st.session_state.df_issuers = load_issuers()
        st.session_state.df_target_allocations = load_target_allocations(include_limits=True)
        st.session_state.df_accounts = load_accounts()
        st.session_state.df = df_positions[df_positions['Portfolio'].isin(carteiras)]

if selected_carteiras:
    load_data(selected_carteiras)
    show_data_freshness("positions", label="Posições", ttl_minutes=60)

    df = st.session_state.df
    df_target_allocations = st.session_state.df_target_allocations
    df_accounts = st.session_state.df_accounts
    instruments_fgc = st.session_state.instruments_fgc
    df_issuers = st.session_state.df_issuers
    is_single_carteira = len(selected_carteiras) == 1

    try:
        if is_single_carteira:
            st.subheader(selected_carteiras[0])
        else:
            st.subheader("Consolidado: " + ", ".join(sorted(selected_carteiras)))

        # Informações Gerais
        account_info = df_accounts[df_accounts['Portfolio'].isin(selected_carteiras)]
        account_lines = []
        for _portfolio in sorted(selected_carteiras):
            info = account_info[account_info['Portfolio'] == _portfolio]
            if len(info) > 0:
                account_lines.append(
                    f"{info['Nome Completo'].values[0]} ({_portfolio})\n\n"
                    f"Conta(s): {', '.join(info['Nr Conta'].values)}\n"
                    f"Custodiante(s): {', '.join(info['Custodiante'].values)}"
                )
        st.code("\n\n---\n\n".join(account_lines), language='markdown')

        # Composição Completa
        df_portfolio_positions = df.groupby(
            [pd.Grouper(key='Data Posição', freq='D'), 'Nome Ativo', 'Alias', 'Classificação do Conjunto']
        ).agg(**{
            'Quantidade': ('Quantidade', 'sum'),
            'Valor Unitário': ('Valor Unitário', 'mean'),
            'Saldo': ('Saldo', 'sum')
        })

        df_portfolio_positions_current = get_latest_date_data(df_portfolio_positions).copy()
        df_portfolio_positions_current['%'] = (
            df_portfolio_positions_current['Saldo'] / df_portfolio_positions_current['Saldo'].sum() * 100
        )

        with st.expander("Composição Completa", expanded=False):
            st.dataframe(
                style_table(
                    df_portfolio_positions_current,
                    numeric_cols_format_as_float=['Quantidade', 'Valor Unitário', 'Saldo', '%'],
                )
            )

        # Política de Investimentos
        if not is_single_carteira:
            st.info("Política disponível apenas para carteira única.")
        else:
            df_policy_investments_current = pd.DataFrame()
            if selected_carteiras[0] in df_target_allocations.index:
                df_policy_investments_current = (
                    df_target_allocations.loc[selected_carteiras[0]].dropna(subset=['PL Min', 'PL Max'])
                )

            if df_policy_investments_current.empty:
                st.warning("Política de Investimentos não cadastrada")
            else:
                df_policy_investments_current = get_latest_date_data(df_policy_investments_current)
                df_policy_investments_current = df_policy_investments_current.mul(100)
                df_policy_investments_current = df_policy_investments_current.reindex(ASSET_CLASSES_ORDER)

                with st.expander("Política de Investimentos", expanded=False):
                    st.dataframe(
                        style_table(
                            df_policy_investments_current.drop(columns='Target'),
                            percent_cols=['PL Min', 'PL Max', 'Target'],
                        )
                    )

        st.markdown("Saldo Total: **R$ {0:,.2f}**".format(df_portfolio_positions_current['Saldo'].sum()))
        st.markdown(f"Data da Posição: `{df['Data Posição'].max().date()}`")

        # =========================================================================
        # SEÇÃO 1 — Indicadores Chave
        # =========================================================================
        if is_single_carteira:
            classificacao_idx = df_portfolio_positions_current.index.get_level_values('Classificação do Conjunto')
            total_saldo = df_portfolio_positions_current['Saldo'].sum()

            saldo_caixa = df_portfolio_positions_current[classificacao_idx == 'Caixa e Equivalentes']['Saldo'].sum()
            pct_caixa = saldo_caixa / total_saldo * 100 if total_saldo > 0 else 0

            df_emissores_rf = df[df['Classificação Instrumento'].isin(INSTRUMENTOS_RF)]
            df_emissores_total_kpi = get_emissor_column(df).groupby([pd.Grouper(key='Data Posição', freq='D'), 'Emissor'])["Saldo"].sum()
            df_emissores_rf_kpi = get_emissor_column(df_emissores_rf).groupby([pd.Grouper(key='Data Posição', freq='D'), 'Emissor'])["Saldo"].sum()
            total_emissores = len(get_latest_date_data(df_emissores_total_kpi))
            total_emissores_rf = len(get_latest_date_data(df_emissores_rf_kpi))

            df_ex_caixa = df_portfolio_positions_current[classificacao_idx != 'Caixa e Equivalentes']
            if not df_ex_caixa.empty:
                maior_posicao = df_ex_caixa['Saldo'].max(), df_ex_caixa['%'].max()
                maior_posicao_alias = df_ex_caixa['Saldo'].idxmax()[1]  # level 1 = 'Alias'
            else:
                maior_posicao = (0.0, 0.0)
                maior_posicao_alias = ""

            df_rf_posicoes = df_emissores_rf.groupby(
                [pd.Grouper(key='Data Posição', freq='D'), 'Nome Ativo', 'Alias', 'Classificação do Conjunto']
            ).agg(**{'Saldo': ('Saldo', 'sum')})
            df_rf_posicoes_current = get_latest_date_data(df_rf_posicoes).reset_index()
            df_rf_posicoes_current_ex_caixa = df_rf_posicoes_current[df_rf_posicoes_current['Classificação do Conjunto'] != 'Caixa e Equivalentes']
            df_rf_posicoes_current_ex_caixa = df_rf_posicoes_current_ex_caixa.set_index(['Nome Ativo', 'Alias', 'Classificação do Conjunto'])
            if not df_rf_posicoes_current_ex_caixa.empty:
                maior_posicao_rf = df_rf_posicoes_current_ex_caixa['Saldo'].max()
                maior_posicao_rf_pct = maior_posicao_rf / total_saldo * 100 if total_saldo > 0 else 0
                maior_posicao_rf_alias = df_rf_posicoes_current_ex_caixa['Saldo'].idxmax()[1]  # level 1 = 'Alias'
            else:
                maior_posicao_rf = 0.0
                maior_posicao_rf_pct = 0.0
                maior_posicao_rf_alias = ""

            kpi_cols = st.columns(4)
            with kpi_cols[0]:
                st.metric(
                    "Posição em Liquidez", f"{pct_caixa:.1f}%", height="stretch",
                    delta=f"R$ {saldo_caixa:,.2f}",
                    delta_color="off",
                    delta_arrow="off",
                )
            with kpi_cols[1]:
                st.metric(
                    "Total de Emissores", total_emissores, height="stretch",
                    delta=f"{total_emissores_rf} de Renda Fixa",
                    delta_color="off",
                    delta_arrow="off",    
                )
            with kpi_cols[2]:
                st.metric(
                    f"Maior Posição (ex-Caixa): **{maior_posicao_alias}**",
                    f"{maior_posicao[1]:,.1f}%",
                    delta=f"R$ {maior_posicao[0]:,.2f}",
                    delta_color="off",
                    delta_arrow="off",
                )
            with kpi_cols[3]:
                st.metric(
                    f"Maior Posição RF  (ex-Caixa): **{maior_posicao_rf_alias}**",
                    f"{maior_posicao_rf_pct:,.1f}%",
                    delta=f"R$ {maior_posicao_rf:,.2f}",
                    delta_color="off",
                    delta_arrow="off",
                )

        # =========================================================================
        # SEÇÃO 2 — Gráficos
        # =========================================================================
        tabs = st.tabs(["Alocação Atual", "Alocação Hierárquica", "Emissores", "Instrumentos", "Custodiantes", "Vencimentos", "Monitor de FGC", "Alertas"])

        with tabs[0]: # Alocação Atual

            cols = st.columns(2)
            with cols[0]:
                df_portfolio_composition = df.groupby(
                    [pd.Grouper(key='Data Posição', freq='D'), 'Classificação do Conjunto']
                ).agg(**{'Saldo': ('Saldo', 'sum')})
                df_portfolio_composition_current = get_latest_date_data(df_portfolio_composition)
                df_portfolio_composition_current = df_portfolio_composition_current.reindex(ASSET_CLASSES_ORDER).dropna()

                chart_portfolio_composition = create_chart(
                    data=df_portfolio_composition_current,
                    columns=['Saldo'],
                    names=['Saldo'],
                    chart_type='donut',
                    title="Alocação Atual",
                    y_axis_title="%",
                )
                hct.streamlit_highcharts(chart_portfolio_composition)

                df_portfolio_composition_sub = df.groupby(
                    [pd.Grouper(key='Data Posição', freq='D'), 'Classificação do Sub-Conjunto']
                ).agg(**{'Saldo': ('Saldo', 'sum')})
                df_portfolio_composition_current_sub = get_latest_date_data(df_portfolio_composition_sub)
                df_portfolio_composition_current = df_portfolio_composition_current.reindex(ASSET_CLASSES_ORDER).dropna()

                chart_portfolio_composition = create_chart(
                    data=df_portfolio_composition_current_sub,
                    columns=['Saldo'],
                    names=['Saldo'],
                    chart_type='donut',
                    title="Alocação Atual - Sub-Conjunto",
                    y_axis_title="%",
                )
                hct.streamlit_highcharts(chart_portfolio_composition)

            
            with cols[1]:
                if not is_single_carteira:
                    st.info("Política disponível apenas para carteira única.")
                else:
                    df_target_allocations_current = pd.DataFrame()
                    if selected_carteiras[0] in df_target_allocations.index:
                        df_target_allocations_current = (
                            df_target_allocations.loc[selected_carteiras[0]].dropna(subset=['Target'])
                        )

                    if df_target_allocations_current.empty:
                        st.warning("Alocação alvo não cadastrada")
                    else:
                        df_target_allocations_current = get_latest_date_data(df_target_allocations_current)
                        df_target_allocations_current = df_target_allocations_current * df_portfolio_positions_current['Saldo'].sum()
                        df_target_allocations_current = df_target_allocations_current.reindex(ASSET_CLASSES_ORDER)

                        chart_portfolio_composition_target = create_chart(
                            data=df_target_allocations_current,
                            columns=['Target'],
                            names=['Target'],
                            chart_type='donut',
                            title="Alocação Alvo",
                            y_axis_title="%",
                        )
                        hct.streamlit_highcharts(chart_portfolio_composition_target)

        with tabs[1]: # Alocação Hierárquica
            df_inner_chart = df_portfolio_composition_current.reset_index()
            df_outer_chart = df_portfolio_positions_current.reset_index()
            category_order = {cat: i for i, cat in enumerate(df_inner_chart['Classificação do Conjunto'])}
            df_outer_chart['_cat_order'] = df_outer_chart['Classificação do Conjunto'].map(category_order)
            df_outer_chart = df_outer_chart.sort_values(
                by=['_cat_order', 'Saldo'],
                ascending=[True, False]  # Categoria na ordem, Saldo decrescente
            ).drop(columns=['_cat_order'])

            options_nested = create_chart(
                data=df_outer_chart,
                columns='Saldo',
                x_column='Alias',  # Ativos individuais no anel externo
                chart_type='nested_pie',
                title='Alocação Hierárquica',
                inner_data=df_inner_chart,
                inner_y_column='Saldo',
                inner_x_column='Classificação do Conjunto',  # Classes no anel interno
                inner_series_name='Classes',
                names='Ativos',
                inner_size="55%",
                outer_inner_size="55%",
                center_hole_size="30%",
                outer_parent_column='Classificação do Conjunto',  # Liga anel externo ao interno
                enable_fullscreen_on_dblclick=True,
            )

            render_chart(options_nested)

        with tabs[2]: # Emissores
            df_emissor = get_emissor_column(df)
            df_portfolio_positions_emissores = df_emissor.groupby(
                [pd.Grouper(key='Data Posição', freq='D'), 'Emissor']
            ).agg(**{'Saldo': ('Saldo', 'sum')})
            df_portfolio_positions_emissores_current = get_latest_date_data(df_portfolio_positions_emissores)
            df_portfolio_positions_emissores_current = df_portfolio_positions_emissores_current.sort_values(
                by='Saldo', ascending=False
            )

            chart_portfolio_positions_emissores = create_chart(
                data=df_portfolio_positions_emissores_current,
                columns=['Saldo'],
                names=['Emissor'],
                chart_type='donut',
                title="Emissores",
                y_axis_title="%",
            )
            hct.streamlit_highcharts(chart_portfolio_positions_emissores)

        with tabs[3]: # Instrumentos
            df_instrument = df.copy()
            df_instrument['Instrumento'] = df_instrument['Classificação Instrumento']
            df_portfolio_positions_instruments = df_instrument.groupby(
                [pd.Grouper(key='Data Posição', freq='D'), 'Instrumento']
            ).agg(**{'Saldo': ('Saldo', 'sum')})
            df_portfolio_positions_instruments_current = get_latest_date_data(df_portfolio_positions_instruments)
            df_portfolio_positions_instruments_current = df_portfolio_positions_instruments_current.sort_values(
                by='Saldo', ascending=False
            )

            chart_portfolio_positions_instruments = create_chart(
                data=df_portfolio_positions_instruments_current,
                columns=['Saldo'],
                names=['Instrumento'],
                chart_type='donut',
                title="Instrumentos",
                y_axis_title="%",
            )
            hct.streamlit_highcharts(chart_portfolio_positions_instruments)

        with tabs[4]: # Custodiantes
            df_custodiante = df.copy()
            df_portfolio_positions_custodiante = df_custodiante.groupby(
                [pd.Grouper(key='Data Posição', freq='D'), 'Custodiante Acronimo']
            ).agg(**{'Saldo': ('Saldo', 'sum')})
            df_portfolio_positions_custodiante_current = get_latest_date_data(df_portfolio_positions_custodiante)
            df_portfolio_positions_custodiante_current = df_portfolio_positions_custodiante_current.sort_values(
                by='Saldo', ascending=False
            )

            chart_portfolio_positions_custodiante = create_chart(
                data=df_portfolio_positions_custodiante_current,
                columns=['Saldo'],
                names=['Custodiante'],
                chart_type='donut',
                title="Custodiantes",
                y_axis_title="%",
            )
            hct.streamlit_highcharts(chart_portfolio_positions_custodiante)

        with tabs[5]: # Vencimentos
            cols = st.columns(2)
            with cols[0]:
                df_data_vencimento_rf = df.copy()
                df_data_vencimento_rf = df_data_vencimento_rf.groupby(
                    [pd.Grouper(key='Data Posição', freq='D'), 'Nome Ativo', 'Alias',
                    'Classificação do Conjunto', 'Classificação Instrumento', 'Data Vencimento', 'Nome Emissor']
                ).agg(**{
                    'Quantidade': ('Quantidade', 'sum'),
                    'Valor Unitário': ('Valor Unitário', 'mean'),
                    'Saldo': ('Saldo', 'sum')
                })
                df_data_vencimento_rf_current = get_latest_date_data(df_data_vencimento_rf).copy()
                df_data_vencimento_rf_current = df_data_vencimento_rf_current.reset_index().set_index(['Nome Ativo'])
                df_data_vencimento_rf_current['Data Vencimento'] = pd.to_datetime(df_data_vencimento_rf_current['Data Vencimento'])
                df_data_vencimento_rf_current = df_data_vencimento_rf_current.sort_values(by='Data Vencimento', ascending=True)
                df_data_vencimento_rf_current = df_data_vencimento_rf_current[df_data_vencimento_rf_current['Saldo'] > 0]
                df_data_vencimento_rf_current['Anos para Vencimento'] = np.busday_count(
                    datetime.now().date(),
                    df_data_vencimento_rf_current['Data Vencimento'].values.astype('datetime64[D]')
                ) / 252

                st.dataframe(
                    style_table(
                        df_data_vencimento_rf_current[[
                            'Alias', 'Classificação do Conjunto', 'Classificação Instrumento',
                            'Data Vencimento', 'Quantidade', 'Valor Unitário', 'Saldo'
                        ]],
                        date_cols=['Data Vencimento'],
                        numeric_cols_format_as_float=['Valor Unitário', 'Saldo'],
                        numeric_cols_format_as_int=['Quantidade'],
                    )
                )

            with cols[1]:
                # Distribuição por vencimento
                maturity_bins = [0, 1, 2, 3, 5, 7, 10, np.inf]
                maturity_labels = ['0-1 ano', '1-2 anos', '2-3 anos', '3-5 anos', '5-7 anos', '7-10 anos', '> 10 anos']

                def build_maturity_histogram(df_filtered, stack_by):
                    df_hist = df_filtered.copy()
                    df_hist['Faixa de Vencimento'] = pd.cut(
                        df_hist['Anos para Vencimento'],
                        bins=maturity_bins,
                        labels=maturity_labels,
                        right=False
                    )
                    df_pivot = (
                        df_hist.groupby(['Faixa de Vencimento', stack_by], observed=True)['Saldo']
                        .sum()
                        .unstack(level=stack_by)
                        .reindex(maturity_labels)
                        .fillna(0)
                        .reset_index()
                    )
                    return df_pivot

                sub_tabs = st.tabs(["Total", "Renda Fixa Pós-Fixada", "Renda Fixa Atrelada à Inflação", "Renda Fixa Pré-Fixada"])
                tab_filters = [None, "Renda Fixa Pós-Fixada", "Renda Fixa Atrelada à Inflação", "Renda Fixa Pré-Fixada"]
                tab_stack_by = ['Classificação do Conjunto', 'Alias', 'Alias', 'Alias']

                for sub_tab, filter_val, stack_by in zip(sub_tabs, tab_filters, tab_stack_by):
                    with sub_tab:
                        df_tab = df_data_vencimento_rf_current.copy()
                        if filter_val:
                            df_tab = df_tab[df_tab['Classificação do Conjunto'] == filter_val]
                        if len(df_tab) > 0:
                            df_hist = build_maturity_histogram(df_tab, stack_by)
                            series_cols = [c for c in df_hist.columns if c != 'Faixa de Vencimento']
                            chart_hist = create_chart(
                                data=df_hist,
                                chart_type='bar',
                                title="Distribuição por Prazo de Vencimento",
                                columns=series_cols,
                                names=series_cols,
                                x_column='Faixa de Vencimento',
                                y_axis_title="Saldo (R$)",
                                stacking='normal',
                                show_legend=False,
                            )
                            hct.streamlit_highcharts(chart_hist)
                        else:
                            st.info("Sem dados para este filtro")                

        with tabs[6]: # Monitor de FGC
            df_data_vencimento_rf_current_fgc = df_data_vencimento_rf_current[np.isin(df_data_vencimento_rf_current['Classificação Instrumento'], instruments_fgc)]
            
            cols = st.columns(2)

            if len(df_data_vencimento_rf_current_fgc) > 0:
                with cols[0]:
                    st.dataframe(
                        style_table(
                            df_data_vencimento_rf_current_fgc[[
                                'Alias', 'Classificação do Conjunto', 'Classificação Instrumento',
                                'Data Vencimento', 'Quantidade', 'Valor Unitário', 'Saldo'
                            ]],
                            date_cols=['Data Vencimento'],
                            numeric_cols_format_as_float=['Valor Unitário', 'Saldo'],
                            numeric_cols_format_as_int=['Quantidade'],
                        )
                    )
                with cols[1]:
                    df_fgc_total = df_data_vencimento_rf_current_fgc.groupby(
                        ['Nome Emissor']
                    ).agg(**{'Saldo': ('Saldo', 'sum')})

                    chart_portfolio_positions_fgc = create_chart(
                        data=df_fgc_total.sort_values(by='Saldo', ascending=False),
                        columns=['Saldo'],
                        names=['Nome Emissor'],
                        chart_type='column',
                        title="Cobertura do FGC",
                        y_axis_title="Total (R$)",
                        x_axis_title="Banco Emissor",
                        show_legend=False,
                        horizontal_line={
                            "value": 250000,
                            "color": "#FF0000",
                            "width": 2,
                            "label": {"text": "Limite por Emissor", "align": "left"}
                        }
                    )
                    hct.streamlit_highcharts(chart_portfolio_positions_fgc)
            else:
                st.info("Cliente não possui ativos cobertos pelo FGC")

        with tabs[7]: # Alertas
            df_alertas_rf = df[df['Classificação Instrumento'].isin(INSTRUMENTOS_RF)].copy()
            df_alertas_rf = get_emissor_column(df_alertas_rf)

            df_alertas_posicoes = df_alertas_rf.groupby(
                [
                    pd.Grouper(key='Data Posição', freq='D'),
                    'Nome Ativo', 'Alias', 'Classificação do Conjunto',
                    'Classificação Instrumento', 'Data Vencimento', 'Emissor',
                ]
            ).agg(**{
                'Quantidade': ('Quantidade', 'sum'),
                'Valor Unitário': ('Valor Unitário', 'mean'),
                'Saldo': ('Saldo', 'sum'),
            })
            df_alertas_current = get_latest_date_data(df_alertas_posicoes).reset_index()
            df_alertas_current = df_alertas_current[df_alertas_current['Saldo'] > 0].copy()

            if df_alertas_current.empty:
                st.info("Cliente não possui posições de Renda Fixa para monitorar.")
            else:
                df_issuers_status = df_issuers[['Nome Emissor', 'Status do Emissor']].drop_duplicates(
                    subset=['Nome Emissor'],
                    keep='first',
                )
                df_alertas_current = df_alertas_current.merge(
                    df_issuers_status,
                    left_on='Emissor',
                    right_on='Nome Emissor',
                    how='left',
                )
                df_alertas_current['Status do Emissor'] = (
                    df_alertas_current['Status do Emissor'].fillna('Sem Classificação')
                )
                df_alertas_current['Em Alerta'] = df_alertas_current['Status do Emissor'].isin(
                    EMISSOR_STATUS_ALERTAS
                )

                total_saldo_carteira = df_portfolio_positions_current['Saldo'].sum()
                df_alertas_current['% PL'] = (
                    df_alertas_current['Saldo'] / total_saldo_carteira * 100
                    if total_saldo_carteira > 0 else 0
                )

                df_em_alerta = df_alertas_current[df_alertas_current['Em Alerta']].copy()
                df_em_alerta = df_em_alerta.sort_values(by='Saldo', ascending=False)

                saldo_alerta = df_em_alerta['Saldo'].sum()
                pct_alerta = (
                    saldo_alerta / total_saldo_carteira * 100 if total_saldo_carteira > 0 else 0
                )
                emissores_alerta = df_em_alerta['Emissor'].nunique()

                if df_em_alerta.empty:
                    st.success(
                        "Nenhuma posição de Renda Fixa sob alerta."
                    )
                else:
                    cols = st.columns([1, 4])
                    with cols[0]:

                        st.metric("Posições sob alerta", value=len(df_em_alerta), delta=f"{emissores_alerta} emissores", delta_color="off", delta_arrow="off")
                        st.metric("Saldo sob alerta", f"R$ {saldo_alerta:,.2f}", delta=f"{pct_alerta:.1f}% do PL", delta_color="off", delta_arrow="off")

                    alert_cols = [
                        'Nome Ativo', 'Alias', 'Classificação Instrumento', 'Emissor',
                        'Status do Emissor', 'Data Vencimento', 'Saldo', '% PL',
                    ]

                    with cols[1]:
                        st.dataframe(
                            style_table(
                                df_em_alerta[alert_cols].set_index('Nome Ativo'),
                                date_cols=['Data Vencimento'],
                                numeric_cols_format_as_float=['Valor Unitário', 'Saldo', '% PL'],
                                numeric_cols_format_as_int=['Quantidade'],
                                highlight_row_by_column='Status do Emissor',
                                highlight_row_if_value_equals='Reprovado',
                                highlight_color='#f8d7da',
                                left_align_cols=['Alias', 'Emissor', 'Status do Emissor'],
                            ),
                            hide_index=False,
                        )

    except KeyError as e:
        st.error(f"Erro ao acessar dados: campo {e} não encontrado")
    except IndexError as e:
        st.error(f"Erro ao acessar dados: índice inválido - {e}")
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
