import streamlit as st
from datetime import datetime

def display_logo():
    """Displays the Persevera logos in the sidebar and header."""
    st.logo("assets/logo_sidebar.png", icon_image="assets/logo_header.png")

def load_css():
    """Loads the custom CSS file."""
    import os
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
    css_path = os.path.join(assets_dir, 'style.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def track_data_load(key: str):
    """Records the timestamp when data is loaded. Call this after each data load."""
    st.session_state[f"_data_loaded_{key}"] = datetime.now()

def show_data_freshness(key: str, label: str = "Dados", ttl_minutes: int = 60):
    """Displays when data was last loaded and the cache TTL."""
    ts: datetime | None = st.session_state.get(f"_data_loaded_{key}")
    if ts:
        elapsed = int((datetime.now() - ts).total_seconds() / 60)
        expires_in = max(0, ttl_minutes - elapsed)
        st.caption(
            f"⏱ {label} · Carregado às {ts.strftime('%H:%M')} · "
            f"Cache expira em {expires_in} min"
        )
    else:
        st.caption(f"⏱ {label} · Aguardando carregamento...")