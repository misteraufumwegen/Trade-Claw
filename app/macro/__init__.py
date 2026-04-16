"""
Macro Events Module - Real-time Macro Event Integration

Includes:
- Real-time event fetching (worldmonitor.app API)
- Event categorization (Politics, Monetary Policy, Geopolitics, Economic, On-Chain)
- Event scoring and filtering
- Historical event database (5+ years for backtests)
"""

from .event_fetcher import EventCategory, MacroEvent, MacroEventFetcher
from .event_filters import EventFilter, EventScorer

__all__ = [
    "MacroEventFetcher",
    "MacroEvent",
    "EventCategory",
    "EventScorer",
    "EventFilter",
]
