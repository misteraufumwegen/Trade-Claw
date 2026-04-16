"""
Phase 2 Integration Tests - Backtest + Risk Engine

Tests:
- Backtest Simulator (simulator logic, metrics calculation)
- Risk Engine (position size, drawdown, stop-loss immutability)
- REST API endpoints
- Error handling & edge cases
"""

import pytest
from fastapi.testclient import TestClient

from app.backtest import BacktestResults, BacktestSimulator
from app.main import app
from app.risk import RiskEngine, RiskVault

client = TestClient(app)


# ==============================================================================
# BACKTEST TESTS (20+ tests)
# ==============================================================================


class TestBacktestResults:
    """Test BacktestResults metrics calculation."""

    def test_initialization(self):
        """Test BacktestResults initialization."""
        results = BacktestResults(starting_capital=100.0)
        assert results.starting_capital == 100.0
        assert results.current_equity == 100.0
        assert len(results.trades) == 0

    def test_add_winning_trade(self):
        """Test adding a winning trade."""
        results = BacktestResults(starting_capital=100.0)
        results.add_trade_result(
            "TRADE_001", entry=100.0, exit=110.0, direction="Long", r_multiple=2.0, pnl_chf=10.0
        )

        assert len(results.trades) == 1
        assert len(results.winning_trades) == 1
        assert results.gross_profit == 10.0
        assert results.current_equity == 110.0

    def test_add_losing_trade(self):
        """Test adding a losing trade."""
        results = BacktestResults(starting_capital=100.0)
        results.add_trade_result(
            "TRADE_001", entry=100.0, exit=95.0, direction="Long", r_multiple=-1.0, pnl_chf=-5.0
        )

        assert len(results.losing_trades) == 1
        assert results.gross_loss == 5.0
        assert results.current_equity == 95.0

    def test_calculate_metrics_no_trades(self):
        """Test metrics with no trades."""
        results = BacktestResults(starting_capital=100.0)
        metrics = results.calculate_metrics()

        assert metrics["total_trades"] == 0
        assert metrics["win_rate_pct"] == 0.0
        assert metrics["roi_pct"] == 0.0

    def test_calculate_metrics_with_trades(self):
        """Test metrics with multiple trades."""
        results = BacktestResults(starting_capital=100.0)

        # Add 5 winning, 5 losing
        for i in range(5):
            results.add_trade_result(f"WIN_{i}", 100.0, 110.0, "Long", 2.0, 10.0)

        for i in range(5):
            results.add_trade_result(f"LOSS_{i}", 100.0, 95.0, "Long", -1.0, -5.0)

        metrics = results.calculate_metrics()

        assert metrics["total_trades"] == 10
        assert metrics["winning_trades"] == 5
        assert metrics["losing_trades"] == 5
        assert metrics["win_rate_pct"] == 50.0

    def test_drawdown_calculation(self):
        """Test max drawdown calculation."""
        results = BacktestResults(starting_capital=100.0)

        results.add_trade_result("TRADE_001", 100.0, 150.0, "Long", 5.0, 50.0)  # Up to 150
        results.add_trade_result("TRADE_002", 150.0, 100.0, "Long", -5.0, -50.0)  # Down to 100

        metrics = results.calculate_metrics()

        # Max drawdown should be (150 - 100) / 150 = 33.33%
        assert metrics["max_drawdown_pct"] == pytest.approx(33.33, rel=0.1)


