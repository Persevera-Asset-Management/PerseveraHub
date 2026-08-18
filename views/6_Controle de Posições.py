import streamlit as st
import streamlit_highcharts as hct

import pandas as pd
import numpy as np
import traceback
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
    load_assets,
    load_scheduled_events,
    get_latest_date_data,
    get_emissor_column,
    enrich_dataframe_with_duration,
    weighted_average_duration,
    weighted_average_duration_by_category,
    build_cash_flow_schedule,
    aggregate_cash_flow_by_month,
    scheduled_events_coverage,
    RF_DURATION_CATEGORIES,
    RF_DURATION_CATEGORY_LABELS,
    INSTRUMENTOS_RF,
    INSTRUMENTOS_EVENTOS_PROGRAMADOS,
    ASSET_CLASSES_ORDER,
)
from services.external_positions_service import (
    MATCH_AMBIGUOUS,
    MATCH_MATCHED,
    MATCH_UNMATCHED,
    enrich_external_positions,
    match_external_positions,
    match_summary,
    parse_external_positions_file,
    template_csv_bytes,
)

EMISSOR_STATUS_ALERTAS = ("Não Aprovável", "Reprovado")
ORIGEM_GESTAO = "Sob gestão (Fibery)"
ORIGEM_EXTERNA = "Carteira externa"

st.title("Controle de Posições")

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    origem_carteira = st.radio(
        "Origem da carteira",
        options=[ORIGEM_GESTAO, ORIGEM_EXTERNA],
        index=0,
    )
    is_external = origem_carteira == ORIGEM_EXTERNA

    selected_carteiras = []
    uploaded_external = None
    external_label = "EXTERNA"
    external_date = datetime.now().date()
    allow_partial_match = False

    if is_external:
        external_label = st.text_input(
            "Nome da carteira",
            value="EXTERNA",
            placeholder="Ex.: Prospect Silva",
        ).strip() or "EXTERNA"
        external_date = st.date_input(
            "Data da posição",
            value=datetime.now().date(),
            format="DD/MM/YYYY",
        )
        uploaded_external = st.file_uploader(
            "Arquivo de posições (CSV ou Excel)",
            type=["csv", "xlsx", "xls"],
            help="Obrigatório: Ativo, Saldo. Opcionais: Quantidade, Valor Unitário, Data Posição, Custodiante, Portfolio.",
        )
        st.download_button(
            "Baixar template",
            data=template_csv_bytes(),
            file_name="template_carteira_externa.csv",
            mime="text/csv",
            width="stretch",
        )
        allow_partial_match = st.checkbox(
            "Analisar apenas ativos com match",
            value=False,
            help="Se marcado, ignora unmatched/ambiguous e segue só com os matched.",
        )
    else:
        selected_carteiras = st.multiselect(
            "Carteiras selecionadas",
            options=CODIGOS_CARTEIRAS_ADM,
            default=None,
            placeholder="Selecione uma ou mais carteiras...",
        )


def _scheduled_events_start_date():
    """Início do mês corrente: janela mínima do fluxo, com cache estável no mês."""
    return datetime.now().replace(day=1).strftime('%Y-%m-%d')


def load_data(carteiras):
    """Carrega todos os dados necessários para a página (modo sob gestão)."""
    with st.spinner("Carregando dados...", show_time=True):
        df_positions = load_positions()
        st.session_state.df_positions = df_positions
        st.session_state.instruments_fgc = load_instruments_fgc()
        st.session_state.df_issuers = load_issuers()
        st.session_state.df_target_allocations = load_target_allocations(include_limits=True)
        st.session_state.df_accounts = load_accounts()
        st.session_state.df_scheduled_events = load_scheduled_events(
            start_date=_scheduled_events_start_date()
        )
        st.session_state.df = df_positions[df_positions['Portfolio'].isin(carteiras)]


def load_external_reference_data():
    """Carrega taxonomia / FGC / emissores para enriquecer carteira externa."""
    with st.spinner("Carregando taxonomia Fibery...", show_time=True):
        st.session_state.df_assets = load_assets()
        st.session_state.instruments_fgc = load_instruments_fgc()
        st.session_state.df_issuers = load_issuers()
        st.session_state.df_scheduled_events = load_scheduled_events(
            start_date=_scheduled_events_start_date()
        )


