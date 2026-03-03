import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table, get_monthly_returns_table, get_performance_table
from utils.auth import check_authentication
from persevera_tools.data import get_descriptors, get_series
from services.position_service import load_equities_portfolio


st.set_page_config(
    page_title="Carteira RVQM | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Carteira RVQM")

# =============================================================================
# Funções de carregamento
# =============================================================================

@st.cache_data(ttl=3600)
def load_data(codes, start_date, field):
    try:
        descriptors = field if isinstance(field, list) else [field]
        return get_descriptors(codes, start_date=start_date, descriptors=descriptors)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_indicators(codes, start_date):
    try:
        return get_series(codes, start_date=start_date)
    except Exception as e:
        st.error(f"Erro ao carregar indicadores: {str(e)}")
        return pd.DataFrame()


# =============================================================================
# Funções analíticas
# =============================================================================

def calculate_drawdown(returns_series: pd.Series) -> pd.Series:
    cumulative = (1 + returns_series).cumprod()
    rolling_max = cumulative.expanding().max()
    return (cumulative - rolling_max) / rolling_max * 100


def color_returns_cell(val):
    if pd.isna(val):
        return ''
    if val > 0:
        intensity = min(val / 8.0, 1.0)
        r = int(198 * (1 - intensity) + 26 * intensity)
        g = int(239 * (1 - intensity) + 122 * intensity)
        b = int(198 * (1 - intensity) + 49 * intensity)
        text = 'white' if intensity > 0.6 else 'black'
    else:
        intensity = min(abs(val) / 8.0, 1.0)
        r = int(255 * (1 - intensity) + 192 * intensity)
        g = int(199 * (1 - intensity) + 0 * intensity)
        b = int(206 * (1 - intensity) + 0 * intensity)
        text = 'white' if intensity > 0.6 else 'black'
    return f'background-color: rgb({r},{g},{b}); color: {text}'


# =============================================================================
# Carregamento de dados
# =============================================================================

with st.spinner("Carregando composição da carteira..."):
    equities_portfolio = load_equities_portfolio()
    securities_list = list(equities_portfolio['code'].unique())

with st.spinner("Carregando preços das ações selecionadas..."):
    raw_data = load_data(
        securities_list,
        start_date=equities_portfolio['date'].min(),
        field=['price_close']
    )

with st.spinner("Carregando indicadores..."):
    indicators = load_indicators(
        ['br_ibovespa', 'br_smll', 'br_cdi_index'],
        start_date=equities_portfolio['date'].min()
    )

if raw_data.empty or len(securities_list) == 0:
    st.warning("Nenhum dado disponível para exibir.")
    st.stop()

prices = raw_data.copy()

# =============================================================================
# Composição Atual
# =============================================================================

current_date = equities_portfolio['date'].max()
current_portfolio = (
    equities_portfolio[equities_portfolio['date'] == current_date]
    .copy()
    .sort_values('weight', ascending=False)
    .reset_index(drop=True)
)
total_weight = current_portfolio['weight'].sum()
current_portfolio['weight_pct'] = current_portfolio['weight'] / total_weight * 100

st.markdown(
    f"<p style='color:#888; font-size:0.85rem; margin-bottom:6px;'>"
    f"{len(current_portfolio)} ativos &nbsp;·&nbsp; {current_date.strftime('%d/%m/%Y')}"
    f"</p>",
    unsafe_allow_html=True,
)

