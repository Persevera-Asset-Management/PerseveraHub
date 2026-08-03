import pandas as pd
import numpy as np
import streamlit as st
import streamlit_highcharts as hct

from utils.table import style_table, get_performance_table
from utils.chart_helpers import create_chart, render_chart

from persevera_tools.data import get_funds_data, get_series
from persevera_tools.db.fibery import read_fibery

st.title("Fundos · Peer Group")

@st.cache_data(ttl=3600)
def get_persevera_peers():
    df = read_fibery(
        table_name="Inv-Asset Allocation/Pares de Fundos",
        include_fibery_fields=False,
    )
    df = df[["Ativo", "Name", "Peer Group"]]
    df.columns = ["fund_cnpj", "short_name", "persevera_group"]
    return df

peers = get_persevera_peers()

@st.cache_data(ttl=3600)
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_fund_data(fund_name):
    """
    Loads NAV and Total Equity data for a given fund and its peers.
    """
    if peers.empty:
        st.warning("Peers data is not loaded. Cannot load fund data.")
        return pd.DataFrame(), pd.DataFrame()

    fund_peers = peers[peers['persevera_group'] == fund_name].copy()

    # Adjustment for Compass fund
    if 'fund_cnpj' in fund_peers.columns:
        fund_peers['fund_cnpj'] = fund_peers['fund_cnpj'].str.replace('32.041.825/0001-40', '44.417.598/0001-94', regex=False)
    if 'short_name' in fund_peers.columns:
        fund_peers['short_name'] = fund_peers['short_name'].str.replace('Persevera Compass Advisory FIC FIMs', 'Persevera Nemesis Total Return FIM', regex=False)
    
    if fund_peers.empty:
        st.warning(f"No peers found for fund group: {fund_name}")
        return pd.DataFrame(), pd.DataFrame()

    fund_cnpjs = list(fund_peers['fund_cnpj'].unique())

    try:
        df = get_funds_data(cnpjs=fund_cnpjs, fields=['fund_nav', 'fund_total_equity'])

    except Exception as e:
        st.error(f"Error calling get_funds_data: {e}")
        return pd.DataFrame(), pd.DataFrame()

    if df.empty:
        st.warning(f"No data returned by get_funds_data for CNPJs: {fund_cnpjs}")
        return pd.DataFrame(), pd.DataFrame()

    # Map fund_name using peers DataFrame
    df = df.swaplevel(axis=1).stack(future_stack=True)
    df.columns = df.columns.map(peers.set_index('fund_cnpj')['short_name'].to_dict())
    df = df.unstack().swaplevel(axis=1)

    # Select NAV data
    if 'fund_nav' not in df.columns:
        st.error("fund_nav column missing for NAV pivot.")
        nav = pd.DataFrame()
    else:
        nav = df['fund_nav'].copy()
        if not nav.empty:
            persevera_cols_nav = nav.filter(like='Persevera').columns
            if not persevera_cols_nav.empty:
                nav.loc[:, persevera_cols_nav] = nav.loc[:, persevera_cols_nav].replace(0, np.nan)
            nav = nav.sort_index(axis=1)

    # Select Total Equity data
    if 'fund_total_equity' not in df.columns:
        st.error("fund_total_equity column missing for Total Equity pivot.")
        total_equity = pd.DataFrame()
    else:
        total_equity = df['fund_total_equity']
        if not total_equity.empty:
            total_equity = total_equity.sort_index(axis=1)
    
    return nav, total_equity

BENCHMARKS = ['CDI', 'Ibovespa', 'SMLL']
RETURN_COLS = ['day', 'mtd', 'ytd', '1m', '3m', '6m', '12m', '24m', '36m', 'custom']


def _normalize_nav_index(nav: pd.DataFrame, ffill: bool = True) -> pd.DataFrame:
    nav_levels = nav.copy()
    if isinstance(nav_levels.index, pd.MultiIndex):
        if 'date' not in nav_levels.index.names:
            raise ValueError("MultiIndex must include a 'date' level")
        nav_levels.index = pd.to_datetime(nav_levels.index.get_level_values('date'))
    else:
        nav_levels.index = pd.to_datetime(nav_levels.index)
    nav_levels = nav_levels.sort_index()
    return nav_levels.ffill() if ffill else nav_levels


def _custom_period_return(nav_levels: pd.DataFrame, start_date, end_date) -> pd.Series:
    custom_period = nav_levels.loc[start_date:end_date]
    if len(custom_period) <= 1:
        return pd.Series(np.nan, index=nav_levels.columns)
    with np.errstate(divide='ignore', invalid='ignore'):
        custom_ret = custom_period.iloc[-1] / custom_period.iloc[0] - 1.0
    return custom_ret.where(np.isfinite(custom_ret)) * 100


