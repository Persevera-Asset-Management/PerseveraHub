import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from configs.pages.screener import FACTOR_OPTIONS_SCREENER, FACTOR_MOMENTUM_COMPONENTS, FACTOR_VALUE_COMPONENTS, FACTOR_LIQUIDITY_COMPONENTS, FACTOR_RISK_COMPONENTS, FACTOR_QUALITY_COMPONENTS
from utils.table import style_table
from persevera_tools.data import get_descriptors, get_securities_by_exchange, get_equities_info
from utils.ui import display_logo, load_css

st.set_page_config(
    page_title="Screener | Persevera",
    page_icon="📈",
    layout="wide"
)

display_logo()
load_css()

@st.cache_data(ttl=3600)
def load_data(start_date, descriptors_list):
    try:
        codes = get_securities_by_exchange(exchange='BZ').values()
        return get_descriptors(list(codes), start_date=start_date, descriptors=descriptors_list)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_sectors(codes):
    try:
        return get_equities_info(codes)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def calculate_factor_exposure(df, factor_name) -> pd.DataFrame:
    """
    Calculate factor scores for all configured factors.
    
    The process follows these steps:
    1. Prepare factor data by aligning with universe
    2. Apply cross-sectional z-score standardization
    3. Handle outliers through winsorization
    4. Apply sector-relative normalization if configured
    5. Calculate final factor scores through ranking
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

        # -- Factor Exposure: Equal-weight individual standardized scores --
        factor_exposure = z_scores.mean(axis=1)

        return factor_exposure.to_frame(name=factor_name)

    except Exception as e:
        st.warning(f"Error calculating factor scores: {str(e)}")
        raise

st.title('Screener')

selected_cols_options = FACTOR_OPTIONS_SCREENER
default_selected_display_names = ['ADTV (21d)', 'Momentum (1m)', 'P/E Fwd', 'EV/EBITDA Fwd', 'EBIT Margin (%)', 'FCF Margin (%)', 'ROE (%)']

# Sidebar fields and factors definition
st.sidebar.header("Filtros")

adtv_filter = st.sidebar.number_input(
    "ADTV Mínimo (21d):",
    min_value=0.0,
    value=8000000.0,
    step=500000.0,
    format="%.0f"
)

selected_display_names = st.sidebar.multiselect(
    "Selecione as métricas para exibir:",
    options=list(selected_cols_options.keys()),
    default=default_selected_display_names
)

selected_momentum_components = st.sidebar.multiselect(
    "Componentes de Momentum:",
    options=list(selected_cols_options.keys()),
    default=list(FACTOR_MOMENTUM_COMPONENTS.keys())
)

selected_value_components = st.sidebar.multiselect(
    "Componentes de Value:",
    options=list(selected_cols_options.keys()),
    default=list(FACTOR_VALUE_COMPONENTS.keys())
)

selected_liquidity_components = st.sidebar.multiselect(
    "Componentes de Liquidity:",
    options=list(selected_cols_options.keys()),
    default=list(FACTOR_LIQUIDITY_COMPONENTS.keys())
)

selected_risk_components = st.sidebar.multiselect(
    "Componentes de Risk:",
    options=list(selected_cols_options.keys()),
    default=list(FACTOR_RISK_COMPONENTS.keys())
)

selected_quality_components = st.sidebar.multiselect(
    "Componentes de Quality:",
    options=list(selected_cols_options.keys()),
    default=list(FACTOR_QUALITY_COMPONENTS.keys())
)

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

# Load data
data_load_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
raw_data = load_data(start_date=data_load_date, descriptors_list=all_cols)

if not raw_data.empty:
    raw_data = raw_data.ffill()
    raw_data = raw_data.iloc[-1].reset_index()
    raw_data.columns = ['ticker', 'descriptor', 'value']
    raw_data = raw_data.pivot(index='ticker', columns='descriptor', values='value')

    # Apply ADTV filter if 'median_dollar_volume_traded_21d' is in the columns
    if 'median_dollar_volume_traded_21d' in raw_data.columns and adtv_filter > 0:
        raw_data = raw_data[raw_data['median_dollar_volume_traded_21d'] >= adtv_filter]

    # Ensure only selected descriptors are present before renaming
    data = raw_data[selected_descriptors_list] 

    # Rename columns to display names
    inverted_selected_cols = {v: k for k, v in selected_cols.items()}
    data = data.rename(columns=inverted_selected_cols)

    # Load and merge sector data
    all_codes = list(get_securities_by_exchange(exchange='BZ').values())
    sector_data = load_sectors(all_codes)
    if not sector_data.empty and 'sector_name_pt' in sector_data.columns:
        sector_data_to_merge = sector_data[['sector_name_pt']].copy()
        data = pd.merge(data, sector_data_to_merge, left_index=True, right_index=True, how='left')
        data = data.rename(columns={'sector_name_pt': 'Setor'})
        
        if 'Setor' in data.columns:
            cols = ['Setor'] + [col for col in data.columns if col != 'Setor']
            data = data[cols]
    
    # Include factor exposures
    factor_exposure_momentum = calculate_factor_exposure(raw_data[selected_descriptors_list_momentum], 'Momentum Score')
    factor_exposure_value = calculate_factor_exposure(raw_data[selected_descriptors_list_value], 'Value Score')
    factor_exposure_liquidity = calculate_factor_exposure(raw_data[selected_descriptors_list_liquidity], 'Liquidity Score')
    factor_exposure_risk = calculate_factor_exposure(raw_data[selected_descriptors_list_risk], 'Risk Score')
    factor_exposure_quality = calculate_factor_exposure(raw_data[selected_descriptors_list_quality], 'Quality Score')

    data = pd.concat([data, factor_exposure_momentum, factor_exposure_value, factor_exposure_liquidity, factor_exposure_risk, factor_exposure_quality], axis=1)

    # Apply styling
    factor_cols = ['Momentum Score', 'Value Score', 'Liquidity Score', 'Risk Score', 'Quality Score']
    cols = factor_cols + [col for col in data.columns if col not in factor_cols]
    data = data[cols]

    # Ensure 'ADTV (21d)' and 'Momentum (1m)' come first if present
    first_cols = ['ADTV (21d)', 'Momentum (1m)']
    first_cols = [col for col in first_cols if col in data.columns]
    remaining_cols = [col for col in data.columns if col not in first_cols]
    data = data[first_cols + remaining_cols]
    
    styled_data = style_table(
        data,
        numeric_cols_format_as_int=['ADTV (21d)'],
        numeric_cols_format_as_float=list(data.columns.drop('ADTV (21d)')),
        currency_cols=['ADTV (21d)'],
        highlight_quartile=['Momentum Score', 'Value Score', 'Liquidity Score', 'Risk Score', 'Quality Score']
    )
    st.write(styled_data)

else:
    st.warning("No data available for the selected metrics and date.")
