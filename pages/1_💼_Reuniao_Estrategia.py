import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from utils.ui import display_logo, load_css

st.set_page_config(
    page_title="Reunião Estratégia | Persevera",
    page_icon="🗓️",
    layout="wide"
)

display_logo()
load_css()

st.title('Reunião Estratégia')