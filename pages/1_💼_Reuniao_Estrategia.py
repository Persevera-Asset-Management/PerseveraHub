import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from utils.auth import check_authentication
from utils.ui import display_logo, load_css

st.set_page_config(
    page_title="Reunião Estratégia | Persevera",
    page_icon="🗓️",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title('Reunião Estratégia')