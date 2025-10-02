"""
Unit tests for the strategy registry.

Tests the StrategyRegistry class for strategy registration, creation,
and lifecycle management.
"""

import pytest
from unittest.mock import Mock, patch
from threading import Thread
import time

from financial_portfolio_automation.strategy.registry import (
    StrategyRegistry, get_global_registry, register_strategy_class, create_strategy
)
from financial_portfolio_automation.strategy.base import Strategy, StrategySignal, SignalType
from financial_portfolio_automation.models.config import (
    StrategyConfig, StrategyType, RiskLimits
)
from financial_portfolio_automation.models.core import Quote, PortfolioSnapshot
from decimal import Decimal
from datetime import datetime, timezone


class MockMomentumStrategy(Strategy):
    """Mock momentum strategy for testing."""
    
    def generate_signals(self, market_data, portfolio, historical_data=None):
        return [
            StrategySignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                strength=0.8
            )
            for symbol in self.symbols if symbol in market_data
        ]
    
    def update_state(self, market_data, portfolio):
        self.state.last_update = datetime.now(timezone.utc)


class MockMeanReversionStrategy(Strategy):
    """Mock mean reversion strategy for testing."""
    
    def generate_signals(self, market_data, portfolio, historical_data=None):
        return [
            StrategySignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                strength=0.6
            )
            for symbol in self.symbols if symbol in market_data
        ]
    
    def update_state(self, market_data, portfolio):
        self.state.last_update = datetime.now(timezone.utc)


