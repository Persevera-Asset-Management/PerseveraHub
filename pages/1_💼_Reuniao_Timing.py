import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Reunião Timing & Awareness | Persevera",
    page_icon="🗓️",
    layout="wide"
)

# Inclusão do CSS
assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
css_path = os.path.join(assets_dir, 'style.css')
with open(css_path) as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.title('Reunião Timing & Awareness')