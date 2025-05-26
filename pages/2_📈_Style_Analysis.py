import streamlit as st
import os

st.set_page_config(
    page_title="Style Analysis | Persevera",
    page_icon="📈",
    layout="wide"
)

# Inclusão do CSS
assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
css_path = os.path.join(assets_dir, 'style.css')
with open(css_path) as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.title("Style Analysis")
