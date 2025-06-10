import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
import datetime
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css

st.set_page_config(
    page_title="Visualizador de Portfolio | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()

st.title("Visualizador de Portfolio")