def _last_nav_dates(nav: pd.DataFrame) -> pd.Series:
    """Last non-null NAV date per fund (no ffill, so lagging peers keep their own date)."""
    nav_raw = _normalize_nav_index(nav, ffill=False)
    return nav_raw.apply(lambda s: s.last_valid_index())


def _fund_type(name) -> str:
    if 'Persevera' in str(name):
        return 'Persevera'
    if name in BENCHMARKS:
        return 'Benchmark'
    return 'Peer'


@st.cache_data(ttl=3600)
def build_peer_performance_table(nav, total_equity, start_date, end_date):
    """Enrich utils performance returns with peer-group ranks, PL, last NAV date and type."""
    if nav is None or nav.empty:
        return pd.DataFrame()

    df_result = get_performance_table(nav)
    if df_result.empty:
        return pd.DataFrame()

    id_col = 'fund_name' if 'fund_name' in df_result.columns else df_result.columns[0]
    df_result = (
        df_result
        .rename(columns={id_col: 'fund_name', '1d': 'day'})
        .set_index('fund_name')
    )

    nav_levels = _normalize_nav_index(nav)
    df_result['custom'] = _custom_period_return(
        nav_levels, start_date, end_date
    ).reindex(df_result.index)

    ranks = {
        f'{key}_rank': (
            df_result[key]
            .drop(labels=BENCHMARKS, errors='ignore')
            .rank(ascending=False)
        )
        for key in RETURN_COLS
    }

    pl_series = pd.Series(np.nan, index=df_result.index)
    if total_equity is not None and not total_equity.empty:
        pl_series = total_equity.ffill().iloc[-1].reindex(df_result.index)

    ultima_cota = _last_nav_dates(nav).reindex(df_result.index)

    df_result = df_result.assign(**ranks, PL=pl_series, ultima_cota=ultima_cota)
    df_result['type'] = df_result.index.map(_fund_type)

    col_order = ['type', 'PL', 'ultima_cota'] + RETURN_COLS + [f'{key}_rank' for key in RETURN_COLS]
    return df_result[col_order].reset_index()

@st.cache_data(ttl=3600)
def calculate_performance(df):
    if df.empty or df.shape[0] < 2:
        return df
    df_pct_change = df.ffill().pct_change(fill_method=None)
    cumulative_returns = (1 + df_pct_change).cumprod()
    cumulative_returns.iloc[0] = 1 
    final_returns = cumulative_returns.sub(1)
    final_returns = final_returns.ffill()
    return final_returns

@st.cache_data(ttl=3600)
def load_benchmark_data(fund_name, _nav_index):
    benchmark_map = {'Trinity': ('br_cdi_index',),
                     'Yield': ('br_cdi_index',),
                     'Phoenix': ('br_cdi_index',),
                     'Prospera': ('br_cdi_index',),
                     'FIDC': ('br_cdi_index',),
                     'Compass': ('br_cdi_index',),
                     'Nemesis': ('br_cdi_index', 'br_ibovespa', 'br_smll'),
                     'Proteus': ('br_cdi_index', 'br_ibovespa', 'br_smll'),
                     'Long Bias': ('br_cdi_index', 'br_ibovespa', 'br_smll')}

    codes_to_fetch = benchmark_map.get(fund_name, ('br_cdi_index',)) # Default to CDI
    df_benchmark = get_series(list(codes_to_fetch), start_date=_nav_index.min(), field='close')
    
    # Ensure df_benchmark is a DataFrame before renaming columns
    if isinstance(df_benchmark, pd.Series):
        df_benchmark = df_benchmark.to_frame('br_cdi_index')

    df_benchmark = df_benchmark.rename(columns={'br_cdi_index': 'CDI', 'br_ibovespa': 'Ibovespa', 'br_smll': 'SMLL'})
    return df_benchmark

with st.sidebar:
    fund_names_list = ['Trinity', 'Yield', 'Phoenix', 'Prospera', 'FIDC', 'Compass', 'Nemesis', 'Proteus', 'Long Bias']
    selected_fund_names = st.multiselect(
        "Selecione o(s) grupo(s) de fundos:",
        fund_names_list,
        default=['Nemesis']
    )

if not selected_fund_names:
    st.info("Selecione pelo menos um grupo de fundos na barra lateral.")
    st.stop()

selected_fund_name = " | ".join(selected_fund_names)
st.header(selected_fund_name)

