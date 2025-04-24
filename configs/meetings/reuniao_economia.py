"""
Meeting configuration for "Reunião de Economia"
"""

# Tab structure configuration defining how charts are organized in this specific meeting
MEETING_TAB_STRUCTURE = {
    "Estados Unidos": {
        "PIB": ["us_gdp"],
        "Inflação": ["us_inflation"],
        "Emprego": ["us_employment"],
        "Indústria": ["Industrial Bloomberg Data Surprise", "Produção Industrial & Utilização de Capacidade"],
        "Varejo": ["Retail & Wholesale Bloomberg Data Surprise", "Vendas no Varejo"],
        "Imobiliário": ["us_real_estate"],
        "Crédito": ["us_credit"],
        "Sentimento": ["us_sentiment"]
    },
    "Brasil": {
        "IBC-Br": ["br_ibcbr"],
        "PIB": ["br_gdp"],
        "Inflação": ["br_inflation"],
        "Indústria": ["br_industry"],
        "Serviços": ["br_services"],
        "Varejo": ["br_retail"],
        "Sentimento": ["br_sentiment"],
        "Emprego": ["br_employment"],
        "Crédito": ["br_credit"],
        "Setor Externo": ["br_external"],
        "Commodities": ["br_commodities"],
        "Fiscal": ["br_fiscal"]
    },
    "Global": {
        "PMI": ["global_pmi"],
        "Commodities": ["global_commodities"],
        "Moedas": ["global_currencies"],
        "Inflação": ["global_inflation"]
    }
}

# Meeting-specific settings
MEETING_SETTINGS = {
    "title": "Reunião de Economia",
    "icon": "🗓️",
    "default_start_date": "2000-01-01",
    "refresh_interval_minutes": 60,  # How often to refresh data (in minutes)
    "chart_groups_to_load": [
        # US chart groups
        "us_gdp", "us_inflation", "us_employment",
        "Industrial Bloomberg Data Surprise", "Produção Industrial & Utilização de Capacidade",
        "Retail & Wholesale Bloomberg Data Surprise", "Vendas no Varejo",
        "us_real_estate", "us_credit", "us_sentiment",
        
        # Brazil chart groups
        "br_ibcbr", "br_gdp", "br_inflation", "br_industry",
        "br_services", "br_retail", "br_sentiment", "br_employment",
        "br_credit", "br_external", "br_commodities", "br_fiscal",
        
        # Global chart groups
        "global_pmi", "global_commodities", "global_currencies", "global_inflation"
    ]
}

def get_tab_structure():
    """
    Returns the tab structure configuration for this meeting.
    
    Returns:
    --------
    Dict[str, Dict[str, List[str]]]
        Dictionary of tab structure
    """
    return MEETING_TAB_STRUCTURE

def get_meeting_settings():
    """
    Returns the meeting-specific settings.
    
    Returns:
    --------
    Dict[str, Any]
        Dictionary of meeting settings
    """
    return MEETING_SETTINGS 