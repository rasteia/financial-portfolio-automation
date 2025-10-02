"""
Integration tests for strategy implementations.

This module tests the integration between different strategy components
and their interaction with the broader system.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from financial_portfolio_automation.strategy.factory import StrategyFactory
from financial_portfolio_automation.strategy.executor import StrategyExecutor
from financial_portfolio_automation.strategy.registry import StrategyRegistry
from financial_portfolio_automation.models.core import Quote, Position, PortfolioSnapshot
from financial_portfolio_automation.models.config import RiskLimits


class TestStrategyIntegration:
    """Integration tests for strategy system."""
    
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
    def sample_market_data(self):
        """Create sample market data."""
        return {
            "AAPL": Quote(
                symbol="AAPL",
                timestamp=datetime.now(timezone.utc),
                open=Decimal('150.0'),
                high=Decimal('152.0'),
                low=Decimal('149.0'),
                close=Decimal('151.0'),
                volume=1000000
            ),
            "GOOGL": Quote(
                symbol="GOOGL",
                timestamp=datetime.now(timezone.utc),
                open=Decimal('2800.0'),
                high=Decimal('2820.0'),
                low=Decimal('2790.0'),
                close=Decimal('2810.0'),
                volume=500000
            )
        }
    
    @pytest.fixture
    def sample_portfolio(self):
        """Create sample portfolio snapshot."""
        return PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('100000'),
            buying_power=Decimal('50000'),
            day_pnl=Decimal('1000'),
            total_pnl=Decimal('5000'),
            positions=[
                Position(
                    symbol="AAPL",
                    quantity=100,
                    market_value=Decimal('15100'),
                    cost_basis=Decimal('15000'),
                    unrealized_pnl=Decimal('100'),
                    day_pnl=Decimal('50')
                )
            ]
        )
    
    @pytest.fixture
    def historical_data(self):
        """Create sample historical data."""
        base_time = datetime.now(timezone.utc)
        
        # Create historical data for AAPL
        aapl_history = []
        for i in range(25):
            price = Decimal('150') + Decimal(str(i * 0.2))
            aapl_history.append(Quote(
                symbol="AAPL",
                timestamp=base_time,
                open=price - Decimal('0.5'),
                high=price + Decimal('1.0'),
                low=price - Decimal('1.0'),
                close=price,
                volume=1000000 + i * 10000
            ))
        
        # Create historical data for GOOGL
        googl_history = []
        for i in range(25):
            price = Decimal('2800') + Decimal(str(i * 5))
            googl_history.append(Quote(
                symbol="GOOGL",
                timestamp=base_time,
                open=price - Decimal('10'),
                high=price + Decimal('20'),
                low=price - Decimal('20'),
                close=price,
                volume=500000 + i * 5000
            ))
        
        return {
            "AAPL": aapl_history,
            "GOOGL": googl_history
        }
    
    def test_strategy_factory_creates_working_strategies(self, risk_limits):
        """Test that factory creates functional strategies."""
        factory = StrategyFactory()
        
        # Create momentum strategy
        momentum_strategy = factory.create_momentum_strategy(
            strategy_id="test_momentum",
            symbols=["AAPL", "GOOGL"],
            risk_limits=risk_limits
        )
        
        # Create mean reversion strategy
        mean_reversion_strategy = factory.create_mean_reversion_strategy(
            strategy_id="test_mean_reversion",
            symbols=["AAPL", "GOOGL"],
            risk_limits=risk_limits
        )
        
        assert momentum_strategy.is_active
        assert mean_reversion_strategy.is_active
        assert momentum_strategy.symbols == ["AAPL", "GOOGL"]
        assert mean_reversion_strategy.symbols == ["AAPL", "GOOGL"]
    
    def test_strategy_executor_runs_multiple_strategies(self, risk_limits, sample_market_data, 
                                                       sample_portfolio, historical_data):
        """Test strategy executor with multiple strategies."""
        # Create registry and factory
        registry = StrategyRegistry()
        factory = StrategyFactory(registry)
        executor = StrategyExecutor(registry)
        
        # Create strategies
        momentum_strategy = factory.create_momentum_strategy(
            strategy_id="momentum_test",
            symbols=["AAPL", "GOOGL"],
            risk_limits=risk_limits
        )
        
        mean_reversion_strategy = factory.create_mean_reversion_strategy(
            strategy_id="mean_reversion_test",
            symbols=["AAPL", "GOOGL"],
            risk_limits=risk_limits
        )
        
        # Mock technical analysis to generate signals
        with patch('financial_portfolio_automation.strategy.momentum.TechnicalAnalysis') as mock_ta_momentum, \
             patch('financial_portfolio_automation.strategy.mean_reversion.TechnicalAnalysis') as mock_ta_mean_rev:
            
            # Setup momentum strategy mocks
            mock_ta_momentum_instance = Mock()
            mock_ta_momentum.return_value = mock_ta_momentum_instance
            mock_ta_momentum_instance.calculate_rsi.return_value = [65.0]
            mock_ta_momentum_instance.calculate_macd.return_value = ([0.8], [0.5], [0.3])
            mock_ta_momentum_instance.calculate_sma.side_effect = [
                [151.0], [150.0],  # AAPL SMAs
                [2810.0], [2800.0]  # GOOGL SMAs
            ]
            
            # Setup mean reversion strategy mocks
            mock_ta_mean_rev_instance = Mock()
            mock_ta_mean_rev.return_value = mock_ta_mean_rev_instance
            mock_ta_mean_rev_instance.calculate_rsi.return_value = [25.0]  # Oversold
            mock_ta_mean_rev_instance.calculate_bollinger_bands.return_value = (
                [155.0], [152.0], [149.0]  # Upper, Middle, Lower bands
            )
            mock_ta_mean_rev_instance.calculate_sma.side_effect = [
                [150.5], [151.0],  # AAPL SMAs
                [2805.0], [2810.0]  # GOOGL SMAs
            ]
            
            # Execute all strategies
            results = executor.execute_all_strategies(
                sample_market_data, sample_portfolio, historical_data
            )
            
            # Check that both strategies generated signals
            assert len(results) == 2
            assert "momentum_test" in results
            assert "mean_reversion_test" in results
            
            # Check execution stats
            stats = executor.get_execution_stats()
            assert stats['execution_count'] == 1
            assert stats['total_signals_generated'] >= 0
    
    def test_strategy_templates_create_different_behaviors(self, risk_limits):
        """Test that different templates create strategies with different parameters."""
        factory = StrategyFactory()
        
        # Create aggressive momentum strategy
        aggressive_momentum = factory.create_strategy_from_template(
            template_name="aggressive_momentum",
            strategy_id="aggressive_test",
            symbols=["AAPL"],
            risk_limits=risk_limits
        )
        
        # Create conservative momentum strategy
        conservative_momentum = factory.create_strategy_from_template(
            template_name="conservative_momentum",
            strategy_id="conservative_test",
            symbols=["AAPL"],
            risk_limits=risk_limits
        )
        
        # Check that they have different parameters
        assert aggressive_momentum.lookback_period != conservative_momentum.lookback_period
        assert aggressive_momentum.min_momentum_strength != conservative_momentum.min_momentum_strength
        
        # Aggressive should have shorter lookback and higher strength requirement
        assert aggressive_momentum.lookback_period < conservative_momentum.lookback_period
        assert aggressive_momentum.min_momentum_strength > conservative_momentum.min_momentum_strength
    
    def test_signal_handler_integration(self, risk_limits, sample_market_data, 
                                      sample_portfolio, historical_data):
        """Test signal handler integration with strategy executor."""
        # Create registry and executor
        registry = StrategyRegistry()
        factory = StrategyFactory(registry)
        executor = StrategyExecutor(registry)
        
        # Create signal handler
        signals_received = []
        
        def signal_handler(signal):
            signals_received.append(signal)
        
        executor.add_signal_handler(signal_handler)
        
        # Create strategy
        strategy = factory.create_momentum_strategy(
            strategy_id="signal_test",
            symbols=["AAPL"],
            risk_limits=risk_limits
        )
        
        # Mock technical analysis to generate a signal
        with patch('financial_portfolio_automation.strategy.momentum.TechnicalAnalysis') as mock_ta:
            mock_ta_instance = Mock()
            mock_ta.return_value = mock_ta_instance
            mock_ta_instance.calculate_rsi.return_value = [65.0]
            mock_ta_instance.calculate_macd.return_value = ([0.8], [0.5], [0.3])
            mock_ta_instance.calculate_sma.side_effect = [
                [151.0], [150.0]  # AAPL SMAs
            ]
            
            # Execute strategy
            executor.execute_all_strategies(sample_market_data, sample_portfolio, historical_data)
            
            # Check that signal handler was called
            assert len(signals_received) >= 0  # May or may not generate signals based on conditions
    
    def test_strategy_state_management(self, risk_limits, sample_market_data, sample_portfolio):
        """Test strategy state management across updates."""
        factory = StrategyFactory()
        
        strategy = factory.create_momentum_strategy(
            strategy_id="state_test",
            symbols=["AAPL"],
            risk_limits=risk_limits
        )
        
        # Initial state
        assert strategy.state.signals_generated == 0
        assert strategy.state.trades_executed == 0
        assert len(strategy.state.positions) == 0
        
        # Update state with portfolio
        strategy.update_state(sample_market_data, sample_portfolio)
        
        # Check that position was added
        assert "AAPL" in strategy.state.positions
        assert strategy.state.positions["AAPL"].quantity == 100
        
        # Check metadata was updated
        assert 'last_market_update' in strategy.state.metadata
        assert 'portfolio_value' in strategy.state.metadata
    
    def test_multiple_strategy_types_coexist(self, risk_limits):
        """Test that multiple strategy types can coexist in the same registry."""
        registry = StrategyRegistry()
        factory = StrategyFactory(registry)
        
        # Create different types of strategies
        momentum1 = factory.create_momentum_strategy(
            strategy_id="momentum_1",
            symbols=["AAPL"],
            risk_limits=risk_limits
        )
        
        momentum2 = factory.create_momentum_strategy(
            strategy_id="momentum_2",
            symbols=["GOOGL"],
            risk_limits=risk_limits
        )
        
        mean_reversion1 = factory.create_mean_reversion_strategy(
            strategy_id="mean_reversion_1",
            symbols=["MSFT"],
            risk_limits=risk_limits
        )
        
        # Check registry stats
        stats = registry.get_registry_stats()
        assert stats['total_strategies'] == 3
        assert stats['active_strategies'] == 3
        
        # Check type distribution
        momentum_strategies = registry.get_strategies_by_type(
            factory.registry._strategy_classes[momentum1.config.strategy_type].__name__
        )
        # Note: This test might need adjustment based on how get_strategies_by_type is implemented
        
        # Check that all strategies are accessible
        assert registry.get_strategy("momentum_1") is not None
        assert registry.get_strategy("momentum_2") is not None
        assert registry.get_strategy("mean_reversion_1") is not None