chips = "".join(
    f'<span style="display:inline-block; background:#1e3a5f; color:white; border-radius:8px; '
    f'padding:6px 14px; margin:3px 4px; font-size:0.83rem; font-weight:600; letter-spacing:0.3px;">'
    f'{row["code"]}&nbsp;'
    f'<span style="font-weight:300; opacity:0.7;">{row["weight_pct"]:.1f}%</span></span>'
    for _, row in current_portfolio.iterrows()
)
st.markdown(f'<div style="line-height:2.8">{chips}</div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# =============================================================================
# Retornos e cumulativo completo
# =============================================================================

weights_df = equities_portfolio.pivot(index='date', columns='code', values='weight')
weights_df = weights_df.div(weights_df.sum(axis=1), axis=0).fillna(0)
weights_df = weights_df.reindex(prices.index).ffill()

returns_portfolio = weights_df.mul(prices.pct_change(), axis=0).sum(axis=1)
returns_df = pd.concat([returns_portfolio, indicators.pct_change().fillna(0)], axis=1)
returns_df.columns = ['Carteira', 'Ibovespa', 'SMLL', 'CDI']

# =============================================================================
# Histórico de Alocações
# =============================================================================

with st.expander("Histórico de Alocações", expanded=False):
    weights_history_table = weights_df.replace(0, np.nan).mul(100)
    weights_history_table.index = weights_history_table.index.strftime('%Y-%m-%d')
    st.dataframe(
        style_table(
            weights_history_table,
            percent_cols=weights_df.columns.tolist()
        ),
        hide_index=False
    )

# =============================================================================
# Seleção de período
# =============================================================================

min_date_val = returns_df.index.min().date()
max_date_val = returns_df.index.max().date()

if 'start_date_picker' not in st.session_state:
    st.session_state['start_date_picker'] = min_date_val
if 'end_date_picker' not in st.session_state:
    st.session_state['end_date_picker'] = max_date_val

cols_date = st.columns(2)
with cols_date[0]:
    start_date_input = st.date_input(
        "Data Inicial",
        format="DD/MM/YYYY",
        min_value=min_date_val,
        max_value=max_date_val,
        key='start_date_picker'
    )
with cols_date[1]:
    end_date_input = st.date_input(
        "Data Final",
        format="DD/MM/YYYY",
        min_value=min_date_val,
        max_value=max_date_val,
        key='end_date_picker'
    )

if start_date_input > end_date_input:
    st.warning("Data inicial deve ser anterior à data final.")
    st.stop()

start_ts = pd.to_datetime(start_date_input)
end_ts = pd.to_datetime(end_date_input)

mask = (returns_df.index >= start_ts) & (returns_df.index <= end_ts)
returns_period = returns_df[mask]
cumulative_period = (1 + returns_period).cumprod() - 1

# =============================================================================
# Performance Acumulada + Drawdown
# =============================================================================

col_charts = st.columns(2)
with col_charts[0]:
    hct.streamlit_highcharts(create_chart(
        data=cumulative_period * 100,
        columns=["Carteira", "Ibovespa", "SMLL", "CDI"],
        names=["Carteira", "Ibovespa", "SMLL", "CDI"],
        chart_type='line',
        title="Performance Acumulada",
        y_axis_title="Retorno (%)",
        decimal_precision=2
    ))

with col_charts[1]:
    dd_df = pd.DataFrame({
        'Carteira': calculate_drawdown(returns_period['Carteira']),
        'Ibovespa': calculate_drawdown(returns_period['Ibovespa']),
    })
    hct.streamlit_highcharts(create_chart(
        data=dd_df,
        columns=['Carteira', 'Ibovespa'],
        names=['Carteira', 'Ibovespa'],
        chart_type='area',
        title="Drawdown",
        y_axis_title="Drawdown (%)",
        decimal_precision=2
    ))

# =============================================================================
# Retorno Mensal
# =============================================================================

st.markdown("#### Retorno Mensal — Carteira (%)")
monthly_table = get_monthly_returns_table(returns_df['Carteira'])
performance_table = get_performance_table(cumulative_period.add(1)).set_index('index')

styled_monthly = (
    monthly_table.style
    .map(color_returns_cell)
    .format("{:.1f}%", na_rep="—")
)
st.dataframe(styled_monthly, use_container_width=True)

st.dataframe(
    style_table(
        performance_table,
        numeric_cols_format_as_float=list(performance_table.columns),
        highlight_quartile=list(performance_table.columns)
        ),
    use_container_width=True
)

# =============================================================================
# Retorno Diário
# =============================================================================

hct.streamlit_highcharts(create_chart(
    data=returns_period * 10000,
    columns=["Carteira", "Ibovespa"],
    names=["Carteira", "Ibovespa"],
    chart_type='column',
    title="Retorno Diário",
    y_axis_title="Retorno (bps)",
    decimal_precision=0
))
