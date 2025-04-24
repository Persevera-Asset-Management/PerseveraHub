import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure assets directory exists
assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
if not os.path.exists(assets_dir):
    os.makedirs(assets_dir)

# Configure the page
st.set_page_config(
    page_title="Persevera Dashboard",
    page_icon="��",
    layout="wide"
)

# Add custom CSS
css_path = os.path.join(assets_dir, 'style.css')
try:
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    # Fallback CSS if file not found
    st.markdown("""
    <style>
    body {
        font-family: sans-serif;
    }
    h1 {
        color: #2C74B3;
    }
    .sidebar .sidebar-content {
        background-color: #f5f5f5;
    }
    </style>
    """, unsafe_allow_html=True)

# Main content
st.title("Persevera Asset Management")
st.write("This dashboard provides tools and analytics for financial analysis across different asset classes.")

# Footer
st.info("© 2025 Persevera Asset Management") 
