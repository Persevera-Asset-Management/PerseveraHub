import streamlit as st
from dotenv import load_dotenv

from utils.auth import (
    ensure_session,
    get_current_username,
    login_form,
    render_sidebar_controls,
)
from utils.navigation import build_navigation_pages, reconcile_intended_page
from utils.ui import display_logo, load_css

load_dotenv()

st.set_page_config(
    page_title="Dashboard | Persevera",
    page_icon="assets/logo_page.png",
    layout="wide",
)

display_logo()
load_css()

ensure_session()


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

if not st.session_state.get("authentication_status"):
    login_form()
    st.stop()

render_sidebar_controls()
reconcile_intended_page(pg, pages)
pg.run()
