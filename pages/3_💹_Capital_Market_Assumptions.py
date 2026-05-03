import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import timedelta, date
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table, get_performance_table
from utils.auth import check_authentication
from persevera_tools.data import get_series
from configs.pages.capital_market_assumptions import (
    CAPITAL_MARKET_ASSUMPTIONS,
    BUCKET_ORDER,
    BUCKET_COLORS,
)

st.set_page_config(
    page_title="Capital Market Assumptions | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Capital Market Assumptions")

LOOKBACK_YEARS = 15
WEEKS_PER_YEAR = 52
DAYS_PER_YEAR = 365.25
MIN_COVERAGE_YEARS = 0.5  # ignore series with less than this for long-term stats


@st.cache_data(ttl=3600)
def load_data(codes, start_date):
    try:
        df = get_series(codes, start_date=start_date, field='close')
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()


def _weekly_returns(df):
    return df.resample('W').last().pct_change(fill_method=None)


def compute_long_term_stats(df):
    """CAGR (geométrico), volatilidade anualizada, assimetria, curtose e
    janela de cobertura por ativo. Cada métrica usa toda a janela disponível
    do próprio ativo, evitando comparar séries com históricos diferentes
    sob uma mesma janela artificial.
    """
    weekly = _weekly_returns(df)

    cagr = pd.Series(np.nan, index=df.columns, dtype=float)
    starts = pd.Series(pd.NaT, index=df.columns, dtype='datetime64[ns]')
    years = pd.Series(np.nan, index=df.columns, dtype=float)

    for col in df.columns:
        s = df[col].dropna()
        if len(s) < 2:
            continue
        first_idx, last_idx = s.index[0], s.index[-1]
        n_years = (last_idx - first_idx).days / DAYS_PER_YEAR
        starts[col] = first_idx
        years[col] = n_years
        if n_years < MIN_COVERAGE_YEARS or s.iloc[0] <= 0:
            continue
        cagr[col] = (s.iloc[-1] / s.iloc[0]) ** (1 / n_years) - 1

    vol = weekly.std() * np.sqrt(WEEKS_PER_YEAR)

    return pd.DataFrame({
        'Retorno (a.a.)': cagr * 100,
        'Volatilidade (a.a.)': vol * 100,
        'Assimetria': weekly.skew(),
        'Curtose': weekly.kurt(),
        'Início': starts,
        'Anos': years.round(1),
    })


def calculate_custom_return(df, start, end):
    period_df = df.loc[start:end].ffill()
    if len(period_df) < 2:
        return pd.Series(np.nan, index=df.columns)
    return (period_df.iloc[-1] / period_df.iloc[0] - 1) * 100


def attach_bucket_index(df, asset_names, asset_buckets):
    """Replace a code-indexed DataFrame with a (Bucket, Classe de Ativos)
    MultiIndex, sorted by canonical bucket order then by name."""
    df = df.copy()
    bucket_rank = {b: i for i, b in enumerate(BUCKET_ORDER)}
    codes = df.index.tolist()
    buckets = [asset_buckets.get(c, '') for c in codes]
    names = [asset_names.get(c, c) for c in codes]
    df['__rank'] = [bucket_rank.get(b, len(BUCKET_ORDER)) for b in buckets]
    df['__bucket'] = buckets
    df['__name'] = names
    df = df.sort_values(['__rank', '__name'])
    df.index = pd.MultiIndex.from_arrays(
        [df['__bucket'].tolist(), df['__name'].tolist()],
        names=['Bucket', 'Classe de Ativos'],
    )
    return df.drop(columns=['__rank', '__bucket', '__name'])


def scatter_data_by_bucket(stats_df, x_col, y_col):
    """Build a flat DataFrame where each bucket becomes a y-column. Each
    bucket therefore renders as its own scatter series with its own color."""
    df = stats_df.reset_index()
    out = pd.DataFrame({
        'Classe de Ativos': df['Classe de Ativos'],
        x_col: df[x_col],
    })
    used_buckets, used_colors = [], []
    for bucket in BUCKET_ORDER:
        mask = df['Bucket'] == bucket
        if not mask.any():
            continue
        ys = np.where(mask, df[y_col], np.nan)
        if not pd.Series(ys).notna().any():
            continue
        out[bucket] = ys
        used_buckets.append(bucket)
        used_colors.append(BUCKET_COLORS.get(bucket, '#999999'))
    return out, used_buckets, used_colors


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
codes = [
    code
    for bucket_codes in CAPITAL_MARKET_ASSUMPTIONS.values()
    for code in bucket_codes.keys()
]
asset_names = {
    code: name
    for bucket_codes in CAPITAL_MARKET_ASSUMPTIONS.values()
    for code, name in bucket_codes.items()
}
asset_buckets = {
    code: bucket
    for bucket, bucket_codes in CAPITAL_MARKET_ASSUMPTIONS.items()
    for code in bucket_codes.keys()
}

