"""Remove bootstrap duplicado das páginas após migração para st.navigation."""

from __future__ import annotations

import re
from pathlib import Path

PAGES_DIR = Path(__file__).resolve().parent.parent / "views"


def _remove_set_page_config(content: str) -> str:
    marker = "st.set_page_config("
    start = content.find(marker)
    if start == -1:
        return content

    depth = 0
    i = start + len(marker) - 1
    while i < len(content):
        char = content[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                end = i + 1
                while end < len(content) and content[end] in "\r\n":
                    end += 1
                return content[:start] + content[end:]
        i += 1
    return content


def _clean_imports(content: str) -> str:
    lines = content.splitlines(keepends=True)
    cleaned: list[str] = []

    for line in lines:
        stripped = line.strip()

        if stripped == "from utils.auth import check_authentication":
            continue

        if stripped.startswith("from utils.ui import "):
            names = stripped.removeprefix("from utils.ui import ").strip()
            kept = [
                part.strip()
                for part in names.split(",")
                if part.strip() not in {"display_logo", "load_css"}
            ]
            if kept:
                cleaned.append(f"from utils.ui import {', '.join(kept)}\n")
            continue

        cleaned.append(line)

    return "".join(cleaned)


def _remove_bootstrap_calls(content: str) -> str:
    for call in ("display_logo()", "load_css()", "check_authentication()"):
        content = re.sub(rf"^[ \t]*{re.escape(call)}\s*\n", "", content, flags=re.MULTILINE)
    return content


def _collapse_blank_lines(content: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", content)


def clean_page(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = original
    updated = _remove_set_page_config(updated)
    updated = _remove_bootstrap_calls(updated)
    updated = _clean_imports(updated)
    updated = _collapse_blank_lines(updated)

    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    for path in sorted(PAGES_DIR.glob("*.py")):
        if clean_page(path):
            changed += 1
            print(f"updated: {path.name}")
    print(f"Done. {changed} file(s) updated.")


if __name__ == "__main__":
    main()
