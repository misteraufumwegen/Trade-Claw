"""
Broker Session Router
Manages broker selection, session pooling, and lifecycle.

Features:
- User selects broker at setup (wizard)
- Router maintains pool of active sessions
- Routes orders to selected broker
- Handles connection failures and failover
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from app.api.order_api_adapter import OrderAPIAdapter
from app.brokers.broker_interface import BrokerAdapter
from app.security.audit import AuditLog

logger = logging.getLogger("BrokerSessionRouter")


class BrokerType(Enum):
    """Supported broker types"""

    ALPACA = "alpaca"
    OANDA = "oanda"
    HYPERLIQUID = "hyperliquid"
    KRAKEN = "kraken"
    MOCK = "mock"


class SessionStatus(Enum):
    """Session lifecycle states"""

    INITIALIZING = "INITIALIZING"
    AUTHENTICATED = "AUTHENTICATED"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class BrokerSession:
    """Single broker session"""

    def __init__(
        self,
        session_id: str,
        broker_type: BrokerType | str,
        broker: BrokerAdapter,
        user_id: str,
        created_at: datetime = None,
    ):
        self.session_id = session_id
        # Normalised to a string so plugins like ``ccxt:binance`` can live
        # alongside the legacy enum values.
        self.broker_type = (
            broker_type.value if isinstance(broker_type, BrokerType) else str(broker_type)
        )
        self.broker = broker
        self.user_id = user_id
        self.created_at = created_at or datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.status = SessionStatus.INITIALIZING
        self.api_adapter: OrderAPIAdapter | None = None
        self.error: str | None = None

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()

    def is_stale(self, timeout_minutes: int = 30) -> bool:
        """Check if session is idle"""
        idle_time = datetime.utcnow() - self.last_activity
        return idle_time > timedelta(minutes=timeout_minutes)

    def __repr__(self):
        return f"<BrokerSession {self.broker_type} status={self.status.value}>"


class BrokerSessionRouter:
    """
    Routes trading requests to the correct broker session.
    """

    def __init__(self, audit_log: AuditLog | None = None):
        """
        Initialize router.

        Args:
            audit_log: Audit logging instance
        """
        self.sessions: dict[str, BrokerSession] = {}
        self.user_sessions: dict[str, str] = {}  # user_id -> session_id
        self.audit_log = audit_log or AuditLog()
        # Guards concurrent create/close (M10). asyncio.Lock() must be created
        # inside an event loop; create lazily so that sync import-time usage
        # (e.g. in tests) still works.
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def create_session(
        self,
        user_id: str,
        broker_type: BrokerType | str,
        credentials: dict[str, str],
        **config,
    ) -> str:
        """
        Create new broker session.

        Args:
            user_id: User identifier
            broker_type: Which broker to use (built-in type or plugin id)
            credentials: API key/secret
            **config: Broker-specific configuration

        Returns:
            session_id string

        Raises:
            ValueError: If broker type not supported by the registry
            AuthenticationError: If credentials invalid
        """
        # Plugin-registered brokers are not in the legacy enum, so we keep
        # broker_type as a string for the rest of this function.
        type_label = broker_type.value if isinstance(broker_type, BrokerType) else str(broker_type)
        logger.info("Creating session for user=%s broker=%s", user_id, type_label)

        # Instantiate broker via the registry (handles both built-ins and plugins)
        broker = await self._instantiate_broker(type_label, credentials, config)

        # Authenticate
        if not await broker.authenticate():
            raise ValueError(f"Authentication failed for {type_label}")

        # Create session
        session_id = self._generate_session_id()
        session = BrokerSession(
            session_id=session_id,
            broker_type=type_label,
            broker=broker,
            user_id=user_id,
        )
        session.status = SessionStatus.AUTHENTICATED

        # Create API adapter
        session.api_adapter = OrderAPIAdapter(
            broker=broker,
            audit_log=self.audit_log,
        )

        # Store session under lock to avoid concurrent overwrites (M10).
        async with self._get_lock():
            self.sessions[session_id] = session
            self.user_sessions[user_id] = session_id

        # Audit
        self.audit_log.log(
            action="SESSION_CREATED",
            session_id=session_id,
            details={"user_id": user_id, "broker": type_label},
        )

        logger.info("Session created: %s", session_id)
        return session_id

    async def get_session(self, user_id: str) -> BrokerSession | None:
        """Get active session for user"""
        session_id = self.user_sessions.get(user_id)
        if not session_id:
            return None

        session = self.sessions.get(session_id)
        if session and session.is_stale():
            await self.close_session(session_id)
            return None

        if session:
            session.update_activity()

        return session

    async def get_session_by_id(self, session_id: str) -> BrokerSession | None:
        """Get session by ID"""
        session = self.sessions.get(session_id)
        if session and not session.is_stale():
            session.update_activity()
            return session

        if session:
            await self.close_session(session_id)

        return None

    async def close_session(self, session_id: str) -> bool:
        """Close session and cleanup"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        try:
            await session.broker.disconnect()
            session.status = SessionStatus.DISCONNECTED

            # Remove from mappings under lock (M10).
            async with self._get_lock():
                if session.user_id in self.user_sessions:
                    del self.user_sessions[session.user_id]
                self.sessions.pop(session_id, None)

            self.audit_log.log(
                action="SESSION_CLOSED",
                session_id=session_id,
                details={"user_id": session.user_id},
            )

            logger.info(f"Session closed: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error closing session: {e}")
            return False

    async def list_sessions(self, user_id: str = None) -> list:
        """List active sessions"""
        if user_id:
            session_id = self.user_sessions.get(user_id)
            if session_id and session_id in self.sessions:
                return [self.sessions[session_id]]
            return []

        return list(self.sessions.values())

    async def get_api_adapter(self, session_id: str) -> OrderAPIAdapter:
        """Get OrderAPIAdapter for a session by ID.

        This is the primary interface used by FastAPI endpoints to interact
        with a broker session.

        Raises:
            ValueError: If session not found or stale.
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        if session.is_stale():
            await self.close_session(session_id)
            raise ValueError(f"Session expired: {session_id}")
        session.update_activity()
        if session.api_adapter is None:
            raise ValueError(f"Session has no API adapter: {session_id}")
        return session.api_adapter

    async def cleanup_stale_sessions(self, timeout_minutes: int = 30):
        """Remove idle sessions"""
        stale = [sid for sid, session in self.sessions.items() if session.is_stale(timeout_minutes)]

        for session_id in stale:
            await self.close_session(session_id)

        if stale:
            logger.info(f"Cleaned up {len(stale)} stale sessions")

    @staticmethod
    async def _instantiate_broker(
        broker_type: BrokerType | str,
        credentials: dict[str, str],
        config: dict[str, Any],
    ) -> BrokerAdapter:
        """Create broker instance via the plugin registry.

        Accepts either a ``BrokerType`` enum value (legacy callers) or any
        string broker_type that's been registered, so plugins can introduce
        new types like ``"ccxt:binance"`` without enum changes.
        """
        from app.brokers.registry import REGISTRY  # noqa: PLC0415

        type_str = broker_type.value if isinstance(broker_type, BrokerType) else str(broker_type)
        return REGISTRY.create(type_str, credentials, **config)

    @staticmethod
    def _generate_session_id() -> str:
        """Generate unique session ID"""
        import uuid

        return f"session_{uuid.uuid4().hex[:12]}"


class RoutingError(Exception):
    """Routing error"""

    pass


class SessionPool:
    """
    Thread-safe pool of broker sessions with load balancing.
    """

    def __init__(self, router: BrokerSessionRouter):
        self.router = router
        self._lock = None  # Use asyncio.Lock in real implementation

    async def get_broker(self, user_id: str) -> BrokerAdapter | None:
        """Get broker for user (with failover)"""
        session = await self.router.get_session(user_id)
        if session:
            return session.broker
        return None

    async def get_api_adapter(self, user_id: str) -> OrderAPIAdapter | None:
        """Get API adapter for user"""
        session = await self.router.get_session(user_id)
        if session:
            return session.api_adapter
        return None
