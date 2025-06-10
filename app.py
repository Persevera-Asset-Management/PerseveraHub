import streamlit as st
import os
from dotenv import load_dotenv
from utils.ui import display_logo, load_css

# Load environment variables
load_dotenv()

# Configure the page
st.set_page_config(
    page_title="Persevera Hub",
    page_icon="assets/logo_page.png",
    layout="wide"
)

display_logo()
load_css()

# Main content
st.title("Persevera Asset Management")
# st.write("This dashboard provides tools and analytics for financial analysis across different asset classes.")

# Footer
st.info("© 2025 Persevera Asset Management") 
