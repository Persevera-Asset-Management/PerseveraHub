import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the page
st.set_page_config(
    page_title="Persevera Hub",
    page_icon="assets/logo.svg",
    layout="wide"
)

# Add custom CSS
assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
css_path = os.path.join(assets_dir, 'style.css')
with open(css_path) as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Main content
st.title("Persevera Asset Management")
# st.write("This dashboard provides tools and analytics for financial analysis across different asset classes.")

# Footer
st.info("© 2025 Persevera Asset Management") 