# Load and combine data for all selected fund groups
with st.spinner(f"Carregando dados de {selected_fund_name}...", show_time=True):
    nav_list, equity_list = [], []
    for fname in selected_fund_names:
        _nav, _eq = load_fund_data(fname)
        if not _nav.empty:
            nav_list.append(_nav)
        if not _eq.empty:
            equity_list.append(_eq)

    nav_data = pd.concat(nav_list, axis=1) if nav_list else pd.DataFrame()
    # Drop duplicate columns that appear in multiple groups
    nav_data = nav_data.loc[:, ~nav_data.columns.duplicated()]
    total_equity_data = pd.concat(equity_list, axis=1) if equity_list else pd.DataFrame()
    total_equity_data = total_equity_data.loc[:, ~total_equity_data.columns.duplicated()]

if nav_data.empty:
    st.warning(f"Não foi possível carregar dados de NAV para o fundo {selected_fund_name}.")
    if not total_equity_data.empty:
        st.subheader(f"Patrimônio Líquido para {selected_fund_name}")
        st.line_chart(total_equity_data.filter(like='Persevera'))

# Determine the Persevera fund's actual name from the loaded data
persevera_fund_col_name = next((col for col in nav_data.columns if 'Persevera' in col), None)
if not persevera_fund_col_name:
    st.error("Não foi possível identificar a coluna do fundo Persevera principal nos dados carregados.")
    
# Load benchmark data — union of all benchmarks across selected groups
benchmark_df_list = [load_benchmark_data(fname, nav_data.index) for fname in selected_fund_names]
benchmark_df = pd.concat(benchmark_df_list, axis=1)
benchmark_df = benchmark_df.loc[:, ~benchmark_df.columns.duplicated()]

# Merge NAV data with benchmark data
if not isinstance(benchmark_df.index, pd.DatetimeIndex):
    benchmark_df.index = pd.to_datetime(benchmark_df.index)

combined_nav_data = pd.merge(nav_data, benchmark_df, left_index=True, right_index=True, how='left')

for col in benchmark_df.columns:
    if col in combined_nav_data:
        combined_nav_data[col] = combined_nav_data[col].ffill()

# Date Range Selection — min date is the Persevera fund's first valid NAV
max_date_val = combined_nav_data.index.max().date()
if persevera_fund_col_name and persevera_fund_col_name in combined_nav_data.columns:
    persevera_start = combined_nav_data[persevera_fund_col_name].first_valid_index()
    min_date_val = (
        pd.Timestamp(persevera_start).date()
        if persevera_start is not None
        else combined_nav_data.index.min().date()
    )
else:
    min_date_val = combined_nav_data.index.min().date()

# Initialize or validate st.session_state.start_date (as Timestamp)
if 'start_date' not in st.session_state:
    st.session_state.start_date = pd.to_datetime(min_date_val)
else:
    # Ensure it's a Timestamp if it exists
    if not isinstance(st.session_state.start_date, pd.Timestamp):
         st.session_state.start_date = pd.to_datetime(st.session_state.start_date)
    # Compare .date() part and clamp
    if st.session_state.start_date.date() < min_date_val:
        st.session_state.start_date = pd.to_datetime(min_date_val)
    elif st.session_state.start_date.date() > max_date_val: 
        st.session_state.start_date = pd.to_datetime(max_date_val)

# Initialize or validate st.session_state.end_date (as Timestamp)
if 'end_date' not in st.session_state:
    st.session_state.end_date = pd.to_datetime(max_date_val)
else:
    # Ensure it's a Timestamp if it exists
    if not isinstance(st.session_state.end_date, pd.Timestamp):
        st.session_state.end_date = pd.to_datetime(st.session_state.end_date)
    # Compare .date() part and clamp
    if st.session_state.end_date.date() > max_date_val:
        st.session_state.end_date = pd.to_datetime(max_date_val)
    elif st.session_state.end_date.date() < min_date_val: 
        st.session_state.end_date = pd.to_datetime(min_date_val)
            
# Ensure start_date <= end_date after clamping
if st.session_state.start_date > st.session_state.end_date:
    st.session_state.start_date = st.session_state.end_date
    
cols_date = st.columns(2)
with cols_date[0]:
    start_date_input = st.date_input(
        "Data Inicial",
        format="DD/MM/YYYY",
        value=st.session_state.start_date.date(), 
        min_value=min_date_val,
        max_value=max_date_val,
        key='start_date_picker'
    )
