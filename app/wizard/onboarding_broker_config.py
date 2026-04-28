"""
Onboarding Broker Configuration Wizard
Guides user through broker setup: selection → credentials → validation → confirmation

Frontend: Separate wizard steps
Backend: This validates and stores configuration securely
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from app.routing.broker_session_router import BrokerSessionRouter, BrokerType
from app.security.audit import AuditLog

logger = logging.getLogger("OnboardingWizard")


class WizardStep(Enum):
    """Onboarding wizard steps"""

    WELCOME = "welcome"
    BROKER_SELECTION = "broker_selection"
    CREDENTIALS = "credentials"
    VALIDATION = "validation"
    RISK_SETUP = "risk_setup"
    CONFIRMATION = "confirmation"
    COMPLETE = "complete"


@dataclass
class OnboardingState:
    """Maintains wizard state across steps"""

    step: WizardStep
    user_id: str
    selected_broker: BrokerType | None = None
    credentials: dict[str, str] = None
    risk_config: dict[str, Any] = None
    session_id: str | None = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.credentials is None:
            self.credentials = {}
        if self.risk_config is None:
            self.risk_config = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class OnboardingWizard:
    """
    Broker onboarding wizard.

    Flow:
    1. User selects broker (Alpaca, OANDA, Hyperliquid, Mock)
    2. Enters API credentials
    3. Validates credentials
    4. Configures risk limits
    5. Confirms and creates session
    """

    def __init__(
        self,
        router: BrokerSessionRouter,
        vault=None,
        audit_log: AuditLog | None = None,
    ):
        """
        Initialize wizard.

        Args:
            router: BrokerSessionRouter instance
            vault: Secure vault for storing credentials (EncryptedKeyVault)
            audit_log: Audit logging instance
        """
        self.router = router
        self.vault = vault
        self.audit_log = audit_log or AuditLog()

        # In-memory state (in production, use Redis/DB)
        self.states: dict[str, OnboardingState] = {}

    def start_onboarding(self, user_id: str) -> OnboardingState:
        """Start wizard for user"""
        state = OnboardingState(
            step=WizardStep.WELCOME,
            user_id=user_id,
        )
        self.states[user_id] = state

        self.audit_log.log(
            action="ONBOARDING_STARTED",
            details={"user_id": user_id},
        )

        logger.info(f"Onboarding started for user={user_id}")
        return state

    def select_broker(self, user_id: str, broker_type: str) -> OnboardingState:
        """
        Step 1: Select broker

        Args:
            user_id: User identifier
            broker_type: "alpaca", "oanda", "hyperliquid", "mock"

        Returns:
            Updated state for next step
        """

        state = self._get_state(user_id)

        try:
            state.selected_broker = BrokerType(broker_type)
            state.step = WizardStep.CREDENTIALS
            state.updated_at = datetime.utcnow()

            logger.info(f"User {user_id} selected broker: {broker_type}")

            self.audit_log.log(
                action="BROKER_SELECTED",
                details={"user_id": user_id, "broker": broker_type},
            )

            return state

        except ValueError as e:
            raise ValueError(f"Unknown broker type: {broker_type}") from e

    def enter_credentials(
        self,
        user_id: str,
        credentials: dict[str, str],
    ) -> dict[str, Any]:
        """
        Step 2: Enter API credentials

        Args:
            user_id: User identifier
            credentials: {"api_key": "...", "secret_key": "..." (if applicable)}

        Returns:
            Validation hints for frontend
        """

        state = self._get_state(user_id)

        if not state.selected_broker:
            raise ValueError("Broker not selected yet")

        # Validate credentials format
        api_key = credentials.get("api_key", "").strip()
        secret_key = credentials.get("secret_key", "").strip()

        if not api_key:
            return {
                "valid": False,
                "errors": ["API key required"],
            }

        # Broker-specific validation
        validation = self._validate_credentials_format(state.selected_broker, api_key, secret_key)

        if not validation["valid"]:
            logger.warning(
                f"Invalid credentials for {state.selected_broker.value}: {validation['errors']}"
            )
            return validation

        # Store credentials temporarily (not persisted yet)
        state.credentials = credentials
        state.step = WizardStep.VALIDATION
        state.updated_at = datetime.utcnow()

        self.audit_log.log(
            action="CREDENTIALS_PROVIDED",
            details={"user_id": user_id, "broker": state.selected_broker.value},
        )

        return {
            "valid": True,
            "message": "Credentials format valid. Proceeding to validation...",
        }

    async def validate_credentials(self, user_id: str) -> dict[str, Any]:
        """
        Step 3: Validate credentials with actual broker

        Returns:
            {"valid": bool, "message": str, "account_info": {...}}
        """

        state = self._get_state(user_id)

        if state.step not in (WizardStep.VALIDATION, WizardStep.CREDENTIALS):
            raise ValueError(f"Invalid step: {state.step}")

        try:
            # Attempt to create session (returns session_id string)
            session_id = await self.router.create_session(
                user_id=user_id,
                broker_type=state.selected_broker,
                credentials=state.credentials,
            )

            state.session_id = session_id
            state.step = WizardStep.RISK_SETUP
            state.updated_at = datetime.utcnow()

            # Fetch account info via the broker session
            session_obj = await self.router.get_session(user_id)
            balance = {}
            if session_obj and hasattr(session_obj.broker, "get_account_balance"):
                try:
                    balance = await session_obj.broker.get_account_balance()
                except Exception:
                    balance = {"balance": 0, "equity": 0}

            logger.info(f"Credentials validated for user={user_id}")

            self.audit_log.log(
                action="CREDENTIALS_VALIDATED",
                details={"user_id": user_id, "session_id": session_id},
            )

            return {
                "valid": True,
                "message": "Credentials validated! Account connected.",
                "account_info": {
                    "broker": state.selected_broker.value,
                    "balance": balance.get("balance", 0) if isinstance(balance, dict) else 0,
                    "equity": balance.get("equity", 0) if isinstance(balance, dict) else 0,
                },
            }

        except Exception as e:
            logger.error(f"Credential validation failed: {e}")

            self.audit_log.log(
                action="CREDENTIALS_VALIDATION_FAILED",
                reason=str(e),
                details={"user_id": user_id},
            )

            return {
                "valid": False,
                "message": f"Validation failed: {str(e)}",
            }

    def configure_risk(
        self,
        user_id: str,
        config: dict[str, Any],
    ) -> OnboardingState:
        """
        Step 4: Configure risk limits

        Args:
            user_id: User identifier
            config: {
                "max_position_size": 0.10,  # 10% of account
                "max_drawdown": -0.15,       # -15%
                "max_daily_loss": -0.05,     # -5%
                "min_rr_ratio": 1.5,         # min 1:1.5 RR
            }

        Returns:
            Updated state
        """

        state = self._get_state(user_id)

        if state.step != WizardStep.RISK_SETUP:
            raise ValueError(f"Invalid step: {state.step}")

        # Validate risk config
        errors = self._validate_risk_config(config)
        if errors:
            raise ValueError(f"Invalid risk config: {errors}")

        state.risk_config = config
        state.step = WizardStep.CONFIRMATION
        state.updated_at = datetime.utcnow()

        logger.info(f"Risk config set for user={user_id}")

        self.audit_log.log(
            action="RISK_CONFIG_SET",
            details={"user_id": user_id, "config": config},
        )

        return state

    def get_confirmation_summary(self, user_id: str) -> dict[str, Any]:
        """Get summary for final confirmation step"""

        state = self._get_state(user_id)

        if state.step != WizardStep.CONFIRMATION:
            raise ValueError(f"Invalid step: {state.step}")

        return {
            "broker": state.selected_broker.value if state.selected_broker else None,
            "api_key_preview": f"...{state.credentials.get('api_key', '')[-4:]}",
            "risk_config": state.risk_config,
            "ready_to_confirm": bool(state.session_id),
        }

    async def confirm_and_complete(self, user_id: str) -> dict[str, Any]:
        """
        Step 5: Confirm setup and complete onboarding

        Returns:
            {"success": bool, "session_id": str, "next_steps": [...]}
        """

        state = self._get_state(user_id)

        if state.step != WizardStep.CONFIRMATION:
            raise ValueError(f"Invalid step: {state.step}")

        if not state.session_id:
            raise ValueError("No valid session")

        # Store credentials securely
        if self.vault:
            try:
                self.vault.store(
                    user_id=user_id,
                    broker=state.selected_broker.value,
                    credentials=state.credentials,
                )
                logger.info(f"Credentials stored securely for user={user_id}")
            except Exception as e:
                logger.error(f"Failed to store credentials: {e}")
                # Continue anyway, session is already active

        state.step = WizardStep.COMPLETE
        state.updated_at = datetime.utcnow()

        self.audit_log.log(
            action="ONBOARDING_COMPLETED",
            details={
                "user_id": user_id,
                "broker": state.selected_broker.value,
                "session_id": state.session_id,
            },
        )

        logger.info(f"Onboarding completed for user={user_id}")

        return {
            "success": True,
            "session_id": state.session_id,
            "broker": state.selected_broker.value,
            "next_steps": [
                "Go to Dashboard to view account status",
                "Configure trading strategies",
                "Start trading with small position sizes",
            ],
        }

    def _get_state(self, user_id: str) -> OnboardingState:
        """Get or create onboarding state"""
        if user_id not in self.states:
            raise ValueError(f"Onboarding not started for user={user_id}")
        return self.states[user_id]

    @staticmethod
    def _validate_credentials_format(
        broker_type: BrokerType,
        api_key: str,
        secret_key: str | None = None,
    ) -> dict[str, Any]:
        """Validate credential format (before hitting broker)"""

        if not api_key or len(api_key) < 10:
            return {
                "valid": False,
                "errors": ["API key too short"],
            }

        if broker_type == BrokerType.HYPERLIQUID:
            # Hyperliquid needs private key
            if not secret_key:
                return {
                    "valid": False,
                    "errors": ["Secret key (private key) required for Hyperliquid"],
                }

            if not secret_key.startswith("0x") and len(secret_key) != 64:
                return {
                    "valid": False,
                    "errors": [
                        "Secret key must be valid Ethereum private key (64 hex chars or 0x-prefixed)"
                    ],
                }

        return {"valid": True}

    @staticmethod
    def _validate_risk_config(config: dict[str, Any]) -> list[str]:
        """Validate risk configuration"""
        errors = []

        # Position size
        pos_size = config.get("max_position_size", 0.1)
        if not (0.01 <= pos_size <= 0.5):
            errors.append(f"Position size must be 1-50%, got {pos_size * 100}%")

        # Drawdown
        drawdown = config.get("max_drawdown", -0.15)
        if not (-0.5 <= drawdown <= -0.01):
            errors.append(f"Drawdown must be -1% to -50%, got {drawdown * 100}%")

        # Daily loss
        daily = config.get("max_daily_loss", -0.05)
        if not (-0.2 <= daily <= -0.01):
            errors.append(f"Daily loss must be -1% to -20%, got {daily * 100}%")

        # R/R ratio
        rr = config.get("min_rr_ratio", 1.5)
        if not (1.0 <= rr <= 5.0):
            errors.append(f"R/R ratio must be 1.0-5.0, got {rr}")

        return errors


class OnboardingError(Exception):
    """Onboarding error"""

    pass
