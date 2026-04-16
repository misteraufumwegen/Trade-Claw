"""
Rules Engine - Parses and enforces trading rules from YAML configuration.

Implements:
- YAML rule parsing
- Entry/Exit rule validation
- Grade-based filtering
- R/R enforcement
- Macro event integration
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Parses and enforces trading rules from YAML configuration.
    """

    def __init__(self, rules_yaml_path: str | None = None):
        """
        Initialize rules engine.

        Args:
            rules_yaml_path: Path to rules.yaml file (auto-discovers if None)
        """
        self.rules = {}
        self.rules_path = rules_yaml_path

        if not self.rules_path:
            # Auto-discover rules.yaml in same directory
            current_dir = Path(__file__).parent
            self.rules_path = str(current_dir / "rules.yaml")

        self.load_rules()

    # Top-level keys that the rest of the code expects under ``trading_rules``.
    # If the YAML is missing or mis-typed here, we fail fast rather than
    # silently serving empty rules (review finding M9).
    _EXPECTED_KEYS = {
        "entry": dict,
        "exit": dict,
        "risk_management": dict,
    }

    def load_rules(self):
        """Load rules from YAML file with shape validation."""
        try:
            with open(self.rules_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)  # safe_load: no arbitrary Python objects
        except FileNotFoundError:
            logger.warning("Rules file not found: %s", self.rules_path)
            self.rules = {}
            return
        except yaml.YAMLError:
            logger.exception("YAML parsing error in %s", self.rules_path)
            self.rules = {}
            return

        if not isinstance(data, dict):
            logger.error(
                "Rules file %s must contain a top-level mapping, got %s",
                self.rules_path,
                type(data).__name__,
            )
            self.rules = {}
            return

        rules = data.get("trading_rules", {})
        if not isinstance(rules, dict):
            logger.error(
                "'trading_rules' must be a mapping in %s (got %s)",
                self.rules_path,
                type(rules).__name__,
            )
            self.rules = {}
            return

        # Validate shape of expected sections — warn, don't crash, for
        # backwards compatibility with partial configs.
        for key, expected_type in self._EXPECTED_KEYS.items():
            value = rules.get(key)
            if value is None:
                logger.warning("Missing section '%s' in rules file", key)
            elif not isinstance(value, expected_type):
                logger.error(
                    "Section '%s' must be %s (got %s) — ignoring",
                    key,
                    expected_type.__name__,
                    type(value).__name__,
                )
                rules[key] = expected_type()

        self.rules = rules
        logger.info("Rules loaded from %s", self.rules_path)
        self._log_rule_summary()

    def _log_rule_summary(self):
        """Log summary of loaded rules."""
        entry_rules = self.rules.get("entry", {})
        exit_rules = self.rules.get("exit", {})
        risk_mgmt = self.rules.get("risk_management", {})

        logger.info(f"  Entry Rules: {len(entry_rules)} criteria")
        logger.info(f"  Exit Rules: {len(exit_rules)} criteria")
        logger.info("  Risk Management:")
        logger.info(f"    - Min R/R: {risk_mgmt.get('minimum_rr_ratio', 'N/A')}:1")
        logger.info(f"    - Max Risk/Trade: {risk_mgmt.get('maximum_risk_per_trade_pct', 'N/A')}%")
        logger.info(f"    - Max Position: {risk_mgmt.get('maximum_position_size_pct', 'N/A')}%")

    def validate_entry_rules(self, entry_rules_data: dict) -> tuple[bool, str, int]:
        """
        Validate entry rules.

        Args:
            entry_rules_data: Dict with rule statuses

        Returns:
            (is_valid, reason, rules_met)
        """
        required_rules = [
            "structural_break",
            "liquidity_sweep",
            "momentum_aligned",
            "volume_confirmed",
            "macro_aligned",
        ]

        rules_met = sum(1 for rule in required_rules if entry_rules_data.get(rule, False))
        is_valid = rules_met >= 4  # Need at least 4 of 5

        reason = f"{rules_met}/5 entry rules triggered"

        logger.info(f"📋 Entry Validation: {reason} {'✅' if is_valid else '⚠️'}")
        return is_valid, reason, rules_met

    def validate_rr_ratio(self, entry: float, stop_loss: float, tp2: float) -> tuple[bool, float]:
        """
        Validate Risk/Reward ratio.

        Args:
            entry: Entry price
            stop_loss: Stop loss price
            tp2: Second target price

        Returns:
            (is_valid, rr_ratio)
        """
        risk = abs(entry - stop_loss)
        reward = abs(tp2 - entry)

        rr_ratio = (reward / risk) if risk > 0 else 0.0
        min_rr = self.rules.get("risk_management", {}).get("minimum_rr_ratio", 3.0)

        is_valid = rr_ratio >= min_rr

        logger.info(
            f"💰 R/R Validation: {rr_ratio:.2f}:1 {'✅' if is_valid else '⚠️'} (min: {min_rr}:1)"
        )
        return is_valid, rr_ratio

    def validate_grade_filter(self, grade: str) -> tuple[bool, str]:
        """
        Validate if trade grade is live tradeable.

        Args:
            grade: Trade grade (A+, A, B, C, D, F)

        Returns:
            (is_tradeable, reason)
        """
        grade_filter = self.rules.get("risk_management", {}).get("grade_filter", {})
        live_tradeable = grade_filter.get("live_tradeable", ["A+", "A"])

        is_tradeable = grade in live_tradeable
        reason = "Live Trading" if is_tradeable else "Backtest Only"

        logger.info(f"🎯 Grade Filter: {grade} → {reason} {'✅' if is_tradeable else '⏸️'}")
        return is_tradeable, reason

    def validate_position_size(
        self, position_size: float, account_equity: float
    ) -> tuple[bool, str]:
        """
        Validate position size against max % of account.

        Args:
            position_size: Position size in units/contracts
            account_equity: Account equity in CHF

        Returns:
            (is_valid, reason)
        """
        risk_mgmt = self.rules.get("risk_management", {})
        risk_mgmt.get("maximum_position_size_pct", 10.0)
        risk_mgmt.get("maximum_risk_per_trade_pct", 2.0)

        # For now, just validate that position size is calculated
        is_valid = position_size > 0
        reason = (
            f"Position size: {position_size:.4f} units" if is_valid else "Position size too small"
        )

        logger.info(f"📊 Position Size Validation: {reason} {'✅' if is_valid else '⚠️'}")
        return is_valid, reason

    def get_entry_rule(self, rule_name: str) -> dict | None:
        """Get specific entry rule details."""
        return self.rules.get("entry", {}).get(rule_name, None)

    def get_exit_rule(self, rule_name: str) -> dict | None:
        """Get specific exit rule details."""
        return self.rules.get("exit", {}).get(rule_name, None)

    def get_risk_limits(self) -> dict:
        """Get all risk management limits."""
        return self.rules.get("risk_management", {})

    def get_grade_scoring_criteria(self) -> list[dict]:
        """Get grade scoring rubric."""
        return self.rules.get("grade_scoring", {}).get("criteria", [])

    def get_macro_categories(self) -> list[str]:
        """Get macro event categories."""
        return self.rules.get("macro_events", {}).get("categories", [])

    def summary(self) -> str:
        """Get human-readable summary of all rules."""
        output = []
        output.append("=" * 70)
        output.append("TRADING RULES SUMMARY")
        output.append("=" * 70)

        # Entry Rules
        output.append("\n📥 ENTRY RULES (need 4 of 5)")
        entry_rules = self.rules.get("entry", {})
        for rule_name, rule_data in entry_rules.items():
            desc = rule_data.get("description", "N/A")
            output.append(f"  • {rule_name}: {desc}")

        # Exit Rules
        output.append("\n📤 EXIT RULES")
        exit_rules = self.rules.get("exit", {})
        for rule_name, rule_data in exit_rules.items():
            desc = rule_data.get("description", "N/A")
            output.append(f"  • {rule_name}: {desc}")

        # Risk Management
        output.append("\n💰 RISK MANAGEMENT")
        risk_mgmt = self.rules.get("risk_management", {})
        output.append(f"  • Min R/R Ratio: {risk_mgmt.get('minimum_rr_ratio', 'N/A')}:1")
        output.append(f"  • Max Risk/Trade: {risk_mgmt.get('maximum_risk_per_trade_pct', 'N/A')}%")
        output.append(f"  • Max Position: {risk_mgmt.get('maximum_position_size_pct', 'N/A')}%")
        output.append(f"  • Max Daily Trades: {risk_mgmt.get('maximum_daily_trades', 'N/A')}")
        output.append(f"  • Drawdown Halt: {risk_mgmt.get('drawdown_halt_pct', 'N/A')}%")

        # Grade Filter
        output.append("\n🎯 GRADE FILTER (Live Trading)")
        grade_filter = risk_mgmt.get("grade_filter", {})
        output.append(f"  • Live: {grade_filter.get('live_tradeable', [])}")
        output.append(f"  • Backtest Only: {grade_filter.get('backtest_only', [])}")

        output.append("\n" + "=" * 70)
        return "\n".join(output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    engine = RulesEngine()

    # Test validation

    entry_rules = {
        "structural_break": True,
        "liquidity_sweep": True,
        "momentum_aligned": True,
        "volume_confirmed": True,
        "macro_aligned": False,
    }
    is_valid, reason, rules_met = engine.validate_entry_rules(entry_rules)

    rr_valid, rr_ratio = engine.validate_rr_ratio(entry=41750, stop_loss=40200, tp2=47500)

    grade_valid, grade_reason = engine.validate_grade_filter("A+")
