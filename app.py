import streamlit as st
from dotenv import load_dotenv

from utils.auth import (
    get_current_username,
    initialize_authenticator,
    login_form,
    render_sidebar_controls,
)
from utils.navigation import build_navigation_pages
from utils.ui import display_logo, load_css

load_dotenv()

st.set_page_config(
    page_title="Dashboard | Persevera",
    page_icon="assets/logo_page.png",
    layout="wide",
)

display_logo()
load_css()

if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = None

if not st.session_state.authentication_status:
    login_form()
    st.stop()

initialize_authenticator()
render_sidebar_controls()


def render_home() -> None:
    st.title("Persevera Asset Management")
    import persevera_tools

    st.markdown(
        f"Versão atual: ```persevera_tools v{persevera_tools.__version__}```"
    )
    st.info("© 2026 Persevera Asset Management")


home = st.Page(
    render_home,
    title="Home",
    icon=":material/home:",
    default=True,
)
pages = build_navigation_pages(home, username=get_current_username())
pg = st.navigation(pages, position="top")
pg.run()
