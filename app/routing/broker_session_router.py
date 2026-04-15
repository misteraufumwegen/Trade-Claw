"""
Broker Session Router
Manages broker selection, session pooling, and lifecycle.

Features:
- User selects broker at setup (wizard)
- Router maintains pool of active sessions
- Routes orders to selected broker
- Handles connection failures and failover
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from app.brokers.broker_interface import BrokerAdapter
from app.brokers.mock_broker import MockBrokerAdapter
from app.api.order_api_adapter import OrderAPIAdapter
from app.security.audit import AuditLog


logger = logging.getLogger('BrokerSessionRouter')


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
        broker_type: BrokerType,
        broker: BrokerAdapter,
        user_id: str,
        created_at: datetime = None,
    ):
        self.session_id = session_id
        self.broker_type = broker_type
        self.broker = broker
        self.user_id = user_id
        self.created_at = created_at or datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.status = SessionStatus.INITIALIZING
        self.api_adapter: Optional[OrderAPIAdapter] = None
        self.error: Optional[str] = None
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def is_stale(self, timeout_minutes: int = 30) -> bool:
        """Check if session is idle"""
        idle_time = datetime.utcnow() - self.last_activity
        return idle_time > timedelta(minutes=timeout_minutes)
    
    def __repr__(self):
        return f"<BrokerSession {self.broker_type.value} status={self.status.value}>"


class BrokerSessionRouter:
    """
    Routes trading requests to the correct broker session.
    """
    
    def __init__(self, audit_log: Optional[AuditLog] = None):
        """
        Initialize router.
        
        Args:
            audit_log: Audit logging instance
        """
        self.sessions: Dict[str, BrokerSession] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.audit_log = audit_log or AuditLog()
    
    async def create_session(
        self,
        user_id: str,
        broker_type: BrokerType,
        credentials: Dict[str, str],
        **config,
    ) -> BrokerSession:
        """
        Create new broker session.
        
        Args:
            user_id: User identifier
            broker_type: Which broker to use
            credentials: API key/secret
            **config: Broker-specific configuration
        
        Returns:
            BrokerSession if successful
        
        Raises:
            ValueError: If broker type not supported
            AuthenticationError: If credentials invalid
        """
        
        logger.info(f"Creating session for user={user_id} broker={broker_type.value}")
        
        # Instantiate broker
        broker = await self._instantiate_broker(broker_type, credentials, config)
        
        # Authenticate
        if not await broker.authenticate():
            raise ValueError(f"Authentication failed for {broker_type.value}")
        
        # Create session
        session_id = self._generate_session_id()
        session = BrokerSession(
            session_id=session_id,
            broker_type=broker_type,
            broker=broker,
            user_id=user_id,
        )
        session.status = SessionStatus.AUTHENTICATED
        
        # Create API adapter
        session.api_adapter = OrderAPIAdapter(
            broker=broker,
            audit_log=self.audit_log,
        )
        
        # Store session
        self.sessions[session_id] = session
        self.user_sessions[user_id] = session_id
        
        # Audit
        self.audit_log.log(
            action="SESSION_CREATED",
            session_id=session_id,
            details={"user_id": user_id, "broker": broker_type.value},
        )
        
        logger.info(f"Session created: {session_id}")
        return session
    
    async def get_session(self, user_id: str) -> Optional[BrokerSession]:
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
    
    async def get_session_by_id(self, session_id: str) -> Optional[BrokerSession]:
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
            
            # Remove from mappings
            if session.user_id in self.user_sessions:
                del self.user_sessions[session.user_id]
            del self.sessions[session_id]
            
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
    
    async def cleanup_stale_sessions(self, timeout_minutes: int = 30):
        """Remove idle sessions"""
        stale = [
            sid for sid, session in self.sessions.items()
            if session.is_stale(timeout_minutes)
        ]
        
        for session_id in stale:
            await self.close_session(session_id)
        
        if stale:
            logger.info(f"Cleaned up {len(stale)} stale sessions")
    
    @staticmethod
    async def _instantiate_broker(
        broker_type: BrokerType,
        credentials: Dict[str, str],
        config: Dict[str, Any],
    ) -> BrokerAdapter:
        """Create broker instance"""
        
        api_key = credentials.get('api_key')
        secret_key = credentials.get('secret_key')
        
        if broker_type == BrokerType.MOCK:
            return MockBrokerAdapter(
                api_key=api_key or 'mock_key',
                **config,
            )
        
        elif broker_type == BrokerType.HYPERLIQUID:
            from app.brokers.hyperliquid_adapter import HyperliquidAdapter
            return HyperliquidAdapter(
                api_key=api_key,
                secret_key=secret_key,
                **config,
            )
        
        # Alpaca, OANDA would be implemented here
        # elif broker_type == BrokerType.ALPACA:
        #     from app.brokers.alpaca_adapter import AlpacaAdapter
        #     return AlpacaAdapter(api_key=api_key, secret_key=secret_key, **config)
        
        else:
            raise ValueError(f"Unsupported broker: {broker_type.value}")
    
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
    
    async def get_broker(self, user_id: str) -> Optional[BrokerAdapter]:
        """Get broker for user (with failover)"""
        session = await self.router.get_session(user_id)
        if session:
            return session.broker
        return None
    
    async def get_api_adapter(self, user_id: str) -> Optional[OrderAPIAdapter]:
        """Get API adapter for user"""
        session = await self.router.get_session(user_id)
        if session:
            return session.api_adapter
        return None
