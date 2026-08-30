import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from configs.pages.market_breadth import INDICADORES

from utils.chart_helpers import create_chart
from utils.table import style_table

import streamlit_highcharts as hct

from persevera_tools.data import get_series

BREADTH_FIELDS = [
    'close',
    'pct_members_above_50dma',
    'pct_members_above_100dma',
    'pct_members_above_150dma',
    'pct_members_above_200dma',
]
BREADTH_COLUMN_NAMES = ['Fechamento', '% > 50DMA', '% > 100DMA', '% > 150DMA', '% > 200DMA']
BREADTH_METRICS = dict(zip(BREADTH_COLUMN_NAMES[1:], BREADTH_FIELDS[1:]))


def compute_conditional_forward_returns(index_data, conditions, horizon):
    """Forward index returns (pct) on days when all breadth conditions hold."""
    if not conditions or horizon < 1 or 'close' not in index_data.columns:
        return pd.Series(dtype=float)

    fields = ['close'] + [cond['field'] for cond in conditions]
    aligned = index_data.loc[:, fields].dropna()
    if aligned.empty:
        return pd.Series(dtype=float)

    fwd = aligned['close'].shift(-horizon) / aligned['close'] - 1.0
    mask = pd.Series(True, index=aligned.index)
    for cond in conditions:
        series = aligned[cond['field']]
        if cond['operator'] == 'gte':
            mask &= series >= cond['threshold']
        else:
            mask &= series <= cond['threshold']
    return (fwd[mask].dropna() * 100).rename('retorno')


def format_conditions_label(conditions):
    return " e ".join(
        f"{cond['label']} {cond['operator_label']} {cond['threshold']:g}"
        for cond in conditions
    )


HIST_NEG_COLOR = '#d32f2f'
HIST_POS_COLOR = '#2e7d32'


def _histogram_edges(values, n_bins):
    """Build bin edges that always split at zero when returns change sign."""
    lo = float(np.min(values))
    hi = float(np.max(values))
    if lo >= 0 or hi <= 0:
        return np.linspace(lo, hi, n_bins + 1)

    span = hi - lo
    n_neg = max(1, min(n_bins - 1, int(round(n_bins * (-lo) / span))))
    n_pos = n_bins - n_neg
    edges_neg = np.linspace(lo, 0.0, n_neg + 1)
    edges_pos = np.linspace(0.0, hi, n_pos + 1)
    return np.concatenate([edges_neg[:-1], edges_pos])


def build_return_histogram(returns, n_bins=15):
    """Bin forward returns, split at zero, with separate negative/positive series."""
    values = pd.to_numeric(returns, errors='coerce').dropna().to_numpy(dtype=float)
    empty = pd.DataFrame(columns=['Negativos', 'Positivos'])
    if values.size == 0:
        return empty
    if np.unique(values).size == 1:
        label = f'{values[0]:.1f}'
        if values[0] < 0:
            return pd.DataFrame({'Negativos': [int(values.size)], 'Positivos': [np.nan]}, index=[label])
        return pd.DataFrame({'Negativos': [np.nan], 'Positivos': [int(values.size)]}, index=[label])

    counts, edges = np.histogram(values, bins=_histogram_edges(values, n_bins))
    labels = [f'{lo:.1f} a {hi:.1f}' for lo, hi in zip(edges[:-1], edges[1:])]
    is_negative = edges[1:] <= 1e-12
    neg = np.where(is_negative, counts, np.nan).astype(float)
    pos = np.where(~is_negative, counts, np.nan).astype(float)
    return pd.DataFrame({'Negativos': neg, 'Positivos': pos}, index=labels)


st.title('Market Breadth')

@st.cache_data(ttl=3600)
def load_data(codes, field, start_date):
    try:
        return get_series(codes, start_date=start_date, field=field)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", min_value=datetime(2010, 1, 1), value=datetime(2010, 1, 1), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