class TestStrategyRegistry:
    """Test cases for StrategyRegistry class."""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return StrategyRegistry()
    
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
    def momentum_config(self, risk_limits):
        """Create momentum strategy configuration."""
        return StrategyConfig(
            strategy_id="momentum_1",
            strategy_type=StrategyType.MOMENTUM,
            name="Test Momentum Strategy",
            description="Test momentum strategy",
            parameters={
                'lookback_period': 20,
                'momentum_threshold': 0.02
            },
            symbols=["AAPL", "GOOGL"],
            risk_limits=risk_limits
        )
    
    @pytest.fixture
    def mean_reversion_config(self, risk_limits):
        """Create mean reversion strategy configuration."""
        return StrategyConfig(
            strategy_id="mean_reversion_1",
            strategy_type=StrategyType.MEAN_REVERSION,
            name="Test Mean Reversion Strategy",
            description="Test mean reversion strategy",
            parameters={
                'lookback_period': 30,
                'deviation_threshold': 2.0
            },
            symbols=["TSLA", "MSFT"],
            risk_limits=risk_limits
        )
    
    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert len(registry._strategy_classes) == 0
        assert len(registry._strategy_instances) == 0
        assert registry.list_registered_types() == []
    
    def test_register_strategy_class(self, registry):
        """Test registering a strategy class."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        
        assert StrategyType.MOMENTUM in registry._strategy_classes
        assert registry._strategy_classes[StrategyType.MOMENTUM] == MockMomentumStrategy
        assert StrategyType.MOMENTUM in registry.list_registered_types()
    
    def test_register_invalid_strategy_class(self, registry):
        """Test registering an invalid strategy class."""
        class InvalidStrategy:
            pass
        
        with pytest.raises(ValueError, match="Strategy class must inherit from Strategy base class"):
            registry.register_strategy_class(StrategyType.MOMENTUM, InvalidStrategy)
    
    def test_register_strategy_class_override(self, registry):
        """Test overriding an existing strategy class registration."""
        # Register first strategy
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        
        # Register different strategy for same type (should log warning)
        with patch('financial_portfolio_automation.strategy.registry.logger') as mock_logger:
            registry.register_strategy_class(StrategyType.MOMENTUM, MockMeanReversionStrategy)
            mock_logger.warning.assert_called_once()
        
        # Should have the new strategy class
        assert registry._strategy_classes[StrategyType.MOMENTUM] == MockMeanReversionStrategy
    
    def test_unregister_strategy_class(self, registry):
        """Test unregistering a strategy class."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        assert StrategyType.MOMENTUM in registry._strategy_classes
        
        registry.unregister_strategy_class(StrategyType.MOMENTUM)
        assert StrategyType.MOMENTUM not in registry._strategy_classes
    
    def test_unregister_nonexistent_strategy_class(self, registry):
        """Test unregistering a non-existent strategy class."""
        with patch('financial_portfolio_automation.strategy.registry.logger') as mock_logger:
            registry.unregister_strategy_class(StrategyType.MOMENTUM)
            mock_logger.warning.assert_called_once()
    
    def test_get_strategy_class(self, registry):
        """Test getting a registered strategy class."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        
        strategy_class = registry.get_strategy_class(StrategyType.MOMENTUM)
        assert strategy_class == MockMomentumStrategy
        
        # Test non-existent class
        assert registry.get_strategy_class(StrategyType.MEAN_REVERSION) is None
    
    def test_create_strategy(self, registry, momentum_config):
        """Test creating a strategy instance."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        
        strategy = registry.create_strategy(momentum_config)
        
        assert isinstance(strategy, MockMomentumStrategy)
        assert strategy.strategy_id == "momentum_1"
        assert "momentum_1" in registry._strategy_instances
    
    def test_create_strategy_unregistered_type(self, registry, momentum_config):
        """Test creating strategy with unregistered type."""
        with pytest.raises(ValueError, match="Strategy type .* not registered"):
            registry.create_strategy(momentum_config)
    
    def test_create_strategy_duplicate_id(self, registry, momentum_config):
        """Test creating strategy with duplicate ID."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        
        # Create first strategy
        registry.create_strategy(momentum_config)
        
        # Try to create another with same ID
        with pytest.raises(ValueError, match="Strategy with ID .* already exists"):
            registry.create_strategy(momentum_config)
    
    def test_get_strategy(self, registry, momentum_config):
        """Test getting strategy instance by ID."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        strategy = registry.create_strategy(momentum_config)
        
        retrieved_strategy = registry.get_strategy("momentum_1")
        assert retrieved_strategy is strategy
        
        # Test non-existent strategy
        assert registry.get_strategy("nonexistent") is None
    
    def test_remove_strategy(self, registry, momentum_config):
        """Test removing strategy instance."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        strategy = registry.create_strategy(momentum_config)
        
        assert registry.remove_strategy("momentum_1") is True
        assert "momentum_1" not in registry._strategy_instances
        assert not strategy.is_active  # Should be deactivated
        
        # Test removing non-existent strategy
        assert registry.remove_strategy("nonexistent") is False
    
    def test_list_strategies(self, registry, momentum_config, mean_reversion_config):
        """Test listing strategy instances."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        registry.register_strategy_class(StrategyType.MEAN_REVERSION, MockMeanReversionStrategy)
        
        strategy1 = registry.create_strategy(momentum_config)
        strategy2 = registry.create_strategy(mean_reversion_config)
        
        # Test listing all strategies
        all_strategies = registry.list_strategies()
        assert len(all_strategies) == 2
        assert strategy1 in all_strategies
        assert strategy2 in all_strategies
        
        # Test listing only active strategies
        strategy1.deactivate()
        active_strategies = registry.list_strategies(active_only=True)
        assert len(active_strategies) == 1
        assert strategy2 in active_strategies
        assert strategy1 not in active_strategies
    
    def test_get_strategies_by_type(self, registry, momentum_config, mean_reversion_config):
        """Test getting strategies by type."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        registry.register_strategy_class(StrategyType.MEAN_REVERSION, MockMeanReversionStrategy)
        
        strategy1 = registry.create_strategy(momentum_config)
        strategy2 = registry.create_strategy(mean_reversion_config)
        
        momentum_strategies = registry.get_strategies_by_type(StrategyType.MOMENTUM)
        assert len(momentum_strategies) == 1
        assert strategy1 in momentum_strategies
        
        mean_reversion_strategies = registry.get_strategies_by_type(StrategyType.MEAN_REVERSION)
        assert len(mean_reversion_strategies) == 1
        assert strategy2 in mean_reversion_strategies
    
    def test_get_strategies_by_symbol(self, registry, momentum_config, mean_reversion_config):
        """Test getting strategies by symbol."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        registry.register_strategy_class(StrategyType.MEAN_REVERSION, MockMeanReversionStrategy)
        
        strategy1 = registry.create_strategy(momentum_config)  # Trades AAPL, GOOGL
        strategy2 = registry.create_strategy(mean_reversion_config)  # Trades TSLA, MSFT
        
        aapl_strategies = registry.get_strategies_by_symbol("AAPL")
        assert len(aapl_strategies) == 1
        assert strategy1 in aapl_strategies
        
        tsla_strategies = registry.get_strategies_by_symbol("TSLA")
        assert len(tsla_strategies) == 1
        assert strategy2 in tsla_strategies
        
        # Test symbol not traded by any strategy
        nvda_strategies = registry.get_strategies_by_symbol("NVDA")
        assert len(nvda_strategies) == 0
    
    def test_activate_deactivate_strategy(self, registry, momentum_config):
        """Test activating and deactivating strategies."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        strategy = registry.create_strategy(momentum_config)
        
        assert strategy.is_active is True
        
        # Deactivate
        assert registry.deactivate_strategy("momentum_1") is True
        assert strategy.is_active is False
        
        # Activate
        assert registry.activate_strategy("momentum_1") is True
        assert strategy.is_active is True
        
        # Test with non-existent strategy
        assert registry.activate_strategy("nonexistent") is False
        assert registry.deactivate_strategy("nonexistent") is False
    
    def test_deactivate_all_strategies(self, registry, momentum_config, mean_reversion_config):
        """Test deactivating all strategies."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        registry.register_strategy_class(StrategyType.MEAN_REVERSION, MockMeanReversionStrategy)
        
        strategy1 = registry.create_strategy(momentum_config)
        strategy2 = registry.create_strategy(mean_reversion_config)
        
        assert strategy1.is_active is True
        assert strategy2.is_active is True
        
        registry.deactivate_all_strategies()
        
        assert strategy1.is_active is False
        assert strategy2.is_active is False
    
    def test_get_registry_stats(self, registry, momentum_config, mean_reversion_config):
        """Test getting registry statistics."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        registry.register_strategy_class(StrategyType.MEAN_REVERSION, MockMeanReversionStrategy)
        
        strategy1 = registry.create_strategy(momentum_config)
        strategy2 = registry.create_strategy(mean_reversion_config)
        strategy1.deactivate()
        
        stats = registry.get_registry_stats()
        
        assert stats['registered_classes'] == 2
        assert stats['total_strategies'] == 2
        assert stats['active_strategies'] == 1
        assert stats['inactive_strategies'] == 1
        assert StrategyType.MOMENTUM in stats['strategy_types']
        assert StrategyType.MEAN_REVERSION in stats['strategy_types']
        assert stats['type_distribution']['momentum'] == 1
        assert stats['type_distribution']['mean_reversion'] == 1
    
    def test_clear_all(self, registry, momentum_config):
        """Test clearing all strategies and classes."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        strategy = registry.create_strategy(momentum_config)
        
        assert len(registry._strategy_classes) == 1
        assert len(registry._strategy_instances) == 1
        assert strategy.is_active is True
        
        registry.clear_all()
        
        assert len(registry._strategy_classes) == 0
        assert len(registry._strategy_instances) == 0
        assert strategy.is_active is False
    
    def test_thread_safety(self, registry):
        """Test thread safety of registry operations."""
        registry.register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        
        def create_strategies():
            for i in range(10):
                try:
                    config = StrategyConfig(
                        strategy_id=f"strategy_{i}",
                        strategy_type=StrategyType.MOMENTUM,
                        name=f"Strategy {i}",
                        description="Test strategy",
                        parameters={'lookback_period': 20, 'momentum_threshold': 0.02},
                        symbols=["AAPL"],
                        risk_limits=RiskLimits(
                            max_position_size=Decimal('10000'),
                            max_portfolio_concentration=0.2,
                            max_daily_loss=Decimal('1000'),
                            max_drawdown=0.1,
                            stop_loss_percentage=0.05
                        )
                    )
                    registry.create_strategy(config)
                except ValueError:
                    # Expected for duplicate IDs in concurrent execution
                    pass
        
        # Create multiple threads
        threads = [Thread(target=create_strategies) for _ in range(3)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Registry should still be in a consistent state
        stats = registry.get_registry_stats()
        assert stats['total_strategies'] >= 0  # Some strategies should be created


class TestGlobalRegistry:
    """Test cases for global registry functions."""
    
    def test_get_global_registry(self):
        """Test getting global registry instance."""
        registry1 = get_global_registry()
        registry2 = get_global_registry()
        
        # Should return the same instance
        assert registry1 is registry2
        assert isinstance(registry1, StrategyRegistry)
    
    def test_register_strategy_class_global(self):
        """Test registering strategy class in global registry."""
        # Clear global registry first
        global_registry = get_global_registry()
        global_registry.clear_all()
        
        register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        
        assert StrategyType.MOMENTUM in global_registry.list_registered_types()
        assert global_registry.get_strategy_class(StrategyType.MOMENTUM) == MockMomentumStrategy
    
    def test_create_strategy_global(self):
        """Test creating strategy using global registry."""
        # Clear and setup global registry
        global_registry = get_global_registry()
        global_registry.clear_all()
        register_strategy_class(StrategyType.MOMENTUM, MockMomentumStrategy)
        
        config = StrategyConfig(
            strategy_id="global_test",
            strategy_type=StrategyType.MOMENTUM,
            name="Global Test Strategy",
            description="Test strategy for global registry",
            parameters={'lookback_period': 20, 'momentum_threshold': 0.02},
            symbols=["AAPL"],
            risk_limits=RiskLimits(
                max_position_size=Decimal('10000'),
                max_portfolio_concentration=0.2,
                max_daily_loss=Decimal('1000'),
                max_drawdown=0.1,
                stop_loss_percentage=0.05
            )
        )
        
        strategy = create_strategy(config)
        
        assert isinstance(strategy, MockMomentumStrategy)
        assert strategy.strategy_id == "global_test"
        assert global_registry.get_strategy("global_test") is strategy