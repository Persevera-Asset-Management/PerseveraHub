import streamlit as st

def display_logo():
    """Displays the Persevera logos in the sidebar and header."""
    st.logo("assets/logo_sidebar.png", icon_image="assets/logo_header.png")

def load_css():
    """Loads the custom CSS file."""
    import os
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
    css_path = os.path.join(assets_dir, 'style.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True) 