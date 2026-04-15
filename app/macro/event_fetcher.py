"""
Macro Event Fetcher - Real-time Integration with worldmonitor.app

Fetches:
- Real-time events (Politics, Monetary Policy, Geopolitics, Economic, On-Chain)
- Event metadata (timestamp, source, impact, assets affected)
- Historical events (5+ years for backtesting)

API Integration:
- worldmonitor.app REST endpoints
- Fallback to cached/historical data if live feed unavailable
"""

import logging
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class EventCategory(Enum):
    """Macro event categories."""
    MONETARY_POLICY = "Monetary Policy"      # Fed, ECB, BOJ decisions
    FISCAL_POLICY = "Fiscal Policy"          # Government stimulus, budgets
    GEOPOLITICAL = "Geopolitical"            # Sanctions, conflicts, trade wars
    ECONOMIC_DATA = "Economic Data"          # CPI, Jobs, GDP, PMI
    ON_CHAIN = "On-Chain"                    # Bitcoin halving, ETH staking


class EventImpact(Enum):
    """Event market impact level."""
    CRITICAL = "Critical"    # Major market moving (>3% impact)
    HIGH = "High"            # Significant impact (1-3%)
    MEDIUM = "Medium"        # Moderate impact (0.5-1%)
    LOW = "Low"              # Minor impact (<0.5%)


class EventDirection(Enum):
    """Event direction bias."""
    BULLISH = "Bullish"      # Supports upward movement
    BEARISH = "Bearish"      # Supports downward movement
    NEUTRAL = "Neutral"      # Mixed or neutral impact


@dataclass
class MacroEvent:
    """Single macro event record."""
    event_id: str
    category: EventCategory
    title: str
    description: str
    timestamp: datetime
    impact: EventImpact
    direction: EventDirection  # Bullish/Bearish for crypto/risk assets
    
    # Metadata
    source: str = "worldmonitor.app"  # Event source
    assets_affected: List[str] = field(default_factory=list)  # [BTC, ETH, EUR, GLD]
    countries: List[str] = field(default_factory=list)  # [US, EU, CN]
    
    # Forecast vs Actual
    forecast_value: Optional[float] = None
    actual_value: Optional[float] = None
    previous_value: Optional[float] = None
    
    # Trading signals
    risk_on_support: bool = False      # Supports risk-on trades
    risk_off_support: bool = False     # Supports risk-off trades
    volatility_expected: bool = False   # Event likely to cause volatility spike
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'event_id': self.event_id,
            'category': self.category.value,
            'title': self.title,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'impact': self.impact.value,
            'direction': self.direction.value,
            'source': self.source,
            'assets_affected': self.assets_affected,
            'countries': self.countries,
            'forecast_value': self.forecast_value,
            'actual_value': self.actual_value,
            'previous_value': self.previous_value,
            'risk_on_support': self.risk_on_support,
            'risk_off_support': self.risk_off_support,
            'volatility_expected': self.volatility_expected,
            'created_at': self.created_at.isoformat(),
        }


