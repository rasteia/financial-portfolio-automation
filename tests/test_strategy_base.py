"""
Unit tests for the base strategy framework.

Tests the abstract Strategy base class, StrategySignal, and StrategyState
components of the strategy framework.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

from financial_portfolio_automation.strategy.base import (
    Strategy, StrategySignal, StrategyState, SignalType
)
from financial_portfolio_automation.models.core import (
    Quote, Position, PortfolioSnapshot, OrderSide
)
from financial_portfolio_automation.models.config import (
    StrategyConfig, StrategyType, RiskLimits
)


class TestStrategySignal:
    """Test cases for StrategySignal class."""
    
    def test_valid_signal_creation(self):
        """Test creating a valid strategy signal."""
        signal = StrategySignal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.8,
            price=Decimal('150.00'),
            quantity=100
        )
        
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == 0.8
        assert signal.price == Decimal('150.00')
        assert signal.quantity == 100
        assert isinstance(signal.timestamp, datetime)
        assert isinstance(signal.metadata, dict)
    
    def test_signal_validation_invalid_symbol(self):
        """Test signal validation with invalid symbol."""
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            StrategySignal(
                symbol="",
                signal_type=SignalType.BUY,
                strength=0.8
            )
    
    def test_signal_validation_invalid_signal_type(self):
        """Test signal validation with invalid signal type."""
        with pytest.raises(ValueError, match="Signal type must be a SignalType enum value"):
            StrategySignal(
                symbol="AAPL",
                signal_type="invalid",
                strength=0.8
            )
    
    def test_signal_validation_invalid_strength(self):
        """Test signal validation with invalid strength."""
        with pytest.raises(ValueError, match="Signal strength must be between 0.0 and 1.0"):
            StrategySignal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=1.5
            )
        
        with pytest.raises(ValueError, match="Signal strength must be between 0.0 and 1.0"):
            StrategySignal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=-0.1
            )
    
    def test_signal_validation_invalid_price(self):
        """Test signal validation with invalid price."""
        with pytest.raises(ValueError, match="Price must be positive"):
            StrategySignal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=0.8,
                price=Decimal('-10.00')
            )
    
    def test_signal_validation_invalid_quantity(self):
        """Test signal validation with invalid quantity."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            StrategySignal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=0.8,
                quantity=-10
            )


class TestStrategyState:
    """Test cases for StrategyState class."""
    
    def test_strategy_state_creation(self):
        """Test creating strategy state."""
        state = StrategyState(strategy_id="test_strategy")
        
        assert state.strategy_id == "test_strategy"
        assert state.is_active is True
        assert isinstance(state.last_update, datetime)
        assert len(state.positions) == 0
        assert state.signals_generated == 0
        assert state.trades_executed == 0
        assert state.total_pnl == Decimal('0')
        assert isinstance(state.metadata, dict)
    
    def test_update_position(self):
        """Test updating position in strategy state."""
        state = StrategyState(strategy_id="test_strategy")
        position = Position(
            symbol="AAPL",
            quantity=100,
            market_value=Decimal('15000'),
            cost_basis=Decimal('14000'),
            unrealized_pnl=Decimal('1000'),
            day_pnl=Decimal('500')
        )
        
        initial_update_time = state.last_update
        # Add a small delay to ensure timestamp difference
        import time
        time.sleep(0.001)
        state.update_position(position)
        
        assert "AAPL" in state.positions
        assert state.positions["AAPL"] == position
        assert state.last_update >= initial_update_time
    
    def test_remove_position(self):
        """Test removing position from strategy state."""
        state = StrategyState(strategy_id="test_strategy")
        position = Position(
            symbol="AAPL",
            quantity=100,
            market_value=Decimal('15000'),
            cost_basis=Decimal('14000'),
            unrealized_pnl=Decimal('1000'),
            day_pnl=Decimal('500')
        )
        
        state.update_position(position)
        assert "AAPL" in state.positions
        
        state.remove_position("AAPL")
        assert "AAPL" not in state.positions
    
    def test_increment_counters(self):
        """Test incrementing signals and trades counters."""
        state = StrategyState(strategy_id="test_strategy")
        
        initial_signals = state.signals_generated
        initial_trades = state.trades_executed
        
        state.increment_signals()
        assert state.signals_generated == initial_signals + 1
        
        state.increment_trades()
        assert state.trades_executed == initial_trades + 1
    
    def test_update_pnl(self):
        """Test updating total PnL."""
        state = StrategyState(strategy_id="test_strategy")
        
        state.update_pnl(Decimal('100'))
        assert state.total_pnl == Decimal('100')
        
        state.update_pnl(Decimal('-50'))
        assert state.total_pnl == Decimal('50')


