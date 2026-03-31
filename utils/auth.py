import streamlit as st
import streamlit_authenticator as stauth

def initialize_authenticator():
    if 'authenticator' not in st.session_state:
        credentials = {"usernames": {
            username: dict(data)
            for username, data in st.secrets["credentials"]["usernames"].items()
        }}
        cookie = st.secrets["cookie"]

        authenticator = stauth.Authenticate(
            credentials,
            cookie["name"],
            cookie["key"],
            cookie["expiry_days"],
        )
        st.session_state.authenticator = authenticator
    return st.session_state.authenticator

def login_form():
    authenticator = initialize_authenticator()
    authenticator.login()

    if st.session_state["authentication_status"] is False:
        st.error('Nome de usuário/senha está incorreto')
    elif st.session_state["authentication_status"] is None:
        st.warning('Por favor, insira seu nome de usuário e senha')

def check_authentication():
    if 'authentication_status' not in st.session_state or st.session_state.authentication_status is not True:
        login_form()
        st.stop()
    
    # User is authenticated, show logout and return authenticator
    authenticator = initialize_authenticator()
    authenticator.logout('Logout', 'sidebar')
    return authenticator 

def custom_logout():
    """Logs the user out without rendering a button."""
    if 'authenticator' in st.session_state:
        st.session_state.authenticator._logout_logic() 