class MacroEventFetcher:
    """
    Fetches and manages macro events from worldmonitor.app.
    
    Supports:
    - Real-time event fetching via REST API
    - Caching of events (local JSON fallback)
    - Historical event database (5+ years)
    - Event categorization and filtering
    """
    
    def __init__(self, api_endpoint: Optional[str] = None, use_cache: bool = True):
        """
        Initialize event fetcher.
        
        Args:
            api_endpoint: worldmonitor.app API URL (auto-default if None)
            use_cache: Use local cache if API unavailable
        """
        self.api_endpoint = api_endpoint or "https://api.worldmonitor.app/v1"
        self.use_cache = use_cache
        self.events: List[MacroEvent] = []
        self.cache_path = Path(__file__).parent / "historical_events.json"
        
        logger.info(f"📡 MacroEventFetcher initialized")
        logger.info(f"   API: {self.api_endpoint}")
        logger.info(f"   Cache: {self.cache_path}")
        
        # Load historical events
        self._load_historical_events()
    
    def _load_historical_events(self):
        """Load historical events from cache file."""
        if not self.cache_path.exists():
            logger.warning(f"⚠️  No historical events cache found at {self.cache_path}")
            self._create_mock_historical_events()
            return
        
        try:
            with open(self.cache_path, 'r') as f:
                data = json.load(f)
                for event_data in data.get('events', []):
                    event = self._parse_event_dict(event_data)
                    if event:
                        self.events.append(event)
            
            logger.info(f"✅ Loaded {len(self.events)} historical events")
        except Exception as e:
            logger.error(f"❌ Error loading historical events: {e}")
    
    def _create_mock_historical_events(self):
        """Create mock historical events for demo/backtest."""
        mock_events = [
            # Bitcoin Halving Events
            {
                'event_id': 'BTC_HALVING_2016',
                'category': EventCategory.ON_CHAIN.value,
                'title': 'Bitcoin Halving',
                'description': 'Bitcoin block reward halved from 25 to 12.5 BTC',
                'timestamp': datetime(2016, 7, 9),
                'impact': EventImpact.CRITICAL.value,
                'direction': EventDirection.BULLISH.value,
                'assets_affected': ['BTC'],
                'risk_on_support': True,
                'volatility_expected': True,
            },
            {
                'event_id': 'BTC_HALVING_2020',
                'category': EventCategory.ON_CHAIN.value,
                'title': 'Bitcoin Halving',
                'description': 'Bitcoin block reward halved from 12.5 to 6.25 BTC',
                'timestamp': datetime(2020, 5, 11),
                'impact': EventImpact.CRITICAL.value,
                'direction': EventDirection.BULLISH.value,
                'assets_affected': ['BTC'],
                'risk_on_support': True,
                'volatility_expected': True,
            },
            {
                'event_id': 'BTC_HALVING_2024',
                'category': EventCategory.ON_CHAIN.value,
                'title': 'Bitcoin Halving',
                'description': 'Bitcoin block reward halved from 6.25 to 3.125 BTC',
                'timestamp': datetime(2024, 4, 19),
                'impact': EventImpact.CRITICAL.value,
                'direction': EventDirection.BULLISH.value,
                'assets_affected': ['BTC'],
                'risk_on_support': True,
                'volatility_expected': True,
            },
            # Fed Events
            {
                'event_id': 'FED_DECISION_2023_03',
                'category': EventCategory.MONETARY_POLICY.value,
                'title': 'Fed Holds Rates, Signals Pivot',
                'description': 'Federal Reserve holds interest rates, signals potential rate cuts ahead',
                'timestamp': datetime(2023, 3, 22),
                'impact': EventImpact.CRITICAL.value,
                'direction': EventDirection.BULLISH.value,
                'countries': ['US'],
                'assets_affected': ['BTC', 'ETH', 'GLD', 'EUR/USD'],
                'risk_on_support': True,
                'volatility_expected': True,
            },
            # Geopolitical
            {
                'event_id': 'UKRAINE_WAR_START',
                'category': EventCategory.GEOPOLITICAL.value,
                'title': 'Russia Invades Ukraine',
                'description': 'Russia launches military invasion of Ukraine',
                'timestamp': datetime(2022, 2, 24),
                'impact': EventImpact.CRITICAL.value,
                'direction': EventDirection.BEARISH.value,
                'countries': ['RU', 'UA', 'EU'],
                'assets_affected': ['BTC', 'GLD', 'JPY'],
                'risk_off_support': True,
                'volatility_expected': True,
            },
            # Economic Data
            {
                'event_id': 'CPI_2023_08',
                'category': EventCategory.ECONOMIC_DATA.value,
                'title': 'US CPI (August 2023)',
                'description': 'US Consumer Price Index released',
                'timestamp': datetime(2023, 9, 13),
                'impact': EventImpact.HIGH.value,
                'direction': EventDirection.BULLISH.value,
                'countries': ['US'],
                'assets_affected': ['BTC', 'USD'],
                'forecast_value': 3.8,
                'actual_value': 3.8,
                'previous_value': 4.3,
                'volatility_expected': True,
            },
            # On-Chain: Ethereum Staking
            {
                'event_id': 'ETH_SHANGHAI',
                'category': EventCategory.ON_CHAIN.value,
                'title': 'Ethereum Shanghai Upgrade',
                'description': 'Ethereum enables staking withdrawals',
                'timestamp': datetime(2023, 4, 12),
                'impact': EventImpact.HIGH.value,
                'direction': EventDirection.BULLISH.value,
                'assets_affected': ['ETH'],
                'risk_on_support': True,
                'volatility_expected': True,
            },
        ]
        
        for event_data in mock_events:
            event = self._parse_event_dict(event_data)
            if event:
                self.events.append(event)
        
        logger.info(f"✅ Created {len(self.events)} mock historical events")
    
    def _parse_event_dict(self, data: Dict) -> Optional[MacroEvent]:
        """Parse event dictionary into MacroEvent object."""
        try:
            return MacroEvent(
                event_id=data.get('event_id', 'UNKNOWN'),
                category=EventCategory(data.get('category', 'Economic Data')),
                title=data.get('title', ''),
                description=data.get('description', ''),
                timestamp=self._parse_datetime(data.get('timestamp')),
                impact=EventImpact(data.get('impact', 'Medium')),
                direction=EventDirection(data.get('direction', 'Neutral')),
                source=data.get('source', 'worldmonitor.app'),
                assets_affected=data.get('assets_affected', []),
                countries=data.get('countries', []),
                forecast_value=data.get('forecast_value'),
                actual_value=data.get('actual_value'),
                previous_value=data.get('previous_value'),
                risk_on_support=data.get('risk_on_support', False),
                risk_off_support=data.get('risk_off_support', False),
                volatility_expected=data.get('volatility_expected', False),
            )
        except Exception as e:
            logger.error(f"❌ Error parsing event: {e}")
            return None
    
    def _parse_datetime(self, dt_str) -> datetime:
        """Parse datetime from string."""
        if isinstance(dt_str, datetime):
            return dt_str
        try:
            return datetime.fromisoformat(dt_str)
        except:
            return datetime.utcnow()
    
    def fetch_live_events(self, limit: int = 50) -> List[MacroEvent]:
        """
        Fetch live events from worldmonitor.app API.
        
        Args:
            limit: Maximum number of events to fetch
        
        Returns:
            List of MacroEvent objects
        """
        try:
            url = f"{self.api_endpoint}/events"
            params = {'limit': limit, 'sort': 'timestamp:desc'}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            events = []
            
            for event_data in data.get('events', []):
                event = self._parse_event_dict(event_data)
                if event:
                    events.append(event)
                    self.events.append(event)
            
            logger.info(f"✅ Fetched {len(events)} live events from worldmonitor.app")
            return events
        
        except Exception as e:
            logger.warning(f"⚠️  Failed to fetch live events: {e}")
            if self.use_cache:
                logger.info("📚 Falling back to cached events")
                return self.events[-50:] if self.events else []
            return []
    
    def get_events_by_category(self, category: EventCategory) -> List[MacroEvent]:
        """Get events by category."""
        return [e for e in self.events if e.category == category]
    
    def get_events_by_date_range(self, start: datetime, end: datetime) -> List[MacroEvent]:
        """Get events within date range."""
        return [e for e in self.events if start <= e.timestamp <= end]
    
    def get_events_for_backtest(self, start_date: datetime, end_date: datetime) -> List[MacroEvent]:
        """
        Get historical events for backtesting (5+ years of data).
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
        
        Returns:
            List of events within range
        """
        return self.get_events_by_date_range(start_date, end_date)
    
    def get_live_feed(self) -> List[MacroEvent]:
        """Get live event feed (recent events only)."""
        # Get events from last 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        return self.get_events_by_date_range(cutoff, datetime.utcnow())
    
    def save_events_to_cache(self):
        """Save current events to cache file."""
        try:
            data = {
                'events': [e.to_dict() for e in self.events],
                'cached_at': datetime.utcnow().isoformat(),
            }
            
            with open(self.cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"✅ Saved {len(self.events)} events to cache")
        except Exception as e:
            logger.error(f"❌ Error saving cache: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    fetcher = MacroEventFetcher()
    
    # Get live events
    print("\n" + "="*70)
    print("LIVE EVENTS (Last 7 Days)")
    print("="*70)
    live_events = fetcher.get_live_feed()
    for event in live_events[:5]:
        print(f"\n📌 {event.title}")
        print(f"   Category: {event.category.value}")
        print(f"   Impact: {event.impact.value}")
        print(f"   Direction: {event.direction.value}")
        print(f"   Affects: {', '.join(event.assets_affected)}")
    
    # Get events by category
    print("\n" + "="*70)
    print("EVENTS BY CATEGORY")
    print("="*70)
    for category in EventCategory:
        events = fetcher.get_events_by_category(category)
        print(f"{category.value}: {len(events)} events")
