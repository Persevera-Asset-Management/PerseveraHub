import streamlit as st
import streamlit_authenticator as stauth


def initialize_authenticator():
    if "authenticator" not in st.session_state:
        credentials = {
            "usernames": {
                username: dict(data)
                for username, data in st.secrets["credentials"]["usernames"].items()
            }
        }
        cookie = st.secrets["cookie"]

        authenticator = stauth.Authenticate(
            credentials,
            cookie["name"],
            cookie["key"],
            cookie["expiry_days"],
        )
        st.session_state.authenticator = authenticator
    return st.session_state.authenticator


def ensure_session() -> None:
    """Restaura sessão via cookie antes do roteamento de páginas.

    Após F5, o Streamlit zera o session state. O cookie de auth precisa ser
    lido antes de ``st.navigation`` registrar as páginas, senão a URL atual não
    é resolvida e o app cai na Home (``default=True``).
    """
    authenticator = initialize_authenticator()

    if st.session_state.get("authentication_status"):
        return

    authenticator.login(location="unrendered")

    if st.session_state.get("authentication_status"):
        st.rerun()


def login_form():
    authenticator = initialize_authenticator()

    if st.session_state.get("authentication_status"):
        return

    authenticator.login()

    if st.session_state["authentication_status"] is False:
        st.error("Nome de usuário/senha está incorreto")
    elif st.session_state["authentication_status"] is None:
        st.warning("Por favor, insira seu nome de usuário e senha")

def check_authentication():
    """Mantido por compatibilidade; auth é centralizada em app.py."""
    if (
        "authentication_status" not in st.session_state
        or st.session_state.authentication_status is not True
    ):
        st.stop()
    return initialize_authenticator()


def render_sidebar_controls() -> None:
    """Logout e limpeza de cache — exibidos na sidebar de todas as páginas."""
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Logout", width="stretch"):
            custom_logout()
            st.rerun()
    with col2:
        if st.button("Clear Cache", width="stretch"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.toast("Cache cleared successfully!")
            st.rerun()

def get_current_username() -> str | None:
    return st.session_state.get("username")


def custom_logout():
    """Logs the user out without rendering a button."""
    if "authenticator" in st.session_state:
        st.session_state.authenticator._logout_logic()