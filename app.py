import streamlit as st
import os
from dotenv import load_dotenv
from utils.ui import display_logo, load_css
from utils.auth import login_form, initialize_authenticator, custom_logout

# Load environment variables
load_dotenv()

# Configure the page
st.set_page_config(
    page_title="Dashboard | Persevera",
    page_icon="assets/logo_page.png",
    layout="wide"
)

display_logo()
load_css()

if 'authentication_status' not in st.session_state:
    st.session_state.authentication_status = None

if st.session_state.authentication_status:
    authenticator = initialize_authenticator()
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button('Logout'):
            custom_logout()
            st.rerun()

    with col2:
        if st.button("Clear Cache"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.toast("Cache cleared successfully!")
            st.rerun()

    # Main content
    st.title("Persevera Asset Management")
    import persevera_tools
    st.markdown(f"Versão atual: ```persevera_tools v{persevera_tools.__version__}```")

    # st.write("This dashboard provides tools and analytics for financial analysis across different asset classes.")

    # Footer
    st.info("© 2026 Persevera Asset Management")
else:
    login_form()