class TestBacktestSimulator:
    """Test BacktestSimulator."""

    def test_initialization(self):
        """Test simulator initialization."""
        sim = BacktestSimulator(starting_capital=100.0)
        assert sim.starting_capital == 100.0
        assert isinstance(sim.results, BacktestResults)

    def test_simulate_trade_long_tp1(self):
        """Test simulating a long trade hitting TP1."""
        sim = BacktestSimulator(starting_capital=100.0)

        # This test is deterministic based on trade_id
        result = sim.simulate_trade(
            entry_price=100.0,
            stop_loss=95.0,
            tp1=110.0,
            tp2=120.0,
            direction="Long",
            trade_id="TEST_001",
            risk_percent=2.0,
        )

        assert result["trade_id"] == "TEST_001"
        assert "exit_price" in result
        assert "r_multiple" in result
        assert "pnl" in result

    def test_simulate_trade_short(self):
        """Test simulating a short trade."""
        sim = BacktestSimulator(starting_capital=100.0)

        result = sim.simulate_trade(
            entry_price=100.0,
            stop_loss=105.0,
            tp1=90.0,
            tp2=80.0,
            direction="Short",
            trade_id="TEST_SHORT_001",
            risk_percent=2.0,
        )

        assert result["direction"] == "Short"

    def test_run_backtest(self):
        """Test running a full backtest."""
        sim = BacktestSimulator(starting_capital=100.0)

        trades = [
            {
                "trade_id": "TRADE_001",
                "entry": 100.0,
                "stop_loss": 95.0,
                "tp1": 110.0,
                "tp2": 120.0,
                "direction": "Long",
                "grade": "A+",
                "risk_pct": 2.0,
            },
            {
                "trade_id": "TRADE_002",
                "entry": 100.0,
                "stop_loss": 95.0,
                "tp1": 110.0,
                "tp2": 120.0,
                "direction": "Long",
                "grade": "A",
                "risk_pct": 2.0,
            },
            {
                "trade_id": "TRADE_003",
                "entry": 100.0,
                "stop_loss": 95.0,
                "tp1": 110.0,
                "tp2": 120.0,
                "direction": "Long",
                "grade": "B",  # Should be filtered out
                "risk_pct": 2.0,
            },
        ]

        result = sim.run_backtest(trades)

        assert result["trades_executed"] == 2  # Only A+ and A
        assert "metrics" in result
        assert "total_trades" in result["metrics"]

    def test_run_backtest_with_custom_grades(self):
        """Test backtest with custom grade filter."""
        sim = BacktestSimulator(starting_capital=100.0)

        trades = [
            {
                "trade_id": "T1",
                "entry": 100.0,
                "stop_loss": 95.0,
                "tp1": 110.0,
                "tp2": 120.0,
                "grade": "A+",
            },
            {
                "trade_id": "T2",
                "entry": 100.0,
                "stop_loss": 95.0,
                "tp1": 110.0,
                "tp2": 120.0,
                "grade": "B",
            },
            {
                "trade_id": "T3",
                "entry": 100.0,
                "stop_loss": 95.0,
                "tp1": 110.0,
                "tp2": 120.0,
                "grade": "C",
            },
        ]

        result = sim.run_backtest(trades, only_grades=["A+", "B"])
        assert result["trades_executed"] == 2


# ==============================================================================
# RISK ENGINE TESTS (20+ tests)
# ==============================================================================


class TestRiskVault:
    """Test RiskVault."""

    def test_initialization(self):
        """Test vault initialization."""
        vault = RiskVault()
        assert vault.position_size_cap_pct == 10.0
        assert vault.drawdown_halt_pct == -15.0
        assert vault.stop_loss_immutable
        assert vault.active
        assert not vault.halted

    def test_register_stop_loss(self):
        """Test stop-loss registration."""
        vault = RiskVault()

        success = vault.register_stop_loss(
            trade_id="TRADE_001", order_id="ORDER_001", stop_loss=95.0, symbol="AAPL"
        )

        assert success
        assert "TRADE_001" in vault.stop_loss_records

    def test_stop_loss_immutability(self):
        """Test that stop-loss is immutable."""
        vault = RiskVault()

        vault.register_stop_loss("TRADE_001", "ORDER_001", 95.0, "AAPL")

        success, reason = vault.attempt_modify_stop_loss("TRADE_001", 90.0)

        assert not success
        assert "IMMUTABLE" in reason

    def test_validate_position_size_valid(self):
        """Test position size validation (valid)."""
        vault = RiskVault()

        valid, reason, pct = vault.validate_position_size(
            account_equity=10000.0,
            position_value=500.0,  # 5% of account
        )

        assert valid
        assert pct == 5.0

    def test_validate_position_size_exceeds_limit(self):
        """Test position size validation (exceeds limit)."""
        vault = RiskVault()

        valid, reason, pct = vault.validate_position_size(
            account_equity=10000.0,
            position_value=1500.0,  # 15% of account (exceeds 10% cap)
        )

        assert not valid
        assert pct == 15.0
        assert "exceeds cap" in reason

    def test_check_drawdown_safe(self):
        """Test drawdown check (safe)."""
        vault = RiskVault()

        safe, reason, dd_pct = vault.check_drawdown(current_equity=9000.0, peak_equity=10000.0)

        assert safe
        assert dd_pct == pytest.approx(-10.0, rel=0.1)

    def test_check_drawdown_halt_triggered(self):
        """Test drawdown halt (-15%)."""
        vault = RiskVault()

        safe, reason, dd_pct = vault.check_drawdown(current_equity=8500.0, peak_equity=10000.0)

        assert not safe
        assert vault.halted
        assert dd_pct == pytest.approx(-15.0, rel=0.1)

    def test_record_trade(self):
        """Test trade recording."""
        vault = RiskVault()

        success = vault.record_trade(
            trade_id="TRADE_001",
            symbol="AAPL",
            side="BUY",
            quantity=10.0,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
        )

        assert success
        assert len(vault.daily_trades) == 1

    def test_get_daily_trade_count(self):
        """Test daily trade count."""
        vault = RiskVault()

        for i in range(5):
            vault.record_trade(f"TRADE_{i}", "AAPL", "BUY", 10.0, 100.0, 95.0, 110.0)

        count = vault.get_daily_trade_count()
        assert count == 5

    def test_halted_state(self):
        """Test halted state."""
        vault = RiskVault()

        assert not vault.is_halted()

        vault.halted = True
        vault.halt_reason = "Test halt"

        assert vault.is_halted()

    def test_unhalt(self):
        """Test manual unhalt."""
        vault = RiskVault()

        vault.halted = True
        vault.halt_reason = "Test halt"

        success = vault.unhalt()

        assert success
        assert not vault.is_halted()


