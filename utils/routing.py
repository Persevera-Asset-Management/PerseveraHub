"""Persistência de rota entre F5 — workaround para limitações do st.navigation.

Streamlit + proxy podem redirecionar subpaths (ex. /equities_valuation) para /
no reload. Espelhamos o slug da página em ``?page=`` (sempre servido na raiz)
e restauramos via ``st.switch_page``.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from utils.navigation import _iter_pages

PAGE_QUERY_KEY = "page"


def _find_page_by_slug(
    pages: dict[str, list[st.Page]], slug: str
) -> st.Page | None:
    for page in _iter_pages(pages):
        if page.url_path == slug:
            return page
    return None


def route_to_requested_page(
    current_page: st.Page,
    pages: dict[str, list[st.Page]],
) -> None:
    """Navega para a página pedida na URL (query param ou path do Streamlit)."""
    slug = st.query_params.get(PAGE_QUERY_KEY)

    if not slug:
        from streamlit.runtime.scriptrunner_utils.script_run_context import (
            get_script_run_ctx,
        )

        ctx = get_script_run_ctx()
        if ctx:
            slug = ctx.pages_manager.intended_page_name or None

    if not slug or current_page.url_path == slug:
        return

    target = _find_page_by_slug(pages, slug)
    if target:
        st.switch_page(target)


def sync_browser_url(slug: str | None) -> None:
    """Espelha o slug da página ativa em ``/?page=<slug>`` para sobreviver ao F5."""
    components.html(
        f"""
        <script>
        (function () {{
            const KEY = "{PAGE_QUERY_KEY}";
            const SLUG = {slug!r};
            const win = window.parent;
            const loc = win.location;

            function sync() {{
                const params = new URLSearchParams(loc.search);
                const fromQuery = params.get(KEY);
                const fromPath = loc.pathname.replace(/^\\/+/, "").split("/")[0];

                let slug = SLUG || fromQuery || fromPath || "";
                if (slug) {{
                    sessionStorage.setItem("persevera_" + KEY, slug);
                    if (fromQuery !== slug) {{
                        params.set(KEY, slug);
                        loc.replace("/?" + params.toString());
                    }}
                }} else if (fromQuery) {{
                    sessionStorage.removeItem("persevera_" + KEY);
                }} else {{
                    const saved = sessionStorage.getItem("persevera_" + KEY);
                    if (saved && loc.pathname.replace(/^\\/+/, "") === "") {{
                        params.set(KEY, saved);
                        loc.replace("/?" + params.toString());
                    }}
                }}
            }}

            sync();
            setInterval(sync, 1000);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )
