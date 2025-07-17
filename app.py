import streamlit as st
import os
from dotenv import load_dotenv
from utils.ui import display_logo, load_css
from utils.auth import login_form, initialize_authenticator

# Load environment variables
load_dotenv()

# Configure the page
st.set_page_config(
    page_title="Ficha Cadastral | Persevera",
    page_icon="assets/logo_page.png",
    layout="wide"
)

display_logo()
load_css()

if 'authentication_status' not in st.session_state:
    st.session_state.authentication_status = None

if st.session_state.authentication_status:
    authenticator = initialize_authenticator()
    authenticator.logout('Logout', 'sidebar')

    # Main content
    st.title("Persevera Asset Management")
    # st.write("This dashboard provides tools and analytics for financial analysis across different asset classes.")

    # Footer
    st.info("© 2025 Persevera Asset Management")
else:
    login_form()