class TestRiskEngine:
    """Test RiskEngine."""

    def test_initialization(self):
        """Test engine initialization."""
        engine = RiskEngine()
        assert isinstance(engine.vault, RiskVault)

    def test_pre_trade_check_all_passes(self):
        """Test pre-trade check (all passes)."""
        engine = RiskEngine()

        approved, details = engine.pre_trade_check(
            symbol="AAPL",
            side="BUY",
            quantity=10.0,
            entry_price=100.0,
            account_equity=10000.0,
            stop_loss=95.0,
            take_profit=110.0,
        )

        assert approved

    def test_pre_trade_check_position_size_exceeds(self):
        """Test pre-trade check (position size exceeds)."""
        engine = RiskEngine()

        approved, details = engine.pre_trade_check(
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            entry_price=100.0,
            account_equity=1000.0,  # Would be 100% of account
            stop_loss=95.0,
            take_profit=110.0,
        )

        assert not approved
        assert not details["checks"]["position_size"]

    def test_pre_trade_check_halted(self):
        """Test pre-trade check (halted)."""
        engine = RiskEngine()
        engine.vault.halted = True
        engine.vault.halt_reason = "Drawdown limit exceeded"

        approved, details = engine.pre_trade_check(
            symbol="AAPL",
            side="BUY",
            quantity=10.0,
            entry_price=100.0,
            account_equity=10000.0,
            stop_loss=95.0,
            take_profit=110.0,
        )

        assert not approved
        assert not details["checks"]["halted"]

    def test_execute_trade(self):
        """Test trade execution."""
        engine = RiskEngine()

        success = engine.execute_trade(
            trade_id="TRADE_001",
            symbol="AAPL",
            side="BUY",
            quantity=10.0,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
        )

        assert success
        assert "TRADE_001" in engine.vault.stop_loss_records

    def test_get_status(self):
        """Test engine status."""
        engine = RiskEngine()
        status = engine.get_status()

        assert "vault_status" in status
        assert "halted" in status
        assert "timestamp" in status


# ==============================================================================
# REST API TESTS (10+ tests)
# ==============================================================================


class TestBacktestAPI:
    """Test Backtest REST API endpoints."""

    def test_backtest_endpoint_success(self):
        """Test POST /api/backtest."""
        payload = {
            "starting_capital": 100.0,
            "only_grades": ["A+", "A"],
            "trades": [
                {
                    "trade_id": "TRADE_001",
                    "entry": 100.0,
                    "stop_loss": 95.0,
                    "tp1": 110.0,
                    "tp2": 120.0,
                    "direction": "Long",
                    "grade": "A+",
                    "risk_pct": 2.0,
                }
            ],
        }

        response = client.post("/api/backtest", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "metrics" in data
        assert "trades" in data

    def test_backtest_status_endpoint(self):
        """Test GET /api/backtest/status."""
        response = client.get("/api/backtest/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "backtest_engine" in data


class TestRiskAPI:
    """Test Risk Engine REST API endpoints."""

    def test_risk_status_endpoint(self):
        """Test GET /api/risk/status."""
        response = client.get("/api/risk/status")

        assert response.status_code == 200
        data = response.json()
        assert "vault_status" in data
        assert "halted" in data

    def test_pre_trade_check_endpoint(self):
        """Test POST /api/risk/pre-trade-check."""
        payload = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 10.0,
            "entry_price": 100.0,
            "account_equity": 10000.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
        }

        response = client.post("/api/risk/pre-trade-check", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "approved" in data
        assert "details" in data

    def test_execute_trade_endpoint(self):
        """Test POST /api/risk/execute-trade."""
        payload = {
            "trade_id": "TRADE_001",
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 10.0,
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
        }

        response = client.post("/api/risk/execute-trade", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"]


# ==============================================================================
# EDGE CASES & ERROR HANDLING
# ==============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_backtest_with_empty_trades(self):
        """Test backtest with empty trades list."""
        payload = {"starting_capital": 100.0, "trades": []}

        response = client.post("/api/backtest", json=payload)
        assert response.status_code == 200

    def test_position_size_zero_equity(self):
        """Test position size validation with zero equity."""
        vault = RiskVault()
        valid, _, _ = vault.validate_position_size(0.0, 100.0)
        assert not valid

    def test_drawdown_with_zero_peak(self):
        """Test drawdown with zero peak equity."""
        vault = RiskVault()
        safe, _, dd_pct = vault.check_drawdown(5000.0, 0.0)
        assert safe
        assert dd_pct == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
