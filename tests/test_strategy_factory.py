"""
Unit tests for strategy factory implementation.
"""

import pytest
from decimal import Decimal

from financial_portfolio_automation.strategy.factory import StrategyFactory, get_global_factory
from financial_portfolio_automation.strategy.momentum import MomentumStrategy
from financial_portfolio_automation.strategy.mean_reversion import MeanReversionStrategy
from financial_portfolio_automation.strategy.registry import StrategyRegistry
from financial_portfolio_automation.models.config import StrategyConfig, StrategyType, RiskLimits


class TestStrategyFactory:
    """Test cases for StrategyFactory class."""
    
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
    def strategy_factory(self):
        """Create strategy factory with clean registry."""
        registry = StrategyRegistry()
        return StrategyFactory(registry)
    
    def test_factory_initialization(self, strategy_factory):
        """Test strategy factory initialization."""
        assert strategy_factory.registry is not None
        
        # Check that built-in strategies are registered
        available_types = strategy_factory.get_available_strategy_types()
        assert StrategyType.MOMENTUM in available_types
        assert StrategyType.MEAN_REVERSION in available_types
    
    def test_create_momentum_strategy(self, strategy_factory, risk_limits):
        """Test momentum strategy creation."""
        strategy = strategy_factory.create_momentum_strategy(
            strategy_id="test_momentum",
            symbols=["AAPL", "GOOGL"],
            risk_limits=risk_limits
        )
        
        assert isinstance(strategy, MomentumStrategy)
        assert strategy.strategy_id == "test_momentum"
        assert strategy.symbols == ["AAPL", "GOOGL"]
        assert strategy.lookback_period == 20  # Default value
        assert strategy.min_momentum_strength == 0.6  # Default value
    
    def test_create_momentum_strategy_with_custom_parameters(self, strategy_factory, risk_limits):
        """Test momentum strategy creation with custom parameters."""
        custom_params = {
            'lookback_period': 30,
            'min_momentum_strength': 0.7,
            'price_change_threshold': 0.03
        }
        
        strategy = strategy_factory.create_momentum_strategy(
            strategy_id="custom_momentum",
            symbols=["MSFT"],
            parameters=custom_params,
            risk_limits=risk_limits
        )
        
        assert strategy.lookback_period == 30
        assert strategy.min_momentum_strength == 0.7
        assert strategy.price_change_threshold == 0.03
    
    def test_create_mean_reversion_strategy(self, strategy_factory, risk_limits):
        """Test mean reversion strategy creation."""
        strategy = strategy_factory.create_mean_reversion_strategy(
            strategy_id="test_mean_reversion",
            symbols=["TSLA", "NVDA"],
            risk_limits=risk_limits
        )
        
        assert isinstance(strategy, MeanReversionStrategy)
        assert strategy.strategy_id == "test_mean_reversion"
        assert strategy.symbols == ["TSLA", "NVDA"]
        assert strategy.lookback_period == 20  # Default value
        assert strategy.std_dev_threshold == 2.0  # Default value
    
    def test_create_mean_reversion_strategy_with_custom_parameters(self, strategy_factory, risk_limits):
        """Test mean reversion strategy creation with custom parameters."""
        custom_params = {
            'std_dev_threshold': 1.5,
            'mean_reversion_threshold': 0.08,
            'volume_confirmation': False
        }
        
        strategy = strategy_factory.create_mean_reversion_strategy(
            strategy_id="custom_mean_reversion",
            symbols=["AMD"],
            parameters=custom_params,
            risk_limits=risk_limits
        )
        
        assert strategy.std_dev_threshold == 1.5
        assert strategy.mean_reversion_threshold == 0.08
        assert strategy.volume_confirmation == False
    
    def test_create_strategy_from_config(self, strategy_factory, risk_limits):
        """Test strategy creation from configuration."""
        config = StrategyConfig(
            strategy_id="config_test",
            strategy_type=StrategyType.MOMENTUM,
            name="Config Test Strategy",
            description="Test strategy created from config",
            symbols=["AAPL"],
            parameters={'lookback_period': 25},
            risk_limits=risk_limits,
            is_active=True
        )
        
        strategy = strategy_factory.create_strategy(config)
        
        assert isinstance(strategy, MomentumStrategy)
        assert strategy.strategy_id == "config_test"
        assert strategy.lookback_period == 25
    
    def test_create_strategy_from_template_aggressive_momentum(self, strategy_factory, risk_limits):
        """Test strategy creation from aggressive momentum template."""
        strategy = strategy_factory.create_strategy_from_template(
            template_name="aggressive_momentum",
            strategy_id="aggressive_test",
            symbols=["AAPL"],
            risk_limits=risk_limits
        )
        
        assert isinstance(strategy, MomentumStrategy)
        assert strategy.lookback_period == 15
        assert strategy.min_momentum_strength == 0.7
        assert strategy.price_change_threshold == 0.03
    
    def test_create_strategy_from_template_conservative_mean_reversion(self, strategy_factory, risk_limits):
        """Test strategy creation from conservative mean reversion template."""
        strategy = strategy_factory.create_strategy_from_template(
            template_name="conservative_mean_reversion",
            strategy_id="conservative_test",
            symbols=["MSFT"],
            risk_limits=risk_limits
        )
        
        assert isinstance(strategy, MeanReversionStrategy)
        assert strategy.std_dev_threshold == 2.5
        assert strategy.mean_reversion_threshold == 0.08
        assert strategy.trend_filter == True
    
    def test_create_strategy_from_invalid_template(self, strategy_factory, risk_limits):
        """Test strategy creation from invalid template."""
        with pytest.raises(ValueError, match="Template invalid_template not found"):
            strategy_factory.create_strategy_from_template(
                template_name="invalid_template",
                strategy_id="test",
                symbols=["AAPL"],
                risk_limits=risk_limits
            )
    
    def test_get_available_strategy_types(self, strategy_factory):
        """Test getting available strategy types."""
        types = strategy_factory.get_available_strategy_types()
        
        assert StrategyType.MOMENTUM in types
        assert StrategyType.MEAN_REVERSION in types
        assert len(types) >= 2
    
    def test_get_available_templates(self, strategy_factory):
        """Test getting available templates."""
        templates = strategy_factory.get_available_templates()
        
        expected_templates = [
            'aggressive_momentum',
            'conservative_momentum',
            'aggressive_mean_reversion',
            'conservative_mean_reversion'
        ]
        
        for template in expected_templates:
            assert template in templates
    
    def test_get_strategy_class(self, strategy_factory):
        """Test getting strategy class by type."""
        momentum_class = strategy_factory.get_strategy_class(StrategyType.MOMENTUM)
        mean_reversion_class = strategy_factory.get_strategy_class(StrategyType.MEAN_REVERSION)
        
        assert momentum_class == MomentumStrategy
        assert mean_reversion_class == MeanReversionStrategy
    
    def test_get_strategy_class_invalid_type(self, strategy_factory):
        """Test getting strategy class for invalid type."""
        # Create a custom strategy type that's not registered
        from enum import Enum
        
        class CustomStrategyType(Enum):
            CUSTOM = "custom"
        
        with pytest.raises(ValueError, match="Strategy type"):
            strategy_factory.get_strategy_class(CustomStrategyType.CUSTOM)
    
    def test_get_factory_info(self, strategy_factory):
        """Test getting factory information."""
        info = strategy_factory.get_factory_info()
        
        assert 'available_types' in info
        assert 'available_templates' in info
        assert 'registered_strategies' in info
        assert 'registry_stats' in info
        
        assert len(info['available_types']) >= 2
        assert len(info['available_templates']) == 4
        assert info['registered_strategies'] >= 2
    
    def test_global_factory(self):
        """Test global factory instance."""
        factory = get_global_factory()
        
        assert isinstance(factory, StrategyFactory)
        assert factory.registry is not None
        
        # Test that it's a singleton
        factory2 = get_global_factory()
        assert factory is factory2
    
    def test_duplicate_strategy_id_error(self, strategy_factory, risk_limits):
        """Test error when creating strategies with duplicate IDs."""
        # Create first strategy
        strategy_factory.create_momentum_strategy(
            strategy_id="duplicate_test",
            symbols=["AAPL"],
            risk_limits=risk_limits
        )
        
        # Try to create second strategy with same ID
        with pytest.raises(ValueError, match="Strategy with ID duplicate_test already exists"):
            strategy_factory.create_momentum_strategy(
                strategy_id="duplicate_test",
                symbols=["GOOGL"],
                risk_limits=risk_limits
            )
    
    def test_all_templates_create_valid_strategies(self, strategy_factory, risk_limits):
        """Test that all templates create valid strategies."""
        templates = strategy_factory.get_available_templates()
        
        for i, template in enumerate(templates):
            strategy = strategy_factory.create_strategy_from_template(
                template_name=template,
                strategy_id=f"template_test_{i}",
                symbols=["AAPL"],
                risk_limits=risk_limits
            )
            
            assert strategy is not None
            assert strategy.strategy_id == f"template_test_{i}"
            assert strategy.symbols == ["AAPL"]
            assert strategy.is_active
    
    def test_factory_with_custom_registry(self):
        """Test factory with custom registry."""
        custom_registry = StrategyRegistry()
        factory = StrategyFactory(custom_registry)
        
        assert factory.registry is custom_registry
        
        # Should still have built-in strategies registered
        types = factory.get_available_strategy_types()
        assert StrategyType.MOMENTUM in types
        assert StrategyType.MEAN_REVERSION in types