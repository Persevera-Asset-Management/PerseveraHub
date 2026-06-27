"""Registro automático de páginas para st.navigation."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import streamlit as st

from configs.navigation import HOME_SECTION, ROLE_SECTIONS, SECTIONS

_PAGE_FILENAME_RE = re.compile(r"^(\d+)_(.+)\.py$", re.UNICODE)
_EMOJI_PREFIX_RE = re.compile(r"^[^\w\s·&]+_(.+)$", re.UNICODE)


def _page_title(identifier: str) -> str:
    return identifier.replace("_", " ")


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    slug = re.sub(r"[^\w]+", "-", ascii_text.lower(), flags=re.UNICODE)
    return re.sub(r"-+", "-", slug).strip("-") or "page"


def _url_path(section_num: str, identifier: str) -> str:
    """
    Gera pathname no estilo seção/página.

    Streamlit não aceita '/' em url_path (levanta StreamlitAPIException).
    Usamos hífen como separador: analise/screener → analise-screener.
    """
    section_slug = SECTIONS[section_num]["slug"]
    return f"{section_slug}_{_slugify(identifier)}"


def _parse_page_filename(filename: str) -> tuple[str, str] | None:
    """Extrai seção numérica e identificador da página (ignora emoji no nome do arquivo)."""
    match = _PAGE_FILENAME_RE.match(filename)
    if not match:
        return None

    section_num, rest = match.groups()
    emoji_match = _EMOJI_PREFIX_RE.match(rest)
    identifier = emoji_match.group(1) if emoji_match else rest
    return section_num, identifier


def get_user_allowed_sections(username: str | None) -> set[str] | None:
    """
    Retorna seções permitidas ao usuário.

    None = todas as seções.
    Prioridade: role em secrets → sections em secrets → acesso total.
    """
    if not username:
        if st.session_state.get("authentication_status"):
            return None
        return {HOME_SECTION}

    users = st.secrets.get("credentials", {}).get("usernames", {})
    user_data = users.get(username, {})

    role = user_data.get("role")
    if role and role in ROLE_SECTIONS:
        allowed = ROLE_SECTIONS[role]
        if allowed is None:
            return None
        return set(allowed) | {HOME_SECTION}

    sections = user_data.get("sections")
    if sections is None:
        return None
    return set(sections) | {HOME_SECTION}


def _filter_sections(
    grouped: dict[str, list[st.Page]],
    allowed: set[str] | None,
) -> dict[str, list[st.Page]]:
    if allowed is None:
        return grouped
    return {name: pages for name, pages in grouped.items() if name in allowed}


def _iter_pages(grouped: dict[str, list[st.Page]]) -> list[st.Page]:
    pages: list[st.Page] = []
    for section_pages in grouped.values():
        pages.extend(section_pages)
    return pages


def reconcile_intended_page(
    current_page: st.Page,
    pages: dict[str, list[st.Page]],
) -> None:
    """Corrige roteamento quando F5 cai na Home apesar da URL apontar para outra página."""
    from streamlit.runtime.scriptrunner_utils.script_run_context import (
        get_script_run_ctx,
    )

    ctx = get_script_run_ctx()
    if not ctx:
        return

    intended = ctx.pages_manager.intended_page_name
    if not intended or current_page.url_path == intended:
        return

    for page in _iter_pages(pages):
        if page.url_path == intended:
            st.switch_page(page)
            return


def build_navigation_pages(
    home_page: st.Page,
    username: str | None = None,
    pages_dir: Path | None = None,
) -> dict[str, list[st.Page]]:
    """Monta o mapa de seções → páginas a partir dos arquivos em pages/."""
    if pages_dir is None:
        pages_dir = Path(__file__).resolve().parent.parent / "pages"

    grouped: dict[str, list[st.Page]] = {HOME_SECTION: [home_page]}

    for path in sorted(pages_dir.glob("*.py"), key=lambda p: p.name):
        parsed = _parse_page_filename(path.name)
        if not parsed:
            continue

        section_num, identifier = parsed
        section = SECTIONS.get(section_num)
        if not section:
            continue

        rel_path = path.relative_to(pages_dir.parent).as_posix()
        grouped.setdefault(section["label"], []).append(
            st.Page(
                rel_path,
                title=_page_title(identifier),
                icon=section["icon"],
                url_path=_url_path(section_num, identifier),
            )
        )

    allowed = get_user_allowed_sections(username)
    return _filter_sections(grouped, allowed)