ready = False
df = None
df_target_allocations = pd.DataFrame()
df_accounts = pd.DataFrame()
instruments_fgc = []
df_issuers = pd.DataFrame()
df_scheduled_events = pd.DataFrame()
is_single_carteira = False

if not is_external and selected_carteiras:
    load_data(selected_carteiras)
    show_data_freshness("positions", label="Posições", ttl_minutes=60)
    df = st.session_state.df
    df_target_allocations = st.session_state.df_target_allocations
    df_accounts = st.session_state.df_accounts
    instruments_fgc = st.session_state.instruments_fgc
    df_issuers = st.session_state.df_issuers
    df_scheduled_events = st.session_state.df_scheduled_events
    is_single_carteira = len(selected_carteiras) == 1
    ready = True
elif is_external and uploaded_external is not None:
    try:
        df_upload = parse_external_positions_file(uploaded_external)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    load_external_reference_data()
    df_assets = st.session_state.df_assets
    instruments_fgc = st.session_state.instruments_fgc
    df_issuers = st.session_state.df_issuers
    df_scheduled_events = st.session_state.df_scheduled_events

    df_match_report = match_external_positions(df_upload, df_assets)
    summary = match_summary(df_match_report)
    has_match_issues = summary[MATCH_UNMATCHED] + summary[MATCH_AMBIGUOUS] > 0

    with st.expander("Qualidade do match", expanded=has_match_issues):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", summary["total"])
        m2.metric("Matched", summary[MATCH_MATCHED])
        m3.metric("Ambiguous", summary[MATCH_AMBIGUOUS])
        m4.metric("Unmatched", summary[MATCH_UNMATCHED])
        st.dataframe(
            style_table(
                df_match_report.drop(columns=["_asset_idx"], errors="ignore"),
                numeric_cols_format_as_float=["Saldo"],
                left_align_cols=["Ativo", "Status Match", "Nome Ativo", "Alias", "Candidatos"],
            ),
            hide_index=True,
        )

    try:
        df_positions_ext, _ = enrich_external_positions(
            df_upload,
            df_assets,
            portfolio_label=external_label,
            position_date=datetime.combine(external_date, datetime.min.time()),
            allow_partial=allow_partial_match,
        )
    except ValueError as e:
        st.warning(str(e))
        st.info(
            "Corrija os códigos no arquivo, cadastre os ativos no Fibery, "
            "ou marque **Analisar apenas ativos com match** na sidebar."
        )
        st.stop()

    if df_positions_ext.empty:
        st.error(
            "Nenhuma posição enriquecida com Classificação do Conjunto. "
            "Verifique o cadastro dos ativos."
        )
        st.stop()

    df = df_positions_ext
    selected_carteiras = [external_label]
    is_single_carteira = True
    ready = True
elif is_external:
    st.info("Envie um arquivo CSV/Excel com colunas **Ativo** e **Saldo** (use o template na sidebar).")
else:
    st.info("Selecione uma ou mais carteiras na sidebar.")