with st.spinner(f"Carregando {LOOKBACK_YEARS} anos de dados..."):
    start_date = pd.to_datetime(date.today() - timedelta(days=LOOKBACK_YEARS * 365))
    data = load_data(codes, start_date.strftime('%Y-%m-%d'))

if data.empty:
    st.warning("Sem dados carregados.")
    st.stop()

# ---------------------------------------------------------------------------
# Compute stats / performance
# ---------------------------------------------------------------------------
performance_table = get_performance_table(data)
if 'code' in performance_table.columns:
    performance_table = performance_table.set_index('code')

stats = compute_long_term_stats(data)

data_min = data.index.min().date()
data_max = data.index.max().date()

# ---------------------------------------------------------------------------
# Sidebar – período customizado
# ---------------------------------------------------------------------------
if 'custom_start' not in st.session_state:
    st.session_state.custom_start = pd.to_datetime(date(data_max.year, 1, 1))
else:
    if not isinstance(st.session_state.custom_start, pd.Timestamp):
        st.session_state.custom_start = pd.to_datetime(st.session_state.custom_start)
    if st.session_state.custom_start.date() < data_min:
        st.session_state.custom_start = pd.to_datetime(data_min)
    elif st.session_state.custom_start.date() > data_max:
        st.session_state.custom_start = pd.to_datetime(data_max)

if 'custom_end' not in st.session_state:
    st.session_state.custom_end = pd.to_datetime(data_max)
else:
    if not isinstance(st.session_state.custom_end, pd.Timestamp):
        st.session_state.custom_end = pd.to_datetime(st.session_state.custom_end)
    if st.session_state.custom_end.date() > data_max:
        st.session_state.custom_end = pd.to_datetime(data_max)
    elif st.session_state.custom_end.date() < data_min:
        st.session_state.custom_end = pd.to_datetime(data_min)

if st.session_state.custom_start > st.session_state.custom_end:
    st.session_state.custom_start = st.session_state.custom_end

with st.sidebar:
    st.markdown("#### Período Customizado")
    custom_start_input = st.date_input(
        "Início",
        format="DD/MM/YYYY",
        value=st.session_state.custom_start.date(),
        min_value=data_min,
        max_value=data_max,
        key="custom_start_picker",
    )
    custom_end_input = st.date_input(
        "Fim",
        format="DD/MM/YYYY",
        value=st.session_state.custom_end.date(),
        min_value=data_min,
        max_value=data_max,
        key="custom_end_picker",
    )
    if custom_start_input >= custom_end_input:
        st.warning("A data de início deve ser anterior à data de fim.")

st.session_state.custom_start = pd.to_datetime(custom_start_input)
st.session_state.custom_end = pd.to_datetime(custom_end_input)

custom_start = st.session_state.custom_start
custom_end = st.session_state.custom_end

# ---------------------------------------------------------------------------
# Custom period column (added before bucket attachment so we can align by code)
# ---------------------------------------------------------------------------
if custom_start < custom_end:
    custom_col_label = f"Custom ({custom_start:%d/%m/%y} – {custom_end:%d/%m/%y})"
    performance_table[custom_col_label] = calculate_custom_return(data, custom_start, custom_end)

# ---------------------------------------------------------------------------
# Attach bucket / sort tables
# ---------------------------------------------------------------------------
performance_table = attach_bucket_index(performance_table, asset_names, asset_buckets)
stats = attach_bucket_index(stats, asset_names, asset_buckets)

st.markdown("Data mais recente: **{0:%Y-%m-%d}**".format(data_max))

incomplete = stats[stats['Anos'] < (LOOKBACK_YEARS - 0.5)]
if not incomplete.empty:
    incomplete_names = ", ".join(incomplete.index.get_level_values('Classe de Ativos').tolist())
    st.caption(
        f"Janela solicitada: {LOOKBACK_YEARS} anos. Séries com cobertura menor: "
        f"{incomplete_names}. As métricas de longo prazo usam toda a janela "
        "disponível de cada ativo (ver colunas Início e Anos)."
    )

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tabs = st.tabs(["Performance Acumulada", "Longo Prazo", "Correlações"])