with cols_date[1]:
    end_date_input = st.date_input(
        "Data Final",
        format="DD/MM/YYYY",
        value=st.session_state.end_date.date(), 
        min_value=min_date_val,
        max_value=max_date_val,
        key='end_date_picker'
    )
    
# Update session state with Timestamps from the input (which are datetime.date objects)
st.session_state.start_date = pd.to_datetime(start_date_input)
st.session_state.end_date = pd.to_datetime(end_date_input)

if st.session_state.start_date > st.session_state.end_date: # Check after user input
    st.warning("Data inicial deve ser anterior à data final.")
    st.stop() 

# Initial selection for the chart and table: Persevera fund + benchmarks
initial_selection_cols = [persevera_fund_col_name]
if 'CDI' in combined_nav_data.columns: initial_selection_cols.append('CDI')
if 'Ibovespa' in combined_nav_data.columns: initial_selection_cols.append('Ibovespa')
if 'SMLL' in combined_nav_data.columns: initial_selection_cols.append('SMLL')

# Ensure only existing columns are selected
initial_selection_cols = [col for col in initial_selection_cols if col in combined_nav_data.columns]

# Allow user to select funds/benchmarks for the chart
all_available_funds_for_chart = list(combined_nav_data.columns)

# Set default selection: Persevera fund and available benchmarks
default_chart_selection = initial_selection_cols

selected_funds_for_chart = st.multiselect(
    "Selecione fundos/benchmarks para o gráfico:",
    options=all_available_funds_for_chart,
    default=default_chart_selection,
    key=f'chart_multiselect_{selected_fund_name}'
)

# Filter data for the selected date range and funds for the chart
chart_data_filtered = combined_nav_data.loc[
    st.session_state.start_date : st.session_state.end_date,
    selected_funds_for_chart
]

# Calculate and display performance chart
st.subheader("Performance Acumulada")
performance_to_plot = calculate_performance(chart_data_filtered) * 100
if not performance_to_plot.empty:
    perf_chart_options = create_chart(
        data=performance_to_plot,
        columns=list(performance_to_plot.columns),
        names=list(performance_to_plot.columns),
        chart_type='line',
        title="",
        y_axis_title="%",
        enable_fullscreen_on_dblclick=True
    )
    render_chart(perf_chart_options, key=f"perf_acumulada_{selected_fund_name}")
else:
    st.info("Não há dados de performance acumulada para exibir com os filtros selecionados.")

# Performance Table
st.subheader("Tabela de Performance")
performance_table_data = build_peer_performance_table(
    combined_nav_data,
    total_equity_data,
    st.session_state.start_date,
    st.session_state.end_date
)

if not performance_table_data.empty:
    styled_performance_table = style_table(
        performance_table_data.set_index('fund_name'),
        rank_cols_identifier='rank',
        numeric_cols_format_as_int=['PL'],
        numeric_cols_format_as_float=RETURN_COLS,
        date_cols=['ultima_cota'],
        date_format='%d/%m/%Y',
        highlight_quartile=RETURN_COLS,
        quartile_exclude_row_by_column='type',
        quartile_exclude_row_if_value_is=['Benchmark'],
        highlight_row_by_column='type',
        highlight_row_if_value_equals='Persevera',
        highlight_color='lightblue'
    )
    st.dataframe(styled_performance_table, width='stretch')

else:
    st.info("Não há dados para a tabela de performance com os filtros selecionados.")

# Retorno x Patrimônio Líquido
st.subheader("Retorno x Patrimônio Líquido")
period_selected = st.radio("Selecione o período:", RETURN_COLS, index=0, horizontal=True)

short_term_chart_options = create_chart(
    # data=performance_table_data.dropna(),
    data=performance_table_data.dropna(subset=['PL', period_selected]).filter(items=['fund_name', 'PL', period_selected]),
    columns=period_selected,
    names="Fundos",
    chart_type='scatter',
    title="",
    y_axis_title=f"Retorno {period_selected.upper()} (%)",
    x_axis_title="Patrimônio Líquido (R$)",
    x_column="PL",
    zoom_type="xy",
    point_name_column="fund_name",
    tooltip_point_format='<b>{point.name}</b><br/>Patrimônio Líquido: {point.x:,.0f}<br/>Retorno: {point.y:.2f}%'
)
hct.streamlit_highcharts(short_term_chart_options, key=f"scatter_1d_pl_{selected_fund_name}")

# Additional Statistics (Drawdown, Volatility, Net Equity)
st.subheader("Estatísticas Adicionais")

# Filter combined_nav_data for the selected funds for these stats
stats_data_selection = initial_selection_cols
stats_data_selection.remove('CDI')

