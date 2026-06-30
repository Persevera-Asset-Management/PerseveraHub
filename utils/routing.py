"""Persistência de rota entre F5 — workaround para limitações do st.navigation.

Streamlit + proxy podem redirecionar subpaths (ex. /equities_valuation) para /
no reload. Mantemos a URL canônica como ``/?page=<slug>`` (sempre servida na
raiz, portanto sobrevive ao proxy e é compartilhável):

- ``sync_browser_url`` (JS): colapsa o path ``/<slug>`` que o Streamlit insere de
  volta para ``/?page=<slug>`` via ``replaceState`` e guarda o slug no
  ``sessionStorage`` como fallback.
- ``route_to_requested_page`` (Python): na carga inicial da sessão (ou F5), lê
  ``?page=`` e navega via ``st.switch_page``; nos reruns seguintes não interfere,
  para não atropelar a navegação do usuário.
"""

from __future__ import annotations

import streamlit as st

from utils.navigation import _iter_pages

PAGE_QUERY_KEY = "page"


def _find_page_by_slug(
    pages: dict[str, list[st.Page]], slug: str
) -> st.Page | None:
    for page in _iter_pages(pages):
        if page.url_path == slug:
            return page
    return None


_ROUTED_FLAG = "_page_routed"


def route_to_requested_page(
    current_page: st.Page,
    pages: dict[str, list[st.Page]],
) -> None:
    """Navega para a página pedida em ``?page=`` apenas na carga inicial da sessão.

    O ``?page=`` é o estado compartilhável/persistente da URL (mantido pelo JS de
    ``sync_browser_url``). Se reagíssemos a ele em todo rerun, clicar em "Home"
    com ``?page=X`` ainda na URL nos jogaria de volta para X. Por isso só roteamos
    uma vez por sessão — ou seja, na primeira execução após uma carga/F5 — e
    deixamos a navegação interna do usuário livre nos reruns seguintes.
    """
    if st.session_state.get(_ROUTED_FLAG):
        return
    st.session_state[_ROUTED_FLAG] = True

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
    """Mantém a URL canônica em ``/?page=<slug>`` (raiz + query).

    ``slug`` é a página ativa segundo o Streamlit (``pg.url_path``; vazio = Home).
    O Streamlit, ao navegar, insere o path ``/<slug>`` na barra; aqui o colapsamos
    de volta para ``/?page=<slug>`` via ``replaceState`` (sem recarregar), para que
    a URL seja sempre compartilhável e sobreviva ao proxy no F5. Também guardamos o
    slug no ``sessionStorage`` para restaurar a página caso o proxy derrube o path.
    """
    current = slug or ""
    st.html(
        f"""
        <script>
        (function () {{
            const KEY = "{PAGE_QUERY_KEY}";
            const STORE = "persevera_" + KEY;
            const SLUG = {current!r};
            const win = window.parent;
            const loc = win.location;
            const hist = win.history;

            function pathSlug() {{
                return loc.pathname.replace(/^\\/+/, "").split("/")[0];
            }}

            const firstLoad = !win.__perseveraRouter;
            win.__perseveraRouter = true;

            // Carga nova que caiu na raiz sem ?page (proxy derrubou o path):
            // restaura a última página salva recarregando com ?page=<slug>,
            // para o Python re-rotear. Só no primeiro load para não brigar com
            // uma ida intencional à Home (que limpa o STORE).
            if (firstLoad && !SLUG && pathSlug() === "") {{
                const params = new URLSearchParams(loc.search);
                const target = params.get(KEY) || sessionStorage.getItem(STORE);
                if (target) {{
                    params.set(KEY, target);
                    loc.replace("/?" + params.toString());
                    return;
                }}
            }}

            // Reescreve a barra para a forma canônica raiz+query, sem recarregar.
            function canonicalize() {{
                const params = new URLSearchParams(loc.search);
                if (SLUG) {{
                    sessionStorage.setItem(STORE, SLUG);
                    params.set(KEY, SLUG);
                    const desired = "/?" + params.toString();
                    if (loc.pathname + loc.search !== desired) {{
                        hist.replaceState(null, "", desired);
                    }}
                }} else {{
                    // Home: remove o ?page e a memória.
                    sessionStorage.removeItem(STORE);
                    if (params.has(KEY)) {{
                        params.delete(KEY);
                        const qs = params.toString();
                        hist.replaceState(null, "", "/" + (qs ? "?" + qs : ""));
                    }}
                }}
            }}

            canonicalize();
            if (win.__perseveraTimer) {{
                clearInterval(win.__perseveraTimer);
            }}
            win.__perseveraTimer = setInterval(canonicalize, 1000);
        }})();
        </script>
        """,
        width="content",
        unsafe_allow_javascript=True,
    )