if ready:
    try:
        if is_external:
            st.subheader(f"{external_label} (externa)")
        elif is_single_carteira:
            st.subheader(selected_carteiras[0])
        else:
            st.subheader("Consolidado: " + ", ".join(sorted(selected_carteiras)))

        # Informações Gerais
        if is_external:
            st.code(
                f"{external_label}\n\n"
                f"Origem: arquivo externo\n"
                f"Data da posição: {external_date.strftime('%d/%m/%Y')}",
                language="markdown",
            )
        else:
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
            [
                pd.Grouper(key='Data Posição', freq='D'),
                'Nome Ativo',
                'Alias',
                'Classificação do Conjunto',
                'Classificação do Sub-Conjunto',
            ]
        ).agg(**{
            'Quantidade': ('Quantidade', 'sum'),
            'Valor Unitário': ('Valor Unitário', 'mean'),
            'Saldo': ('Saldo', 'sum')
        })

        df_portfolio_positions_current = get_latest_date_data(df_portfolio_positions).copy()
        df_portfolio_positions_current['%'] = (
            df_portfolio_positions_current['Saldo'] / df_portfolio_positions_current['Saldo'].sum() * 100
        )

        position_date = df['Data Posição'].max()

        # Agregações consumidas por mais de uma seção/aba. Ficam aqui para que
        # nenhuma aba dependa de variável criada dentro de outra.
        df_portfolio_composition = df.groupby(
            [pd.Grouper(key='Data Posição', freq='D'), 'Classificação do Conjunto']
        ).agg(**{'Saldo': ('Saldo', 'sum')})
        df_portfolio_composition_current = get_latest_date_data(df_portfolio_composition)
        df_portfolio_composition_current = df_portfolio_composition_current.reindex(ASSET_CLASSES_ORDER).dropna()

        # dropna=False: 'Data Vencimento', 'Nome Emissor' e 'Indexador' são chaves
        # de agrupamento e podem estar vazias no cadastro. Sem isso, o pandas
        # descarta essas posições silenciosamente das análises abaixo.
        df_maturity = df.groupby(
            [
                pd.Grouper(key='Data Posição', freq='D'),
                'Nome Ativo', 'Alias', 'Classificação do Conjunto',
                'Classificação Instrumento', 'Data Vencimento', 'Nome Emissor', 'Indexador',
            ],
            dropna=False,
        ).agg(**{
            'Quantidade': ('Quantidade', 'sum'),
            'Valor Unitário': ('Valor Unitário', 'mean'),
            'Saldo': ('Saldo', 'sum'),
        })
        df_maturity_current = get_latest_date_data(df_maturity).reset_index()
        df_maturity_current = df_maturity_current[df_maturity_current['Saldo'] > 0]
        df_maturity_current['Data Vencimento'] = pd.to_datetime(
            df_maturity_current['Data Vencimento'], errors='coerce'
        )
        df_maturity_current = df_maturity_current.sort_values(
            by='Data Vencimento', ascending=True
        ).reset_index(drop=True)
        df_maturity_current = enrich_dataframe_with_duration(
            df_maturity_current,
            settlement_date=position_date,
        )

        # Prazo residual medido na data da posição — mesma régua da duration.
        has_maturity = df_maturity_current['Data Vencimento'].notna()
        df_maturity_current['Anos para Vencimento'] = np.nan
        if has_maturity.any():
            df_maturity_current.loc[has_maturity, 'Anos para Vencimento'] = np.busday_count(
                position_date.date(),
                df_maturity_current.loc[has_maturity, 'Data Vencimento'].values.astype('datetime64[D]')
            ) / 252

        df_rf_duration_current = df_maturity_current[
            df_maturity_current['Classificação Instrumento'].isin(INSTRUMENTOS_RF)
        ]
        duration_media_rf = weighted_average_duration(df_rf_duration_current)
        duration_by_category_rf = weighted_average_duration_by_category(df_rf_duration_current)
        n_duration_ok = int(df_rf_duration_current['Duration'].notna().sum())
        n_duration_total = len(df_rf_duration_current)

        with st.expander("Resumo do Cliente", expanded=False):
            pass # TODO: Adicionar resumo do cliente

        with st.expander("Composição Completa", expanded=False):
            st.dataframe(
                style_table(
                    df_portfolio_positions_current,
                    numeric_cols_format_as_float=['Quantidade', 'Valor Unitário', 'Saldo', '%'],
                )
            )

        # Política de Investimentos (apenas carteiras sob gestão no Fibery)
        if is_external:
            pass
        elif not is_single_carteira:
            st.info("Política disponível apenas para carteira única.")
        else:
            df_policy_investments_current = pd.DataFrame()
            if (
                not df_target_allocations.empty
                and selected_carteiras[0] in df_target_allocations.index
            ):
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
        st.markdown(f"Data da Posição: `{position_date.date()}`")

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

            kpi_cols = st.columns(5)
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
            with kpi_cols[4]:
                duration_label = (
                    f"{duration_media_rf:.2f} anos" if duration_media_rf is not None else "—"
                )
                st.metric(
                    "Duration Média RF",
                    duration_label,
                    height="stretch",
                    delta=f"{n_duration_ok}/{n_duration_total} ativos com duration",
                    delta_color="off",
                    delta_arrow="off",
                )


        # =========================================================================
        # SEÇÃO 2 — Gráficos
        # =========================================================================
        # Acesso por nome: inserir/reordenar abas não desloca os blocos abaixo.
        tab_names = [
            "Alocação Atual",
            "Alocação Hierárquica",
            "Emissores",
            "Instrumentos",
            "Custodiantes",
            "Vencimentos & Duration",
            "Fluxo de Caixa",
            "Monitor de FGC",
            "Alertas",
        ]
        tabs = dict(zip(tab_names, st.tabs(tab_names)))

        with tabs["Alocação Atual"]:

            cols = st.columns(2)
            with cols[0]:
                chart_portfolio_composition = create_chart(
                    data=df_portfolio_composition_current,
                    columns=['Saldo'],
                    names=['Saldo'],
                    chart_type='donut',
                    title="Alocação Atual",
                    y_axis_title="%",
                )
                hct.streamlit_highcharts(chart_portfolio_composition)
            
            with cols[1]:
                if is_external:
                    st.info("Alocação alvo disponível apenas para carteiras sob gestão.")
                elif not is_single_carteira:
                    st.info("Política disponível apenas para carteira única.")
                else:
                    df_target_allocations_current = pd.DataFrame()
                    if (
                        not df_target_allocations.empty
                        and selected_carteiras[0] in df_target_allocations.index
                    ):
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

        with tabs["Alocação Hierárquica"]:
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

            df_portfolio_composition_sub = df.groupby(
                [pd.Grouper(key='Data Posição', freq='D'), 'Classificação do Sub-Conjunto']
            ).agg(**{'Saldo': ('Saldo', 'sum')})
            df_portfolio_composition_current_sub = get_latest_date_data(df_portfolio_composition_sub)
            df_portfolio_composition_current_sub = df_portfolio_composition_current_sub.sort_values(
                by='Saldo', ascending=False
            )

            df_inner_chart = df_portfolio_composition_current_sub.reset_index()
            df_outer_chart = df_portfolio_positions_current.reset_index()
            category_order = {cat: i for i, cat in enumerate(df_inner_chart['Classificação do Sub-Conjunto'])}
            df_outer_chart['_cat_order'] = df_outer_chart['Classificação do Sub-Conjunto'].map(category_order)
            df_outer_chart = df_outer_chart.sort_values(
                by=['_cat_order', 'Saldo'],
                ascending=[True, False]  # Categoria na ordem, Saldo decrescente
            ).drop(columns=['_cat_order'])

            options_nested = create_chart(
                data=df_outer_chart,
                columns='Saldo',
                x_column='Alias',  # Ativos individuais no anel externo
                chart_type='nested_pie',
                title='Alocação Hierárquica - Sub-Conjunto',
                inner_data=df_inner_chart,
                inner_y_column='Saldo',
                inner_x_column='Classificação do Sub-Conjunto',  # Classes no anel interno
                inner_series_name='Classes',
                names='Ativos',
                inner_size="55%",
                outer_inner_size="55%",
                center_hole_size="30%",
                outer_parent_column='Classificação do Sub-Conjunto',  # Liga anel externo ao interno
                enable_fullscreen_on_dblclick=True,
            )

            render_chart(options_nested)

        with tabs["Emissores"]:
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

        with tabs["Instrumentos"]:
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

        with tabs["Custodiantes"]:
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

        with tabs["Vencimentos & Duration"]:
            df_com_vencimento = df_maturity_current[df_maturity_current['Data Vencimento'].notna()]
            df_rf_sem_vencimento = df_rf_duration_current[
                df_rf_duration_current['Data Vencimento'].isna()
            ]

            cols = st.columns(2)
            with cols[0]:
                if duration_media_rf is not None:
                    by_cat_parts = []
                    for category in RF_DURATION_CATEGORIES:
                        value = duration_by_category_rf.get(category)
                        label = RF_DURATION_CATEGORY_LABELS[category]
                        if pd.notna(value):
                            by_cat_parts.append(f"{label}: **{value:.2f}**")
                        else:
                            by_cat_parts.append(f"{label}: —")
                    st.caption(
                        f"Duration média ponderada (RF): **{duration_media_rf:.2f} anos** "
                        f"· {n_duration_ok}/{n_duration_total} ativos com duration"
                    )
                    st.caption(" · ".join(by_cat_parts) + " (anos)")
                else:
                    st.caption("Duration média ponderada (RF): sem dados suficientes")

                if not df_rf_sem_vencimento.empty:
                    aliases_sem_vencimento = ", ".join(
                        sorted(df_rf_sem_vencimento['Alias'].dropna().astype(str).unique())
                    )
                    st.warning(
                        f"{len(df_rf_sem_vencimento)} posição(ões) de Renda Fixa sem Data de "
                        f"Vencimento cadastrada, fora da tabela e do histograma: "
                        f"{aliases_sem_vencimento}"
                    )

                st.dataframe(
                    style_table(
                        df_com_vencimento.set_index('Nome Ativo')[[
                            'Alias', 'Classificação do Conjunto', 'Classificação Instrumento',
                            'Data Vencimento', 'Duration', 'Duration Fonte',
                            'Quantidade', 'Valor Unitário', 'Saldo'
                        ]],
                        date_cols=['Data Vencimento'],
                        numeric_cols_format_as_float=['Valor Unitário', 'Saldo', 'Duration'],
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
                        df_tab = df_com_vencimento.copy()
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

        with tabs["Fluxo de Caixa"]:
            # A projeção parte de hoje (e não da data da posição) porque a
            # pergunta é o que ainda está por receber.
            cash_flow_reference = pd.Timestamp(datetime.now()).normalize()
            horizon_options = {"6 meses": 6, "12 meses": 12, "24 meses": 24, "36 meses": 36}
            horizon_label = st.radio(
                "Horizonte de projeção",
                options=list(horizon_options),
                index=1,
                horizontal=True,
                key="cash_flow_horizon",
            )
            horizon_months = horizon_options[horizon_label]

            df_cash_flow = build_cash_flow_schedule(
                df,
                df_scheduled_events,
                reference_date=cash_flow_reference,
                horizon_months=horizon_months,
            )
            df_cash_flow_coverage = scheduled_events_coverage(
                df,
                df_scheduled_events,
                reference_date=cash_flow_reference,
                horizon_months=horizon_months,
            )

            ultimo_mes = (cash_flow_reference.to_period('M') + horizon_months - 1)
            st.caption(
                f"Eventos de {cash_flow_reference:%d/%m/%Y} até {ultimo_mes.strftime('%m/%Y')}, "
                f"valorizados pelas quantidades da posição de {position_date.date()}. "
                f"O cronograma no Fibery cobre apenas "
                f"{', '.join(INSTRUMENTOS_EVENTOS_PROGRAMADOS)}."
            )

            if not df_cash_flow_coverage.empty:
                df_sem_cronograma = df_cash_flow_coverage[
                    df_cash_flow_coverage['Eventos Futuros'] == 0
                ]
                saldo_elegivel = df_cash_flow_coverage['Saldo'].sum()
                saldo_sem_cronograma = df_sem_cronograma['Saldo'].sum()
                if not df_sem_cronograma.empty:
                    pct_sem_cronograma = (
                        saldo_sem_cronograma / saldo_elegivel * 100 if saldo_elegivel > 0 else 0
                    )
                    st.warning(
                        f"{len(df_sem_cronograma)} de {len(df_cash_flow_coverage)} ativos com "
                        f"cronograma esperado não têm eventos cadastrados no período "
                        f"(R$ {saldo_sem_cronograma:,.2f}, {pct_sem_cronograma:.1f}% do saldo "
                        f"em {', '.join(INSTRUMENTOS_EVENTOS_PROGRAMADOS)}). "
                        f"O fluxo abaixo é um piso, não o total a receber."
                    )
                    with st.expander("Ativos sem eventos cadastrados no período", expanded=False):
                        st.dataframe(
                            style_table(
                                df_sem_cronograma[[
                                    'Nome Ativo', 'Alias', 'Classificação Instrumento',
                                    'Quantidade', 'Saldo',
                                ]],
                                numeric_cols_format_as_float=['Saldo'],
                                numeric_cols_format_as_int=['Quantidade'],
                                left_align_cols=['Nome Ativo', 'Alias'],
                            ),
                            hide_index=True,
                        )

                # O fluxo é Quantidade × valor unitário do evento, então posição
                # sem quantidade (comum em carteira externa) não pode ser valorizada.
                # A máscara é explícita para que quantidade nula (NA) entre no aviso.
                quantidade_coverage = pd.to_numeric(
                    df_cash_flow_coverage['Quantidade'], errors='coerce'
                ).fillna(0)
                df_sem_quantidade = df_cash_flow_coverage[
                    (df_cash_flow_coverage['Eventos Futuros'] > 0)
                    & ~(quantidade_coverage > 0)
                ]
                if not df_sem_quantidade.empty:
                    st.warning(
                        f"{len(df_sem_quantidade)} ativo(s) têm cronograma cadastrado mas estão "
                        f"sem quantidade na posição, então ficam fora do fluxo: "
                        + ", ".join(sorted(df_sem_quantidade['Alias'].dropna().astype(str)))
                    )

            if df_cash_flow.empty:
                st.info(
                    "Nenhum evento programado para as posições desta carteira no período. "
                    "Verifique o cadastro em Inv-Taxonomia/Evento Programado."
                )
            else:
                total_periodo = df_cash_flow['Valor'].sum()
                total_saldo_carteira = df_portfolio_positions_current['Saldo'].sum()
                pct_pl_periodo = (
                    total_periodo / total_saldo_carteira * 100 if total_saldo_carteira > 0 else 0
                )

                total_30d = df_cash_flow[
                    df_cash_flow['Data do Pagamento'] < cash_flow_reference + pd.Timedelta(days=30)
                ]['Valor'].sum()

                proxima_data = df_cash_flow['Data do Pagamento'].min()
                valor_proxima_data = df_cash_flow[
                    df_cash_flow['Data do Pagamento'] == proxima_data
                ]['Valor'].sum()

                cash_flow_kpis = st.columns(4)
                with cash_flow_kpis[0]:
                    st.metric(
                        f"A receber em {horizon_label}",
                        f"R$ {total_periodo:,.2f}",
                        height="stretch",
                        delta=f"{pct_pl_periodo:.1f}% do PL",
                        delta_color="off",
                        delta_arrow="off",
                    )
                with cash_flow_kpis[1]:
                    st.metric(
                        "Próximos 30 dias",
                        f"R$ {total_30d:,.2f}",
                        height="stretch",
                        delta_color="off",
                        delta_arrow="off",
                    )
                with cash_flow_kpis[2]:
                    st.metric(
                        "Média mensal",
                        f"R$ {total_periodo / horizon_months:,.2f}",
                        height="stretch",
                        delta_color="off",
                        delta_arrow="off",
                    )
                with cash_flow_kpis[3]:
                    st.metric(
                        f"Próximo pagamento: **{proxima_data:%d/%m/%Y}**",
                        f"R$ {valor_proxima_data:,.2f}",
                        height="stretch",
                        delta=f"{len(df_cash_flow)} eventos no período",
                        delta_color="off",
                        delta_arrow="off",
                    )

                df_cash_flow_monthly = aggregate_cash_flow_by_month(df_cash_flow)
                monthly_series_cols = [
                    col for col in df_cash_flow_monthly.columns if col != 'Mês'
                ]
                chart_cash_flow = create_chart(
                    data=df_cash_flow_monthly,
                    chart_type='column',
                    title="Fluxo Projetado por Mês",
                    columns=monthly_series_cols,
                    names=monthly_series_cols,
                    x_column='Mês',
                    y_axis_title="Valor (R$)",
                    x_axis_title="Mês do Pagamento",
                    stacking='normal',
                )
                hct.streamlit_highcharts(chart_cash_flow)

                cols = st.columns(2)
                with cols[0]:
                    st.markdown("**Eventos**")
                    # Índice oculto: o mesmo ativo repete em várias datas e o
                    # Styler do pandas não aceita índice duplicado.
                    st.dataframe(
                        style_table(
                            df_cash_flow[[
                                'Data do Pagamento', 'Alias', 'Tipo do Evento', 'Quantidade',
                                'Valor Unitário Evento', 'Valor',
                            ]],
                            date_cols=['Data do Pagamento'],
                            numeric_cols_format_as_float=['Valor Unitário Evento', 'Valor'],
                            numeric_cols_format_as_int=['Quantidade'],
                            left_align_cols=['Alias', 'Tipo do Evento'],
                        ),
                        hide_index=True,
                    )
                with cols[1]:
                    st.markdown("**Total por ativo no período**")
                    df_cash_flow_por_ativo = (
                        df_cash_flow
                        .groupby(['Alias', 'Classificação Instrumento'], dropna=False)
                        .agg(**{
                            'Valor': ('Valor', 'sum'),
                            'Eventos': ('Valor', 'size'),
                        })
                        .reset_index()
                        .sort_values(by='Valor', ascending=False)
                    )
                    df_cash_flow_por_ativo['% do Fluxo'] = (
                        df_cash_flow_por_ativo['Valor'] / total_periodo * 100
                        if total_periodo > 0 else 0
                    )
                    st.dataframe(
                        style_table(
                            df_cash_flow_por_ativo,
                            numeric_cols_format_as_float=['Valor', '% do Fluxo'],
                            numeric_cols_format_as_int=['Eventos'],
                            left_align_cols=['Alias', 'Classificação Instrumento'],
                        ),
                        hide_index=True,
                    )

        with tabs["Monitor de FGC"]:
            df_fgc = df_maturity_current[
                np.isin(df_maturity_current['Classificação Instrumento'], instruments_fgc)
            ].copy()
            # Emissor em branco no cadastro sairia do groupby e sumiria da
            # cobertura; explicitar mantém o saldo visível no gráfico.
            df_fgc['Nome Emissor'] = df_fgc['Nome Emissor'].fillna('Não Identificado')

            cols = st.columns(2)

            if len(df_fgc) > 0:
                with cols[0]:
                    st.dataframe(
                        style_table(
                            df_fgc.set_index('Nome Ativo')[[
                                'Alias', 'Classificação do Conjunto', 'Classificação Instrumento',
                                'Data Vencimento', 'Quantidade', 'Valor Unitário', 'Saldo'
                            ]],
                            date_cols=['Data Vencimento'],
                            numeric_cols_format_as_float=['Valor Unitário', 'Saldo'],
                            numeric_cols_format_as_int=['Quantidade'],
                        )
                    )
                with cols[1]:
                    df_fgc_total = df_fgc.groupby(
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

        with tabs["Alertas"]:
            df_alertas_rf = df[df['Classificação Instrumento'].isin(INSTRUMENTOS_RF)].copy()
            df_alertas_rf = get_emissor_column(df_alertas_rf)
            # Sem emissor a posição não casa com a tabela de status (fica como
            # 'Sem Classificação'), mas não pode desaparecer do monitoramento.
            df_alertas_rf['Emissor'] = df_alertas_rf['Emissor'].fillna('Não Identificado')

            df_alertas_posicoes = df_alertas_rf.groupby(
                [
                    pd.Grouper(key='Data Posição', freq='D'),
                    'Nome Ativo', 'Alias', 'Classificação do Conjunto',
                    'Classificação Instrumento', 'Data Vencimento', 'Emissor',
                ],
                dropna=False,
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
        with st.expander("Detalhes técnicos"):
            st.code(traceback.format_exc())
    except IndexError as e:
        st.error(f"Erro ao acessar dados: índice inválido - {e}")
        with st.expander("Detalhes técnicos"):
            st.code(traceback.format_exc())
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
        with st.expander("Detalhes técnicos"):
            st.code(traceback.format_exc())