stats_data_options = st.multiselect(
    "Selecione fundos/benchmarks para Estatísticas Adicionais:",
    options=all_available_funds_for_chart,
    default=stats_data_selection,
    key=f'stats_multiselect_{selected_fund_name}'
)

if not stats_data_options:
    st.info("Selecione fundos/benchmarks para as estatísticas adicionais.")
    
stats_data_filtered = combined_nav_data.loc[
    st.session_state.start_date : st.session_state.end_date,
    stats_data_options
].ffill()

if not stats_data_filtered.empty:
    tabs = st.tabs(["Drawdown", "Volatilidade (21d)", "Patrimônio Líquido", "Correlação (21d)"])

    with tabs[0]:   # Drawdown
        drawdown_data = (stats_data_filtered / stats_data_filtered.cummax() - 1) * 100
        if not drawdown_data.empty:
            drawdown_chart_options = create_chart(
                data=drawdown_data,
                columns=list(drawdown_data.columns),
                names=list(drawdown_data.columns),
                chart_type='area',
                title="",
                y_axis_title="%"
            )
            hct.streamlit_highcharts(drawdown_chart_options, key=f"drawdown_{selected_fund_name}")
        else:
            st.info("Não há dados de drawdown para exibir com os filtros selecionados.")

    with tabs[1]:   # Volatilidade Anualizada (Janela de 21 dias úteis)
        volatility_data = stats_data_filtered.pct_change().rolling(window=21).std() * np.sqrt(252) * 100
        if not volatility_data.empty:
            vol_chart_options = create_chart(
                data=volatility_data,
                columns=list(volatility_data.columns),
                names=list(volatility_data.columns),
                chart_type='line',
                title="",
                y_axis_title="%"
            )
            hct.streamlit_highcharts(vol_chart_options, key=f"volatility_{selected_fund_name}")
        else:
            st.info("Não há dados de volatilidade para exibir com os filtros selecionados.")

    with tabs[2]:   # Patrimônio Líquido
        persevera_pl_cols = [col for col in total_equity_data.columns if 'Persevera' in col]
        if persevera_pl_cols:
            pl_to_display = total_equity_data[persevera_pl_cols].copy()
            pl_to_display = pl_to_display.loc[st.session_state.start_date : st.session_state.end_date]
            if not pl_to_display.empty:
                pl_chart_options = create_chart(
                    data=pl_to_display,
                    columns=list(pl_to_display.columns),
                    names=list(pl_to_display.columns),
                    chart_type='area',
                    title="",
                    y_axis_title="Valor"
                )
                hct.streamlit_highcharts(pl_chart_options, key=f"pl_{selected_fund_name}")
            else:
                st.info("Dados de Patrimônio Líquido não disponíveis para o período selecionado.")
        else:
            st.info("Colunas de Patrimônio Líquido para os fundos Persevera não encontradas nos dados.")

    with tabs[3]:   # Correlação (Janela de 21 dias úteis)
        equity_groups = {"Nemesis", "Proteus", "Marujo"}
        if any(fname in equity_groups for fname in selected_fund_names):
            correlation_data = stats_data_filtered.iloc[:,0].pct_change().rolling(window=21).corr(stats_data_filtered.iloc[:,1:].pct_change())
            if not correlation_data.empty:
                correlation_chart_options = create_chart(
                    data=correlation_data,
                    columns=list(correlation_data.columns),
                    names=list(correlation_data.columns),
                    chart_type='line',
                    title="",
                    y_axis_title="Correlação",
                    x_axis_title="Data",
                    y_axis_max=1,
                    y_axis_min=-1
                )
                hct.streamlit_highcharts(correlation_chart_options, key=f"correlation_{selected_fund_name}")
            else:
                st.info("Não há dados de correlação para exibir com os filtros selecionados.")

    st.subheader("Correlação dos Fundos")
    correlation_matrix = combined_nav_data.pct_change(fill_method=None).corr()
    correlation_matrix = correlation_matrix.where(np.tril(np.ones(correlation_matrix.shape)).astype(np.bool_))

    # Define a altura do heatmap proporcional à quantidade de variáveis
    num_vars = correlation_matrix.shape[0]
    heatmap_height = max(300, num_vars * 30)  # 30px por variável, com altura mínima de 300px

    heatmap = create_chart(
        data=correlation_matrix,
        chart_type="heatmap",
        title="",
        height=heatmap_height
    )
    hct.streamlit_highcharts(heatmap, height=heatmap_height)

else:
    st.warning("Nenhum dado para calcular estatísticas adicionais com os filtros atuais.")