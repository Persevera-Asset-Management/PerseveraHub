"""Wrapper sobre :class:`FinancialDataService` que tolera providers indisponíveis.

A classe :class:`FinancialDataService` original do ``persevera_tools`` instancia
todos os providers de forma ansiosa no construtor. Se algum deles falhar (por
exemplo, a BCB Expectativas indisponível), a inicialização inteira do serviço
levanta exceção e a página fica inacessível.

Esta camada substitui o ``__init__`` por uma versão resiliente, que tenta cada
provider isoladamente, registra os erros em ``provider_errors`` e expõe um
mapeamento ``SOURCE_TO_PROVIDER`` (idêntico ao usado em ``get_data``) para que
a UI saiba qual atributo de provider cada fonte (``source``) consome — útil
para desabilitar botões quando o provider correspondente está fora do ar.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

from persevera_tools.data import FinancialDataService
from persevera_tools.data.providers.anbima import AnbimaProvider
from persevera_tools.data.providers.anbima_feed import (
    AnbimaFeedProvider,
    AnbimaFundosProvider,
)
from persevera_tools.data.providers.b3 import B3Provider
from persevera_tools.data.providers.bcb_focus import BcbFocusProvider
from persevera_tools.data.providers.bloomberg import BloombergProvider
from persevera_tools.data.providers.cvm import CVMProvider
from persevera_tools.data.providers.debentures_com import DebenturesComProvider
from persevera_tools.data.providers.fred import FredProvider
from persevera_tools.data.providers.invesco import InvescoProvider
from persevera_tools.data.providers.investing_com import InvestingComProvider
from persevera_tools.data.providers.kraneshares import KraneSharesProvider
from persevera_tools.data.providers.mais_retorno import MaisRetornoProvider
from persevera_tools.data.providers.mdic import MDICProvider
from persevera_tools.data.providers.sgs import SGSProvider
from persevera_tools.data.providers.sidra import SidraProvider
from persevera_tools.data.providers.simplify import SimplifyProvider


# Espelha o dicionário interno de :meth:`FinancialDataService.get_data` para que
# a camada de UI possa descobrir qual provider sustenta cada ``source``.
SOURCE_TO_PROVIDER: Dict[str, str] = {
    'sgs': 'sgs',
    'fred': 'fred',
    'sidra': 'sidra',
    'debentures_com': 'debentures_com',
    'anbima_indices': 'anbima',
    'anbima_debentures': 'anbima',
    'anbima_titulos_publicos': 'anbima',
    'anbima_cri_cra': 'anbima',
    'anbima_feed_titulos_publicos_mercado_secundario': 'anbima_feed',
    'anbima_feed_titulos_publicos_vna': 'anbima_feed',
    'anbima_feed_titulos_publicos_curvas_juros': 'anbima_feed',
    'anbima_feed_debentures_mercado_secundario': 'anbima_feed',
    'anbima_feed_debentures_curvas_credito': 'anbima_feed',
    'anbima_feed_cri_cra_mercado_secundario': 'anbima_feed',
    'anbima_feed_fidc_mercado_secundario': 'anbima_feed',
    'anbima_feed_indices_resultados_ihfa_fechado': 'anbima_feed',
    'anbima_feed_indices_resultados_ima': 'anbima_feed',
    'anbima_feed_indices_resultados_idka': 'anbima_feed',
    'anbima_fundos_lista': 'anbima_fundos',
    'anbima_fundos_instituicoes': 'anbima_fundos',
    'anbima_fundos_lote_dados_cadastrais': 'anbima_fundos',
    'anbima_fundos_lote_serie_historica': 'anbima_fundos',
    'bcb_focus': 'bcb_focus',
    'simplify': 'simplify',
    'invesco': 'invesco',
    'kraneshares': 'kraneshares',
    'mdic': 'mdic',
    'b3_investor_flow': 'b3',
    'b3_bdi': 'b3',
    'mais_retorno_debentures': 'mais_retorno',
    'mais_retorno_fundos': 'mais_retorno',
    'investfy_investor_flow': 'investfy',
}


class SafeFinancialDataService(FinancialDataService):
    """Variante de :class:`FinancialDataService` resiliente a providers offline.

    Cada provider é instanciado dentro de seu próprio ``try/except``. Os que
    falham têm o atributo correspondente definido como ``None`` e a mensagem
    de erro é registrada em :attr:`provider_errors`.
    """

    def __init__(
        self,
        start_date: str = '1980-01-01',
        fred_api_key: Optional[str] = None,
        bloomberg_tickers_mapping: Optional[Dict[str, Dict[str, str]]] = None,
        bloomberg_fields_mapping: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> None:
        self.start_date = start_date
        self.logger = logging.getLogger(self.__class__.__name__)
        self.provider_errors: Dict[str, str] = {}

        provider_factories: Dict[str, Callable[[], object]] = {
            'bloomberg': lambda: BloombergProvider(
                start_date=start_date,
                tickers_mapping=bloomberg_tickers_mapping,
                fields_mapping=bloomberg_fields_mapping,
            ),
            'sgs': lambda: SGSProvider(start_date=start_date),
            'fred': lambda: FredProvider(start_date=start_date),
            'sidra': lambda: SidraProvider(start_date=start_date),
            'anbima': lambda: AnbimaProvider(start_date=start_date),
            'anbima_feed': lambda: AnbimaFeedProvider(start_date=start_date),
            'anbima_fundos': lambda: AnbimaFundosProvider(start_date=start_date),
            'cvm': lambda: CVMProvider(start_date=start_date),
            'bcb_focus': lambda: BcbFocusProvider(start_date=start_date),
            'simplify': lambda: SimplifyProvider(start_date=start_date),
            'invesco': lambda: InvescoProvider(start_date=start_date),
            'kraneshares': lambda: KraneSharesProvider(start_date=start_date),
            'investing_com': lambda: InvestingComProvider(),
            'debentures_com': lambda: DebenturesComProvider(),
            'mdic': lambda: MDICProvider(),
            'b3': lambda: B3Provider(),
            'mais_retorno': lambda: MaisRetornoProvider(),
            'investfy': lambda: InvestfyProvider(),
        }

        for attr, factory in provider_factories.items():
            try:
                setattr(self, attr, factory())
            except Exception as exc:
                setattr(self, attr, None)
                self.provider_errors[attr] = str(exc)
                self.logger.warning("Falha ao inicializar provider '%s': %s", attr, exc)

    def is_provider_available(self, provider_attr: str) -> bool:
        """Indica se o provider foi instanciado com sucesso."""
        return getattr(self, provider_attr, None) is not None

    def is_source_available(self, source: str) -> bool:
        """Indica se o ``source`` está disponível (provider correspondente OK)."""
        provider_attr = SOURCE_TO_PROVIDER.get(source)
        if provider_attr is None:
            return True
        return self.is_provider_available(provider_attr)

    def get_provider_error(self, provider_attr: str) -> Optional[str]:
        """Retorna a mensagem de erro do provider, se houver."""
        return self.provider_errors.get(provider_attr)

    def get_source_error(self, source: str) -> Optional[str]:
        """Retorna a mensagem de erro do provider que sustenta o ``source``."""
        provider_attr = SOURCE_TO_PROVIDER.get(source)
        if provider_attr is None:
            return None
        return self.get_provider_error(provider_attr)
