import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

def initialize_authenticator():
    if 'authenticator' not in st.session_state:
        with open('config.yaml') as file:
            config = yaml.load(file, Loader=SafeLoader)

        authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days']
        )
        st.session_state.authenticator = authenticator
    return st.session_state.authenticator

def login_form():
    authenticator = initialize_authenticator()
    authenticator.login()

    if st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')

def check_authentication():
    if 'authentication_status' not in st.session_state or st.session_state.authentication_status is not True:
        login_form()
        st.stop()
    
    # User is authenticated, show logout and return authenticator
    authenticator = initialize_authenticator()
    authenticator.logout('Logout', 'sidebar')
    return authenticator 