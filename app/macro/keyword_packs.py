"""
Keyword packs for GDELT DOC queries.

Each pack defines a thematic search (GDELT query syntax) plus a mapping from
"matches in this pack" → MacroEvent metadata (which assets are affected,
default direction, risk regime).

User asked for these three packs in the implementation brief; we keep them as
the default. Add more by appending to ``DEFAULT_PACKS``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .event_fetcher import EventCategory, EventDirection


@dataclass(frozen=True)
class KeywordPack:
    """One thematic GDELT search package."""

    name: str
    description: str
    gdelt_query: str
    category: EventCategory
    default_direction: EventDirection
    assets_affected: tuple[str, ...] = ()
    risk_on_support: bool = False
    risk_off_support: bool = False
    volatility_expected: bool = True


DEFAULT_PACKS: tuple[KeywordPack, ...] = (
    KeywordPack(
        name="energy_shipping",
        description="Energy / shipping disruption (sanctions, export bans, port closures)",
        gdelt_query='(sanctions OR "export ban" OR "port closure")',
        category=EventCategory.GEOPOLITICAL,
        default_direction=EventDirection.BEARISH,
        assets_affected=("CL", "BZ", "NG", "USO", "USD"),
        risk_off_support=True,
    ),
    KeywordPack(
        name="geopolitical_stress",
        description="Geopolitical escalation (missile strikes, airstrikes, mobilization)",
        gdelt_query='("missile strike" OR "airstrike" OR "mobilization")',
        category=EventCategory.GEOPOLITICAL,
        default_direction=EventDirection.BEARISH,
        assets_affected=("GLD", "JPY", "USD", "CHF", "BTC"),
        risk_off_support=True,
    ),
    KeywordPack(
        name="event_risk",
        description="Industrial / infrastructure shock (refinery fires, pipeline blasts, outages)",
        gdelt_query='("refinery fire" OR "pipeline explosion" OR "power outage")',
        category=EventCategory.GEOPOLITICAL,
        default_direction=EventDirection.BEARISH,
        assets_affected=("CL", "NG", "XLE", "USO"),
        risk_off_support=True,
    ),
)


def get_pack(name: str) -> KeywordPack | None:
    for p in DEFAULT_PACKS:
        if p.name == name:
            return p
    return None