class MockStrategy(Strategy):
    """Mock strategy implementation for testing."""
    
    def generate_signals(self, market_data, portfolio, historical_data=None):
        """Mock signal generation."""
        signals = []
        for symbol in self.symbols:
            if symbol in market_data:
                signal = StrategySignal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strength=0.7,
                    price=market_data[symbol].mid_price
                )
                signals.append(signal)
        return signals
    
    def update_state(self, market_data, portfolio):
        """Mock state update."""
        self.state.last_update = datetime.now(timezone.utc)


class TestStrategy:
    """Test cases for Strategy base class."""
    
    @pytest.fixture
    def risk_limits(self):
        """Create test risk limits."""
        return RiskLimits(
            max_position_size=Decimal('10000'),
            max_portfolio_concentration=0.2,
            max_daily_loss=Decimal('1000'),
            max_drawdown=0.1,
            stop_loss_percentage=0.05
        )
    
    @pytest.fixture
    def strategy_config(self, risk_limits):
        """Create test strategy configuration."""
        return StrategyConfig(
            strategy_id="test_momentum",
            strategy_type=StrategyType.MOMENTUM,
            name="Test Momentum Strategy",
            description="Test strategy for unit tests",
            parameters={
                'lookback_period': 20,
                'momentum_threshold': 0.02,
                'min_signal_strength': 0.6
            },
            symbols=["AAPL", "GOOGL"],
            risk_limits=risk_limits
        )
    
    @pytest.fixture
    def mock_strategy(self, strategy_config):
        """Create mock strategy instance."""
        return MockStrategy(strategy_config)
    
    def test_strategy_initialization(self, mock_strategy, strategy_config):
        """Test strategy initialization."""
        assert mock_strategy.strategy_id == "test_momentum"
        assert mock_strategy.strategy_type == "momentum"
        assert mock_strategy.symbols == ["AAPL", "GOOGL"]
        assert mock_strategy.risk_limits == strategy_config.risk_limits
        assert mock_strategy.is_active is True
        assert isinstance(mock_strategy.state, StrategyState)
    
    def test_strategy_activation_deactivation(self, mock_strategy):
        """Test strategy activation and deactivation."""
        assert mock_strategy.is_active is True
        
        mock_strategy.deactivate()
        assert mock_strategy.is_active is False
        
        mock_strategy.activate()
        assert mock_strategy.is_active is True
    
    def test_validate_signal_valid(self, mock_strategy):
        """Test signal validation with valid signal."""
        signal = StrategySignal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.8
        )
        
        assert mock_strategy.validate_signal(signal) is True
    
    def test_validate_signal_invalid_symbol(self, mock_strategy):
        """Test signal validation with invalid symbol."""
        signal = StrategySignal(
            symbol="MSFT",  # Not in strategy symbols
            signal_type=SignalType.BUY,
            strength=0.8
        )
        
        assert mock_strategy.validate_signal(signal) is False
    
    def test_validate_signal_weak_strength(self, mock_strategy):
        """Test signal validation with weak signal strength."""
        signal = StrategySignal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.5  # Below min_signal_strength of 0.6
        )
        
        assert mock_strategy.validate_signal(signal) is False
    
    def test_calculate_position_size(self, mock_strategy):
        """Test position size calculation."""
        signal = StrategySignal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.8
        )
        
        portfolio_value = Decimal('100000')
        current_price = Decimal('150')
        
        position_size = mock_strategy.calculate_position_size(
            signal, portfolio_value, current_price
        )
        
        assert isinstance(position_size, int)
        assert position_size > 0
        
        # Check that position size respects risk limits
        position_value = position_size * current_price
        max_position_value = mock_strategy.risk_limits.calculate_max_position_value(portfolio_value)
        assert position_value <= max_position_value
    
    def test_calculate_position_size_minimum(self, mock_strategy):
        """Test position size calculation with minimum constraints."""
        signal = StrategySignal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.1  # Very weak signal
        )
        
        portfolio_value = Decimal('1000')  # Small portfolio
        current_price = Decimal('1000')    # Expensive stock
        
        position_size = mock_strategy.calculate_position_size(
            signal, portfolio_value, current_price
        )
        
        # Should still return at least 1 share
        assert position_size >= 1
    
    def test_get_performance_metrics(self, mock_strategy):
        """Test getting performance metrics."""
        # Update some state
        mock_strategy.state.signals_generated = 10
        mock_strategy.state.trades_executed = 5
        mock_strategy.state.total_pnl = Decimal('500')
        
        metrics = mock_strategy.get_performance_metrics()
        
        assert metrics['strategy_id'] == "test_momentum"
        assert metrics['strategy_type'] == "momentum"
        assert metrics['is_active'] is True
        assert metrics['signals_generated'] == 10
        assert metrics['trades_executed'] == 5
        assert metrics['total_pnl'] == 500.0
        assert metrics['symbols'] == ["AAPL", "GOOGL"]
    
    def test_reset_state(self, mock_strategy):
        """Test resetting strategy state."""
        # Modify state
        mock_strategy.state.signals_generated = 10
        mock_strategy.state.trades_executed = 5
        mock_strategy.state.total_pnl = Decimal('500')
        
        mock_strategy.reset_state()
        
        assert mock_strategy.state.signals_generated == 0
        assert mock_strategy.state.trades_executed == 0
        assert mock_strategy.state.total_pnl == Decimal('0')
        assert len(mock_strategy.state.positions) == 0
    
    def test_update_config(self, mock_strategy, risk_limits):
        """Test updating strategy configuration."""
        new_config = StrategyConfig(
            strategy_id="test_momentum",  # Same ID
            strategy_type=StrategyType.MOMENTUM,  # Same type
            name="Updated Test Strategy",
            description="Updated description",
            parameters={
                'lookback_period': 30,  # Changed parameter
                'momentum_threshold': 0.03,
                'min_signal_strength': 0.7
            },
            symbols=["AAPL", "GOOGL", "TSLA"],  # Added symbol
            risk_limits=risk_limits
        )
        
        mock_strategy.update_config(new_config)
        
        assert mock_strategy.config.name == "Updated Test Strategy"
        assert mock_strategy.config.parameters['lookback_period'] == 30
        assert "TSLA" in mock_strategy.symbols
    
    def test_update_config_invalid_id(self, mock_strategy, risk_limits):
        """Test updating configuration with different strategy ID."""
        new_config = StrategyConfig(
            strategy_id="different_id",  # Different ID
            strategy_type=StrategyType.MOMENTUM,
            name="Test Strategy",
            description="Test description",
            parameters={'lookback_period': 20, 'momentum_threshold': 0.02},
            symbols=["AAPL"],
            risk_limits=risk_limits
        )
        
        with pytest.raises(ValueError, match="Cannot change strategy ID"):
            mock_strategy.update_config(new_config)
    
    def test_update_config_invalid_type(self, mock_strategy, risk_limits):
        """Test updating configuration with different strategy type."""
        new_config = StrategyConfig(
            strategy_id="test_momentum",
            strategy_type=StrategyType.MEAN_REVERSION,  # Different type
            name="Test Strategy",
            description="Test description",
            parameters={'lookback_period': 20, 'deviation_threshold': 2.0},
            symbols=["AAPL"],
            risk_limits=risk_limits
        )
        
        with pytest.raises(ValueError, match="Cannot change strategy type"):
            mock_strategy.update_config(new_config)
    
    def test_string_representations(self, mock_strategy):
        """Test string representations of strategy."""
        str_repr = str(mock_strategy)
        assert "test_momentum" in str_repr
        assert "momentum" in str_repr
        assert "active=True" in str_repr
        
        repr_str = repr(mock_strategy)
        assert "test_momentum" in repr_str
        assert "momentum" in repr_str
        assert "AAPL" in repr_str
        assert "GOOGL" in repr_str
    
    def test_generate_signals_integration(self, mock_strategy):
        """Test signal generation integration."""
        market_data = {
            "AAPL": Quote(
                symbol="AAPL",
                timestamp=datetime.now(timezone.utc),
                bid=Decimal('149.50'),
                ask=Decimal('150.50'),
                bid_size=100,
                ask_size=100
            ),
            "GOOGL": Quote(
                symbol="GOOGL",
                timestamp=datetime.now(timezone.utc),
                bid=Decimal('2799.50'),
                ask=Decimal('2800.50'),
                bid_size=50,
                ask_size=50
            )
        }
        
        portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('100000'),
            buying_power=Decimal('50000'),
            day_pnl=Decimal('1000'),
            total_pnl=Decimal('5000')
        )
        
        signals = mock_strategy.generate_signals(market_data, portfolio)
        
        assert len(signals) == 2  # One for each symbol
        assert all(isinstance(signal, StrategySignal) for signal in signals)
        assert all(signal.symbol in ["AAPL", "GOOGL"] for signal in signals)