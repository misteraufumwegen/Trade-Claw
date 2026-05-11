"""
Macro Events Module — live event signals + historical seed.

Live providers (free, no auth):
- GDELT DOC v2 — multi-source-confirmed news (see :mod:`app.macro.gdelt_client`)
- GDACS — structured natural disasters with alert levels
  (see :mod:`app.macro.gdacs_client`)

Internal normalizer maps both into the shared :class:`MacroEvent` shape.
Filtering / scoring / sentiment lives in :mod:`app.macro.event_filters`.
"""

from .event_fetcher import (
    EventCategory,
    EventDirection,
    EventImpact,
    MacroEvent,
    MacroEventFetcher,
)
from .event_filters import EventFilter, EventScorer, MacroSignal
from .gdacs_client import GdacsClient, GdacsRecord
from .gdelt_client import GdeltArticle, GdeltClient, confirm_articles
from .keyword_packs import DEFAULT_PACKS, KeywordPack, get_pack
from .normalizer import gdacs_to_macro_event, gdelt_pack_to_macro_event

__all__ = [
    "MacroEvent",
    "MacroEventFetcher",
    "EventCategory",
    "EventImpact",
    "EventDirection",
    "EventScorer",
    "EventFilter",
    "MacroSignal",
    "GdeltClient",
    "GdeltArticle",
    "confirm_articles",
    "GdacsClient",
    "GdacsRecord",
    "KeywordPack",
    "DEFAULT_PACKS",
    "get_pack",
    "gdelt_pack_to_macro_event",
    "gdacs_to_macro_event",
]
