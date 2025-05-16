import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Persevera Dashboard - Meetings: Timing",
    page_icon="🗓️",
    layout="wide"
)

# Common meetings header with navigation links
st.title("Meetings Dashboard: Timing")

# Create tabs for different meeting views
tabs = st.tabs(["Calendar", "Meeting Notes", "Action Items", "Documents"])

# Tab 1: Calendar
with tabs[0]:
    st.subheader("Estratégia Meetings Calendar")

# Tab 2: Meeting Notes
with tabs[1]:
    st.subheader("Estratégia Meeting Notes")

# Tab 3: Action Items
with tabs[2]:
    st.subheader("Estratégia Action Items")

# Tab 4: Documents
with tabs[3]:
    st.subheader("Estratégia Documents") 