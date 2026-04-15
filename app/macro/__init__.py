"""
Macro Events Module - Real-time Macro Event Integration

Includes:
- Real-time event fetching (worldmonitor.app API)
- Event categorization (Politics, Monetary Policy, Geopolitics, Economic, On-Chain)
- Event scoring and filtering
- Historical event database (5+ years for backtests)
"""

from .event_fetcher import MacroEventFetcher, MacroEvent, EventCategory
from .event_filters import EventScorer, EventFilter

__all__ = [
    'MacroEventFetcher',
    'MacroEvent',
    'EventCategory',
    'EventScorer',
    'EventFilter',
]