with tabs[0]:   # Performance Acumulada
    perf_numeric_cols = [c for c in performance_table.columns]
    st.dataframe(
        style_table(
            performance_table,
            numeric_cols_format_as_float=perf_numeric_cols,
            color_negative_positive_cols=perf_numeric_cols,
        )
    )

with tabs[1]:   # Longo Prazo
    stats_float_cols = ['Retorno (a.a.)', 'Volatilidade (a.a.)', 'Assimetria', 'Curtose', 'Anos']
    st.dataframe(
        style_table(
            stats,
            numeric_cols_format_as_float=stats_float_cols,
            date_cols=['Início'],
            date_format='%d/%m/%Y',
        )
    )

    cols = st.columns(2)

    with cols[0]:
        scatter_rr, used_buckets_rr, used_colors_rr = scatter_data_by_bucket(
            stats[['Volatilidade (a.a.)', 'Retorno (a.a.)']],
            x_col='Volatilidade (a.a.)',
            y_col='Retorno (a.a.)',
        )
        chart_risk_return = create_chart(
            data=scatter_rr,
            columns=used_buckets_rr,
            names=used_buckets_rr,
            color=used_colors_rr,
            x_column='Volatilidade (a.a.)',
            chart_type='scatter',
            point_name_column='Classe de Ativos',
            title="Retorno vs Volatilidade",
            y_axis_title="Retorno (%)",
            x_axis_title="Volatilidade (%)",
            show_legend=True,
            zoom_type='xy',
            show_point_name_labels=True,
            tooltip_point_format=(
                '<b>{point.name}</b><br/>'
                '<span style="color:{series.color}">{series.name}</span><br/>'
                'Risco: {point.x:.2f}%<br/>'
                'Retorno: {point.y:.2f}%'
            ),
        )
        hct.streamlit_highcharts(chart_risk_return)
        st.info("""
        - **Retorno**: CAGR (taxa composta de crescimento anual) calculado sobre toda a janela
        disponível de cada ativo.
        - **Volatilidade**: desvio padrão dos retornos semanais anualizado por √52,
        medindo a dispersão em torno da média. Valores altos indicam maior risco.
        """)

    with cols[1]:
        scatter_sk, used_buckets_sk, used_colors_sk = scatter_data_by_bucket(
            stats[['Curtose', 'Assimetria']],
            x_col='Curtose',
            y_col='Assimetria',
        )
        chart_skew_kurt = create_chart(
            data=scatter_sk,
            columns=used_buckets_sk,
            names=used_buckets_sk,
            color=used_colors_sk,
            x_column='Curtose',
            chart_type='scatter',
            point_name_column='Classe de Ativos',
            title="Assimetria vs Curtose",
            y_axis_title="Assimetria",
            x_axis_title="Curtose",
            show_legend=True,
            zoom_type='xy',
            horizontal_line={'value': 0, 'color': '#FF0000', 'width': 2, 'zIndex': 5},
            show_point_name_labels=True,
            tooltip_point_format=(
                '<b>{point.name}</b><br/>'
                '<span style="color:{series.color}">{series.name}</span><br/>'
                'Curtose: {point.x:.2f}<br/>'
                'Assimetria: {point.y:.2f}'
            ),
        )
        hct.streamlit_highcharts(chart_skew_kurt)
        st.info("""
        - **Assimetria**: mede a simetria da distribuição dos retornos em relação à distribuição
        normal (referência = 0). Um valor positivo indica cauda longa à direita (retornos extremos
        positivos mais frequentes que o esperado); um valor negativo indica cauda longa à esquerda
        (retornos extremos negativos mais frequentes que o esperado).
        - **Curtose**: mede o peso das caudas em relação à distribuição normal (referência = 0,
        usando curtose em excesso). Um valor positivo (leptocúrtica) indica caudas mais pesadas
        que a normal — maior probabilidade de eventos extremos. Um valor negativo (platicúrtica)
        indica caudas mais leves que a normal.
        """)

with tabs[2]:   # Correlações
    correlation_matrix = _weekly_returns(data.rename(columns=asset_names)).corr()
    correlation_matrix = correlation_matrix.where(np.tril(np.ones(correlation_matrix.shape)).astype(np.bool_))
    correlation_heatmap = create_chart(
        data=correlation_matrix,
        chart_type="heatmap",
        title="",
    )
    hct.streamlit_highcharts(correlation_heatmap)