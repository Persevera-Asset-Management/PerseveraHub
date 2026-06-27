"""Metadados de navegação, slugs de URL e permissões por perfil.

Permissões (em .streamlit/secrets.toml):

    [credentials.usernames.joao]
    email = "..."
    name = "João"
    password = "..."
    role = "carteiras"          # usa ROLE_SECTIONS abaixo

    # ou lista explícita de seções:
    sections = ["Início", "Análise", "Carteiras"]

Sem role/sections → acesso a todas as seções.
"""

from __future__ import annotations

SECTIONS: dict[str, dict[str, str]] = {
    "1": {"label": "Acompanhamentos Periódicos", "slug": "acompanhamentos-periodicos", "icon": ":material/event_repeat:"},
    "2": {"label": "Crédito Privado", "slug": "credito-privado", "icon": ":material/credit_score:"},
    "3": {"label": "Equities", "slug": "equities", "icon": ":material/candlestick_chart:"},
    "4": {"label": "Análise Quantitativa", "slug": "analise-quantitativa", "icon": ":material/analytics:"},
    "5": {"label": "Fundos", "slug": "fundos", "icon": ":material/pie_chart:"},
    "6": {"label": "Carteiras Administradas", "slug": "carteiras-administradas", "icon": ":material/account_balance_wallet:"},
    "7": {"label": "Administrativo", "slug": "administrativo", "icon": ":material/receipt_long:"},
    "8": {"label": "Utilitários", "slug": "utilitarios", "icon": ":material/handyman:"},
}

HOME_SECTION = "Início"

# Perfis opcionais — sobrescrevem a lista de seções do usuário quando definidos em secrets.
# None = acesso a todas as seções.
ROLE_SECTIONS: dict[str, list[str] | None] = {
    "admin": None,
    "full": None,
    "acompanhamentos-periodicos": [HOME_SECTION, "Acompanhamentos Periódicos"],
    "credito-privado": [HOME_SECTION, "Crédito Privado"],
    "equities": [HOME_SECTION, "Equities"],
    "fundos": [HOME_SECTION, "Fundos"],
    "analise-quantitativa": [HOME_SECTION, "Análise Quantitativa"],
    "carteiras-administradas": [HOME_SECTION, "Carteiras Administradas"],
    "utilitarios": [HOME_SECTION, "Utilitários"],
    "administrativo": [HOME_SECTION, "Administrativo"],
}
