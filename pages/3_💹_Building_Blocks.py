import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
import datetime
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication
from persevera_tools.data.sma import get_building_blocks

st.set_page_config(
    page_title="Building Blocks | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Building Blocks")

building_blocks_dict = {
    # Renda Fixa
    'IMA-B': 'anbima_ima_b',
    'IMA-B 5': 'anbima_ima_b5',
    'IMA-B 5+': 'anbima_ima_b5+',
    'IRF-M': 'anbima_irf_m',
    'IRF-M 1+': 'anbima_irf_m1+',

    # Renda Variável BR
    'Ibovespa': 'br_ibovespa',
    'SMLL': 'br_smll',
    'IBr-X 100': 'br_ibx100',
    'IBr-X 50': 'br_ibx50',

    # Renda Variável US
    'Nasdaq-100': 'us_nasdaq100',
    'S&P 500': 'us_sp500',
    
    # Commodities
    'Ouro': 'gold_100oz_futures',

    # Alternativos
    'Bitcoin': 'bitcoin_usd',
    'IFIX': 'br_ifix',
}

building_blocks_df = get_building_blocks()

for block in building_blocks_dict:
    with st.expander(block):
        st.dataframe(
            style_table(
                building_blocks_df[building_blocks_df['reference'] == block].drop(columns=['reference']),
                column_names=['Instrumento', 'Código', 'Nome', 'Hedge Cambial?'],
            ),
            hide_index=True,
        )
