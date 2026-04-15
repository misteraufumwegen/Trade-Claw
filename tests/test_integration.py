"""
Integration tests for Trade-Claw components.
"""

import pytest
import asyncio
from datetime import datetime

from app.brokers.mock_broker import MockBrokerScenarios
from app.api.order_api_adapter import OrderAPIAdapter, OrderAPIRequest
from app.routing.broker_session_router import BrokerSessionRouter, BrokerType
from app.wizard.onboarding_broker_config import OnboardingWizard
from app.security.audit import AuditLog
from app.brokers.broker_interface import OrderDirection, OrderType


class TestOrderSubmissionFlow:
    """Test complete order submission flow"""
    
    @pytest.mark.asyncio
    async def test_submit_order_through_api_adapter(self):
        """Test order submission via OrderAPIAdapter"""
        
        broker = MockBrokerScenarios.instant_fill()
        await broker.authenticate()
        
        adapter = OrderAPIAdapter(broker=broker)
        
        request = OrderAPIRequest(
            symbol='EUR_USD',
            direction=OrderDirection.BUY,
            quantity=2.0,
            entry_price=1.0850,
            stop_loss=1.0820,
            take_profit=1.0900,
            order_type=OrderType.MARKET,
        )
        
        order = await adapter.submit_order(request)
        
        assert order.order_id is not None
        assert order.symbol == 'EUR_USD'
        assert order.direction == OrderDirection.BUY
        
        # Wait for fill
        await asyncio.sleep(0.2)
        
        filled = await adapter.get_order(order.order_id)
        assert filled.filled_quantity == 2.0


class TestSessionRouter:
    """Test broker session routing"""
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating a broker session"""
        
        router = BrokerSessionRouter()
        
        session = await router.create_session(
            user_id='test_user',
            broker_type=BrokerType.MOCK,
            credentials={'api_key': 'test'},
        )
        
        assert session.session_id is not None
        assert session.user_id == 'test_user'
        assert session.broker_type == BrokerType.MOCK
        assert session.api_adapter is not None
    
    @pytest.mark.asyncio
    async def test_session_retrieval(self):
        """Test retrieving session by user"""
        
        router = BrokerSessionRouter()
        
        session1 = await router.create_session(
            user_id='user1',
            broker_type=BrokerType.MOCK,
            credentials={'api_key': 'test'},
        )
        
        retrieved = await router.get_session('user1')
        
        assert retrieved is not None
        assert retrieved.session_id == session1.session_id
    
    @pytest.mark.asyncio
    async def test_session_closure(self):
        """Test closing session"""
        
        router = BrokerSessionRouter()
        
        session = await router.create_session(
            user_id='user1',
            broker_type=BrokerType.MOCK,
            credentials={'api_key': 'test'},
        )
        
        success = await router.close_session(session.session_id)
        assert success is True
        
        # Should be gone
        retrieved = await router.get_session('user1')
        assert retrieved is None


class TestOnboardingWizard:
    """Test broker onboarding wizard"""
    
    def test_wizard_initialization(self):
        """Test wizard start"""
        
        router = BrokerSessionRouter()
        wizard = OnboardingWizard(router=router)
        
        state = wizard.start_onboarding(user_id='user1')
        
        assert state.user_id == 'user1'
        assert state.selected_broker is None
    
    def test_broker_selection(self):
        """Test selecting broker"""
        
        router = BrokerSessionRouter()
        wizard = OnboardingWizard(router=router)
        
        wizard.start_onboarding(user_id='user1')
        state = wizard.select_broker(user_id='user1', broker_type='mock')
        
        assert state.selected_broker == BrokerType.MOCK
    
    def test_credentials_entry(self):
        """Test entering credentials"""
        
        router = BrokerSessionRouter()
        wizard = OnboardingWizard(router=router)
        
        wizard.start_onboarding(user_id='user1')
        wizard.select_broker(user_id='user1', broker_type='mock')
        
        result = wizard.enter_credentials(
            user_id='user1',
            credentials={'api_key': 'test_key_123456'},
        )
        
        assert result['valid'] is True
    
    @pytest.mark.asyncio
    async def test_full_onboarding_flow(self):
        """Test complete onboarding flow"""
        
        router = BrokerSessionRouter()
        wizard = OnboardingWizard(router=router)
        
        # Step 1: Start
        wizard.start_onboarding(user_id='user1')
        
        # Step 2: Select broker
        wizard.select_broker(user_id='user1', broker_type='mock')
        
        # Step 3: Enter credentials
        wizard.enter_credentials(
            user_id='user1',
            credentials={'api_key': 'test_key'},
        )
        
        # Step 4: Validate credentials
        validation = await wizard.validate_credentials(user_id='user1')
        assert validation['valid'] is True
        
        # Step 5: Configure risk
        state = wizard.configure_risk(
            user_id='user1',
            config={
                'max_position_size': 0.10,
                'max_drawdown': -0.15,
                'max_daily_loss': -0.05,
                'min_rr_ratio': 1.5,
            },
        )
        
        # Step 6: Confirm
        summary = wizard.get_confirmation_summary(user_id='user1')
        assert summary['broker'] == 'mock'
        assert summary['ready_to_confirm'] is True
        
        # Step 7: Complete
        result = await wizard.confirm_and_complete(user_id='user1')
        assert result['success'] is True
        assert result['broker'] == 'mock'


class TestAuditLog:
    """Test audit logging"""
    
    def test_logging_event(self):
        """Test logging an event"""
        
        audit = AuditLog()
        
        entry = audit.log(
            action="TEST_ACTION",
            user_id="test_user",
            order_id="test_order",
            details={"test": True},
        )
        
        assert entry.action == "TEST_ACTION"
        assert entry.user_id == "test_user"
        assert entry.order_id == "test_order"
    
    def test_event_retrieval(self):
        """Test retrieving events"""
        
        audit = AuditLog()
        
        # Log multiple events
        for i in range(5):
            audit.log(
                action=f"ACTION_{i}",
                user_id="user1",
                severity="INFO",
            )
        
        # Retrieve
        recent = audit.get_recent(limit=10)
        assert len(recent) >= 5
        
        user_events = audit.get_for_user("user1")
        assert len(user_events) >= 5
    
    def test_critical_events(self):
        """Test filtering critical events"""
        
        audit = AuditLog()
        
        audit.log(action="NORMAL", severity="INFO")
        audit.log(action="ALERT", severity="WARNING")
        audit.log(action="CRITICAL", severity="CRITICAL")
        
        critical = audit.get_critical_events()
        assert len(critical) >= 1


class TestRiskValidation:
    """Test risk validation in order flow"""
    
    @pytest.mark.asyncio
    async def test_rr_ratio_validation(self):
        """Test Risk/Reward ratio validation"""
        
        broker = MockBrokerScenarios.instant_fill()
        await broker.authenticate()
        
        adapter = OrderAPIAdapter(broker=broker)
        
        # Valid R/R
        is_valid, ratio = await adapter.validate_rr_ratio(
            entry=1.0850,
            stop_loss=1.0820,
            take_profit=1.0950,
            direction=OrderDirection.BUY,
            min_ratio=1.5,
        )
        
        assert is_valid is True
        assert ratio >= 1.5
        
        # Invalid R/R
        is_valid, ratio = await adapter.validate_rr_ratio(
            entry=1.0850,
            stop_loss=1.0800,
            take_profit=1.0900,
            direction=OrderDirection.BUY,
            min_ratio=2.0,
        )
        
        assert is_valid is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