# Load data with progress indicator
with st.spinner("Carregando dados dos índices...", show_time=True):
    data = load_data(list(INDICADORES.keys()), field=BREADTH_FIELDS, start_date=start_date_str)
    data.ffill(inplace=True, limit=1)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    # Tabela consolidada
    st.markdown(f"Dado mais recente: `{data.index.max().date()}`")
    consolidated_data = data.iloc[-1].to_frame('value').reset_index()
    consolidated_data = consolidated_data.pivot(index='code', columns='field', values='value')
    consolidated_data = consolidated_data.reindex(columns=BREADTH_FIELDS)
    consolidated_data.index = consolidated_data.index.map(lambda x: INDICADORES[x])
    
    st.dataframe(
        style_table(
            consolidated_data,
            column_names=BREADTH_COLUMN_NAMES,
            numeric_cols_format_as_int=['Fechamento'],
            percent_cols=['% > 50DMA', '% > 100DMA', '% > 150DMA', '% > 200DMA']
        ),
    )

    # Por índice
    selected_index = st.selectbox("Selecione o índice:", list(consolidated_data.index), width=300)
    value_selected = [k for k,v in INDICADORES.items() if v == selected_index][0]
    selected_index_data = data[value_selected]

    chart_breadth = create_chart(
        data=selected_index_data,
        columns=([BREADTH_FIELDS[0]], BREADTH_FIELDS[1:]),
        names=([BREADTH_COLUMN_NAMES[0]], BREADTH_COLUMN_NAMES[1:]),
        chart_type='dual_axis_line',
        title=f"Breadth de {selected_index}",
        y_axis_title=("Fechamento", "% de membros acima de"),
        y_axis_max=(None, 100),
    )
    hct.streamlit_highcharts(chart_breadth)

    # Análise de retornos condicionais
    cols = st.columns([1, 3])
    with cols[0]:
        horizon = st.number_input("Horizonte (dias)", min_value=1, max_value=252, value=21, step=1, key="fwd_horizon")
        st.caption("Ative os indicadores. Todas as condições ativas precisam valer no mesmo dia.")

        hdr_1, hdr_2, hdr_3 = st.columns([0.46, 0.24, 0.30])
        hdr_1.caption("Indicador")
        hdr_2.caption("Condição")
        hdr_3.caption("Threshold (%)")

        conditions = []
        for metric_label, metric_field in BREADTH_METRICS.items():
            on_col, op_col, thr_col = st.columns([0.46, 0.24, 0.30])
            enabled = on_col.checkbox(
                metric_label,
                value=(metric_label == '% > 50DMA'),
                key=f"fwd_on_{metric_field}",
            )
            operator_label = op_col.selectbox(
                "Condição",
                ["≥", "≤"],
                key=f"fwd_op_{metric_field}",
                label_visibility="collapsed",
            )
            threshold = thr_col.number_input(
                "Threshold",
                min_value=0.0,
                max_value=100.0,
                value=50.0,
                step=5.0,
                key=f"fwd_thr_{metric_field}",
                label_visibility="collapsed",
            )
            if enabled:
                conditions.append({
                    'label': metric_label,
                    'field': metric_field,
                    'operator': 'gte' if operator_label == '≥' else 'lte',
                    'operator_label': operator_label,
                    'threshold': float(threshold),
                })

    with cols[1]:
        if not conditions:
            st.warning("Ative pelo menos um indicador de breadth.")
        else:
            forward_returns = compute_conditional_forward_returns(
                selected_index_data,
                conditions,
                int(horizon),
            )

            if forward_returns.empty:
                st.warning("Não há observações suficientes para essa combinação de filtros e horizonte.")
            else:
                histogram = build_return_histogram(forward_returns)
                conditions_label = format_conditions_label(conditions)
                chart_fwd = create_chart(
                    data=histogram,
                    columns=['Negativos', 'Positivos'],
                    names=['Negativos', 'Positivos'],
                    color=[HIST_NEG_COLOR, HIST_POS_COLOR],
                    chart_type='column',
                    stacking='normal',
                    title=f"Retornos em {int(horizon)}d · {conditions_label} · {selected_index}",
                    y_axis_title="Frequência",
                    x_axis_title="Retorno (%)",
                    decimal_precision=0,
                    show_legend=True,
                )
                hct.streamlit_highcharts(chart_fwd)

                stat_1, stat_2, stat_3, stat_4 = st.columns(4)
                stat_1.metric("Observações", f"{len(forward_returns):,}".replace(",", "."))
                stat_2.metric("Média", f"{forward_returns.mean():.2f}%")
                stat_3.metric("Mediana", f"{forward_returns.median():.2f}%")
                stat_4.metric("% positivos", f"{(forward_returns > 0).mean() * 100:.1f}%")
                st.caption(
                    "Cada observação é o retorno do índice nos pregões seguintes a um dia em que todas as condições ativas foram verdadeiras."
                )
