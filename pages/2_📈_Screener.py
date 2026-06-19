import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta, date

from utils.table import style_table
from utils.ui import display_logo, load_css
from utils.auth import check_authentication
from utils.chart_helpers import create_chart
import streamlit_highcharts as hct

from configs.pages.screener import (
    get_factor_options,
    get_factor_components,
    get_higher_is_better_map,
)

from persevera_tools.data import get_descriptors
from persevera_tools.db.operations import read_sql
from persevera_tools.db.fibery import read_fibery

st.set_page_config(
    page_title="Screener | Persevera",
    page_icon="📈",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

@st.cache_data(ttl=3600)
def load_descriptor_evolution(codes, descriptor, start_date) -> pd.DataFrame:
    try:
        result = get_descriptors(
            list(codes),
            start_date=start_date,
            descriptors=[descriptor],
        )
        if isinstance(result, pd.Series):
            return result.to_frame(name=codes[0])
        if isinstance(result.columns, pd.MultiIndex):
            return result.xs(descriptor, level="descriptor", axis=1)
        return result
    except Exception as e:
        st.error(f"Erro ao carregar evolução da métrica: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_data(start_date, descriptors_list) -> pd.DataFrame:
    try:
        df = read_fibery(
            table_name="Inv-Rsrch-Quant/Ações Ativas",
            include_fibery_fields=False,
        )
        df = df[df["Denominação"] == "BRL"]
        codes = df["Ativo"].tolist()

        query = f"""
            SELECT * FROM factor_zoo_latest
            WHERE code IN ('{"', '".join(codes)}')
            AND field IN ('{"', '".join(descriptors_list)}')
            AND date >= '{start_date}'
        """
        df = read_sql(query)
        return df.pivot(index='code', columns='field', values='value')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def calculate_factor_exposure(df, factor_name, higher_is_better_map=None) -> pd.DataFrame:
    """
    Calculate factor scores for all configured factors.

    The process follows these steps:
    1. Prepare factor data by aligning with universe
    2. Apply cross-sectional z-score standardization
    3. Handle outliers through winsorization
    4. Align signs so every component is "higher is better" before averaging
    5. Calculate final factor scores through equal-weighted average
    """
    try:
        # -- Outlier handling: Two-step outlier trimming process --
        # Step 1: Handle extreme outliers using robust statistics, column-wise
        zR = 3
        zC = 3

        median = df.median()
        robust_std = 1.4826 * (df - median).abs().median()
        
        df_trimmed = df.apply(
            lambda col: col.clip(lower=median[col.name] - zR * robust_std[col.name],
                                 upper=median[col.name] + zR * robust_std[col.name])
        )

        # Step 2: Handle remaining outliers using conventional statistics, column-wise
        mean = df_trimmed.mean()
        std = df_trimmed.std()
        
        df_trimmed = df_trimmed.apply(
            lambda col: col.clip(lower=mean[col.name] - zC * std[col.name],
                                 upper=mean[col.name] + zC * std[col.name])
        )

        # -- Standardization: Standardize series to equal-weighted unit std and cap-weighted zero mean --
        mean = df_trimmed.mean()
        std = df_trimmed.std()
        z_scores = (df_trimmed - mean) / std

        # -- Sign alignment: invert columns where lower values are preferred --
        if higher_is_better_map:
            for col in z_scores.columns:
                if not higher_is_better_map.get(col, True):
                    z_scores[col] = -z_scores[col]

        # -- Factor Exposure: Equal-weight individual standardized scores --
        factor_exposure = z_scores.mean(axis=1)

        return factor_exposure.to_frame(name=factor_name)

    except Exception as e:
        st.warning(f"Error calculating factor scores: {str(e)}")
        raise

st.title('Screener')

# Sidebar fields and factors definition
with st.sidebar:
    st.header("Parâmetros")

    adtv_filter = st.number_input(
        "ADTV Mínimo (21d):",
        min_value=0.0,
        value=8000000.0,
        step=500000.0,
        format="%.0f"
    )

    selected_cols_options = get_factor_options()
    factor_option_names = list(selected_cols_options.keys())

    descriptor_to_alias = {v: k for k, v in selected_cols_options.items()}
    default_selected_display_names = [
        descriptor_to_alias[desc] for desc in [
            'median_dollar_volume_traded_21d',
            'momentum_7d',
            'momentum_1m',
            'dividend_yield_fwd',
            'price_to_earnings_fwd',
            'ev_to_ebitda_fwd',
            'ebit_margin',
            'fcf_margin',
            'roe',
        ] if desc in descriptor_to_alias
    ]

    selected_display_names = st.multiselect("Selecione as métricas para exibir:", options=factor_option_names, default=default_selected_display_names)
    selected_momentum_components = st.multiselect("Componentes de Momentum:", options=factor_option_names, default=list(get_factor_components('Momentum').keys()))
    selected_value_components = st.multiselect("Componentes de Value:", options=factor_option_names, default=list(get_factor_components('Value').keys()))
    selected_liquidity_components = st.multiselect("Componentes de Liquidity:", options=factor_option_names, default=list(get_factor_components('Liquidity').keys()))
    selected_risk_components = st.multiselect("Componentes de Risk:", options=factor_option_names, default=list(get_factor_components('Risk').keys()))
    selected_quality_components = st.multiselect("Componentes de Quality:", options=factor_option_names, default=list(get_factor_components('Quality').keys()))

# Filter selected_cols based on user selection
selected_cols = {name: selected_cols_options[name] for name in selected_display_names}
selected_descriptors_list = list(selected_cols.values())

selected_cols_momentum = {name: selected_cols_options[name] for name in selected_momentum_components}
selected_descriptors_list_momentum = list(selected_cols_momentum.values())

selected_cols_value = {name: selected_cols_options[name] for name in selected_value_components}
selected_descriptors_list_value = list(selected_cols_value.values())

selected_cols_liquidity = {name: selected_cols_options[name] for name in selected_liquidity_components}
selected_descriptors_list_liquidity = list(selected_cols_liquidity.values())

selected_cols_risk = {name: selected_cols_options[name] for name in selected_risk_components}
selected_descriptors_list_risk = list(selected_cols_risk.values())

selected_cols_quality = {name: selected_cols_options[name] for name in selected_quality_components}
selected_descriptors_list_quality = list(selected_cols_quality.values())

all_cols = selected_descriptors_list + selected_descriptors_list_momentum + selected_descriptors_list_value + selected_descriptors_list_liquidity + selected_descriptors_list_risk + selected_descriptors_list_quality
all_cols = list(dict.fromkeys(all_cols))

def keep_available_columns(columns, source_df):
    return [col for col in columns if col in source_df.columns]

# Load data
with st.spinner("Carregando dados das empresas...", show_time=True):
    data_load_date = (pd.to_datetime(date.today()) - timedelta(days=360)).strftime('%Y-%m-%d')
    raw_data = load_data(start_date=data_load_date, descriptors_list=all_cols)

if not raw_data.empty:

    # Apply ADTV filter if 'median_dollar_volume_traded_21d' is in the columns
    if 'median_dollar_volume_traded_21d' in raw_data.columns and adtv_filter > 0:
        raw_data = raw_data[raw_data['median_dollar_volume_traded_21d'] >= adtv_filter]

    # Ensure only selected descriptors are present before renaming
    data = raw_data[selected_descriptors_list] 

    # Rename columns to display names
    inverted_selected_cols = {v: k for k, v in selected_cols.items()}
    data = data.rename(columns=inverted_selected_cols)

    # Include factor exposures (sign alignment driven by `Maior Melhor` in FACTOR_DEFINITIONS)
    higher_is_better_map = get_higher_is_better_map()
    factor_exposure_momentum = calculate_factor_exposure(raw_data[selected_descriptors_list_momentum], 'Momentum Score', higher_is_better_map)
    factor_exposure_value = calculate_factor_exposure(raw_data[selected_descriptors_list_value], 'Value Score', higher_is_better_map)
    factor_exposure_liquidity = calculate_factor_exposure(raw_data[selected_descriptors_list_liquidity], 'Liquidity Score', higher_is_better_map)
    factor_exposure_risk = calculate_factor_exposure(raw_data[selected_descriptors_list_risk], 'Risk Score', higher_is_better_map)
    factor_exposure_quality = calculate_factor_exposure(raw_data[selected_descriptors_list_quality], 'Quality Score', higher_is_better_map)

    data = pd.concat([data, factor_exposure_momentum, factor_exposure_value, factor_exposure_liquidity, factor_exposure_risk, factor_exposure_quality], axis=1)

    # Apply styling
    factor_cols = ['Momentum Score', 'Value Score', 'Liquidity Score', 'Risk Score', 'Quality Score']
    cols = factor_cols + [col for col in data.columns if col not in factor_cols]
    data = data[cols]

    # Ensure 'ADTV (21d)' and 'Momentum (1m)' come first if present
    first_cols = ['ADTV (21d)', '7-day Momentum', '1-Month Momentum']
    first_cols = [col for col in first_cols if col in data.columns]
    remaining_cols = [col for col in data.columns if col not in first_cols]
    data = data[first_cols + remaining_cols]
    
    styled_data = style_table(
        data,
        numeric_cols_format_as_int=['ADTV (21d)'],
        numeric_cols_format_as_float=list(data.columns.drop('ADTV (21d)')),
        currency_cols=['ADTV (21d)'],
        highlight_quartile=['Momentum Score', 'Value Score', 'Liquidity Score', 'Risk Score', 'Quality Score'],
        color_negative_positive_cols=list(data.columns.drop(['ADTV (21d)', 'Momentum Score', 'Value Score', 'Liquidity Score', 'Risk Score', 'Quality Score'])),
    )
    st.write(styled_data)

    with st.expander("Evolução de Métricas", expanded=False):
        row_1 = st.columns([1, 3])
        with row_1[0]:
            chart_descriptor_display = st.selectbox(
                "Métrica",
                options=factor_option_names,
                key="screener_chart_descriptor",
            )
            chart_descriptor = selected_cols_options[chart_descriptor_display]
            
        with row_1[1]:
            available_codes = sorted(data.index.tolist())
            chart_tickers = st.multiselect(
                "Ativos",
                options=available_codes,
                default=[],
                key="screener_chart_tickers",
            )
        
        row_2 = st.columns([1, 3])
        with row_2[0]:
            start_date = st.date_input(
                "Data inicial",
                value=pd.to_datetime("2010-01-01"),
                min_value=pd.to_datetime("2010-01-01"),
                max_value=pd.to_datetime(date.today()),
                format="DD/MM/YYYY",
            )

        generate_chart = st.button("Gerar gráfico", disabled=len(chart_tickers) == 0)

        if generate_chart:
            st.session_state.screener_chart_request = {
                "descriptor": chart_descriptor,
                "descriptor_display": chart_descriptor_display,
                "tickers": list(chart_tickers),
            }

        chart_request = st.session_state.get("screener_chart_request")
        if chart_request:
            with st.spinner("Carregando série histórica...", show_time=True):
                chart_data = load_descriptor_evolution(
                    tuple(chart_request["tickers"]),
                    chart_request["descriptor"],
                    start_date=pd.to_datetime(start_date),
                )

            if chart_data.empty:
                st.warning("Não há dados históricos para a seleção.")
            else:
                chart_data = chart_data.dropna(how="all")
                hct.streamlit_highcharts(
                    create_chart(
                        data=chart_data,
                        columns=list(chart_data.columns),
                        names=list(chart_data.columns),
                        chart_type="line",
                        title=chart_request["descriptor_display"],
                        y_axis_title=chart_request["descriptor_display"],
                        x_axis_title="Data",
                        decimal_precision=2,
                    ),
                    key="screener_descriptor_evolution",
                )

else:
    st.warning("No data available for the selected metrics and date.")
