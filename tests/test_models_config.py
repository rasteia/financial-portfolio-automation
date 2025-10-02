"""
Unit tests for configuration data models.

Tests validation logic, business rules, and environment loading for configuration models.
"""

import pytest
import os
from decimal import Decimal
from unittest.mock import patch

from financial_portfolio_automation.models.config import (
    AlpacaConfig,
    RiskLimits,
    StrategyConfig,
    SystemConfig,
    Environment,
    DataFeed,
    StrategyType,
)


class TestAlpacaConfig:
    """Test cases for AlpacaConfig data model."""
    
    def test_valid_paper_config(self):
        """Test creating a valid paper trading configuration."""
        config = AlpacaConfig(
            api_key="PKTEST1234567890ABCDEF",
            secret_key="abcdef1234567890abcdef1234567890abcdef12",
            base_url="https://paper-api.alpaca.markets",
            data_feed=DataFeed.IEX,
            environment=Environment.PAPER
        )
        
        assert config.api_key == "PKTEST1234567890ABCDEF"
        assert config.environment == Environment.PAPER
        assert config.is_paper_trading()
    
    def test_valid_live_config(self):
        """Test creating a valid live trading configuration."""
        config = AlpacaConfig(
            api_key="AKLIVE1234567890ABCDEF",
            secret_key="abcdef1234567890abcdef1234567890abcdef12",
            base_url="https://api.alpaca.markets",
            data_feed=DataFeed.SIP,
            environment=Environment.LIVE
        )
        
        assert config.environment == Environment.LIVE
        assert not config.is_paper_trading()
    
    def test_short_api_key(self):
        """Test validation of short API key."""
        with pytest.raises(ValueError, match="API key appears to be too short"):
            AlpacaConfig(
                api_key="SHORT",
                secret_key="abcdef1234567890abcdef1234567890abcdef12",
                base_url="https://paper-api.alpaca.markets"
            )
    
    def test_short_secret_key(self):
        """Test validation of short secret key."""
        with pytest.raises(ValueError, match="Secret key appears to be too short"):
            AlpacaConfig(
                api_key="PKTEST1234567890ABCDEF",
                secret_key="short",
                base_url="https://paper-api.alpaca.markets"
            )
    
    def test_invalid_base_url(self):
        """Test validation of invalid base URL."""
        with pytest.raises(ValueError, match="Base URL must start with http:// or https://"):
            AlpacaConfig(
                api_key="PKTEST1234567890ABCDEF",
                secret_key="abcdef1234567890abcdef1234567890abcdef12",
                base_url="invalid-url"
            )
    
    def test_paper_environment_with_live_url(self):
        """Test validation of paper environment with live URL."""
        with pytest.raises(ValueError, match="Paper trading environment requires paper trading URL"):
            AlpacaConfig(
                api_key="PKTEST1234567890ABCDEF",
                secret_key="abcdef1234567890abcdef1234567890abcdef12",
                base_url="https://api.alpaca.markets",
                environment=Environment.PAPER
            )
    
    def test_live_environment_with_paper_url(self):
        """Test validation of live environment with paper URL."""
        with pytest.raises(ValueError, match="Live trading environment cannot use paper trading URL"):
            AlpacaConfig(
                api_key="AKLIVE1234567890ABCDEF",
                secret_key="abcdef1234567890abcdef1234567890abcdef12",
                base_url="https://paper-api.alpaca.markets",
                environment=Environment.LIVE
            )
    
    @patch.dict(os.environ, {
        'ALPACA_API_KEY': 'PKTEST1234567890ABCDEF',
        'ALPACA_SECRET_KEY': 'abcdef1234567890abcdef1234567890abcdef12',
        'ALPACA_BASE_URL': 'https://paper-api.alpaca.markets',
        'ALPACA_DATA_FEED': 'iex',
        'ALPACA_ENVIRONMENT': 'paper'
    })
    def test_from_env_valid(self):
        """Test creating config from environment variables."""
        config = AlpacaConfig.from_env()
        
        assert config.api_key == "PKTEST1234567890ABCDEF"
        assert config.environment == Environment.PAPER
        assert config.data_feed == DataFeed.IEX
    
    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_missing_api_key(self):
        """Test error when API key is missing from environment."""
        with pytest.raises(ValueError, match="ALPACA_API_KEY environment variable is required"):
            AlpacaConfig.from_env()


class TestRiskLimits:
    """Test cases for RiskLimits data model."""
    
    def test_valid_risk_limits(self):
        """Test creating valid risk limits."""
        limits = RiskLimits(
            max_position_size=Decimal('10000'),
            max_portfolio_concentration=0.2,
            max_daily_loss=Decimal('1000'),
            max_drawdown=0.1,
            stop_loss_percentage=0.05
        )
        
        assert limits.max_position_size == Decimal('10000')
        assert limits.max_portfolio_concentration == 0.2
        assert limits.stop_loss_percentage == 0.05
    
    def test_calculate_max_position_value(self):
        """Test calculation of maximum position value."""
        limits = RiskLimits(
            max_position_size=Decimal('10000'),
            max_portfolio_concentration=0.2,
            max_daily_loss=Decimal('1000'),
            max_drawdown=0.1,
            stop_loss_percentage=0.05
        )
        
        portfolio_value = Decimal('50000')
        max_position = limits.calculate_max_position_value(portfolio_value)
        assert max_position == Decimal('10000')  # 50000 * 0.2
    
    def test_calculate_stop_loss_price_long(self):
        """Test stop loss calculation for long position."""
        limits = RiskLimits(
            max_position_size=Decimal('10000'),
            max_portfolio_concentration=0.2,
            max_daily_loss=Decimal('1000'),
            max_drawdown=0.1,
            stop_loss_percentage=0.05
        )
        
        entry_price = Decimal('100')
        stop_loss = limits.calculate_stop_loss_price(entry_price, is_long=True)
        assert stop_loss == Decimal('95')  # 100 * (1 - 0.05)
    
    def test_calculate_stop_loss_price_short(self):
        """Test stop loss calculation for short position."""
        limits = RiskLimits(
            max_position_size=Decimal('10000'),
            max_portfolio_concentration=0.2,
            max_daily_loss=Decimal('1000'),
            max_drawdown=0.1,
            stop_loss_percentage=0.05
        )
        
        entry_price = Decimal('100')
        stop_loss = limits.calculate_stop_loss_price(entry_price, is_long=False)
        assert stop_loss == Decimal('105')  # 100 * (1 + 0.05)
    
    def test_position_size_validation(self):
        """Test position size validation."""
        limits = RiskLimits(
            max_position_size=Decimal('10000'),
            max_portfolio_concentration=0.2,
            max_daily_loss=Decimal('1000'),
            max_drawdown=0.1,
            stop_loss_percentage=0.05,
            min_position_value=Decimal('100')
        )
        
        portfolio_value = Decimal('50000')
        
        # Valid position
        assert limits.is_position_size_valid(Decimal('5000'), portfolio_value)
        
        # Too large (exceeds max position size)
        assert not limits.is_position_size_valid(Decimal('15000'), portfolio_value)
        
        # Too small (below minimum)
        assert not limits.is_position_size_valid(Decimal('50'), portfolio_value)
        
        # Exceeds concentration limit (20% of 50000 = 10000)
        assert not limits.is_position_size_valid(Decimal('12000'), portfolio_value)
    
    def test_negative_max_position_size(self):
        """Test validation of negative maximum position size."""
        with pytest.raises(ValueError, match="Maximum position size must be positive"):
            RiskLimits(
                max_position_size=Decimal('-1000'),
                max_portfolio_concentration=0.2,
                max_daily_loss=Decimal('1000'),
                max_drawdown=0.1,
                stop_loss_percentage=0.05
            )
    
    def test_invalid_portfolio_concentration(self):
        """Test validation of invalid portfolio concentration."""
        with pytest.raises(ValueError, match="Portfolio concentration must be between 0 and 1"):
            RiskLimits(
                max_position_size=Decimal('10000'),
                max_portfolio_concentration=1.5,
                max_daily_loss=Decimal('1000'),
                max_drawdown=0.1,
                stop_loss_percentage=0.05
            )
    
    def test_invalid_leverage(self):
        """Test validation of invalid leverage."""
        with pytest.raises(ValueError, match="Maximum leverage must be between 0 and 4"):
            RiskLimits(
                max_position_size=Decimal('10000'),
                max_portfolio_concentration=0.2,
                max_daily_loss=Decimal('1000'),
                max_drawdown=0.1,
                stop_loss_percentage=0.05,
                max_leverage=5.0
            )


class TestStrategyConfig:
    """Test cases for StrategyConfig data model."""
    
    def test_valid_momentum_strategy(self):
        """Test creating a valid momentum strategy configuration."""
        risk_limits = RiskLimits(
            max_position_size=Decimal('5000'),
            max_portfolio_concentration=0.1,
            max_daily_loss=Decimal('500'),
            max_drawdown=0.05,
            stop_loss_percentage=0.03
        )
        
        config = StrategyConfig(
            strategy_id="momentum_001",
            strategy_type=StrategyType.MOMENTUM,
            name="Basic Momentum Strategy",
            description="Simple momentum-based trading strategy",
            parameters={
                'lookback_period': 20,
                'momentum_threshold': 0.02
            },
            symbols=["AAPL", "TSLA"],
            risk_limits=risk_limits
        )
        
        assert config.strategy_id == "momentum_001"
        assert config.strategy_type == StrategyType.MOMENTUM
        assert len(config.symbols) == 2
    
    def test_valid_pairs_trading_strategy(self):
        """Test creating a valid pairs trading strategy configuration."""
        risk_limits = RiskLimits(
            max_position_size=Decimal('5000'),
            max_portfolio_concentration=0.1,
            max_daily_loss=Decimal('500'),
            max_drawdown=0.05,
            stop_loss_percentage=0.03
        )
        
        config = StrategyConfig(
            strategy_id="pairs_001",
            strategy_type=StrategyType.PAIRS_TRADING,
            name="AAPL-MSFT Pairs",
            description="Pairs trading between AAPL and MSFT",
            parameters={
                'correlation_threshold': 0.8,
                'spread_threshold': 2.0
            },
            symbols=["AAPL", "MSFT"],
            risk_limits=risk_limits
        )
        
        assert config.strategy_type == StrategyType.PAIRS_TRADING
        assert len(config.symbols) == 2
    
    def test_invalid_strategy_id_format(self):
        """Test validation of invalid strategy ID format."""
        risk_limits = RiskLimits(
            max_position_size=Decimal('5000'),
            max_portfolio_concentration=0.1,
            max_daily_loss=Decimal('500'),
            max_drawdown=0.05,
            stop_loss_percentage=0.03
        )
        
        with pytest.raises(ValueError, match="Strategy ID can only contain letters, numbers, underscores, and hyphens"):
            StrategyConfig(
                strategy_id="invalid strategy id!",
                strategy_type=StrategyType.MOMENTUM,
                name="Test Strategy",
                description="Test description",
                parameters={'lookback_period': 20, 'momentum_threshold': 0.02},
                symbols=["AAPL"],
                risk_limits=risk_limits
            )
    
    def test_empty_symbols_list(self):
        """Test validation of empty symbols list."""
        risk_limits = RiskLimits(
            max_position_size=Decimal('5000'),
            max_portfolio_concentration=0.1,
            max_daily_loss=Decimal('500'),
            max_drawdown=0.05,
            stop_loss_percentage=0.03
        )
        
        with pytest.raises(ValueError, match="At least one symbol must be specified"):
            StrategyConfig(
                strategy_id="test_001",
                strategy_type=StrategyType.MOMENTUM,
                name="Test Strategy",
                description="Test description",
                parameters={'lookback_period': 20, 'momentum_threshold': 0.02},
                symbols=[],
                risk_limits=risk_limits
            )
    
    def test_invalid_symbol_format(self):
        """Test validation of invalid symbol format."""
        risk_limits = RiskLimits(
            max_position_size=Decimal('5000'),
            max_portfolio_concentration=0.1,
            max_daily_loss=Decimal('500'),
            max_drawdown=0.05,
            stop_loss_percentage=0.03
        )
        
        with pytest.raises(ValueError, match="Invalid symbol format"):
            StrategyConfig(
                strategy_id="test_001",
                strategy_type=StrategyType.MOMENTUM,
                name="Test Strategy",
                description="Test description",
                parameters={'lookback_period': 20, 'momentum_threshold': 0.02},
                symbols=["invalid_symbol"],
                risk_limits=risk_limits
            )
    
    def test_momentum_strategy_missing_parameters(self):
        """Test validation of momentum strategy with missing parameters."""
        risk_limits = RiskLimits(
            max_position_size=Decimal('5000'),
            max_portfolio_concentration=0.1,
            max_daily_loss=Decimal('500'),
            max_drawdown=0.05,
            stop_loss_percentage=0.03
        )
        
        with pytest.raises(ValueError, match="Momentum strategy requires 'lookback_period' parameter"):
            StrategyConfig(
                strategy_id="momentum_001",
                strategy_type=StrategyType.MOMENTUM,
                name="Test Strategy",
                description="Test description",
                parameters={'momentum_threshold': 0.02},  # Missing lookback_period
                symbols=["AAPL"],
                risk_limits=risk_limits
            )
    
    def test_pairs_trading_wrong_symbol_count(self):
        """Test validation of pairs trading with wrong number of symbols."""
        risk_limits = RiskLimits(
            max_position_size=Decimal('5000'),
            max_portfolio_concentration=0.1,
            max_daily_loss=Decimal('500'),
            max_drawdown=0.05,
            stop_loss_percentage=0.03
        )
        
        with pytest.raises(ValueError, match="Pairs trading strategy requires exactly 2 symbols"):
            StrategyConfig(
                strategy_id="pairs_001",
                strategy_type=StrategyType.PAIRS_TRADING,
                name="Test Strategy",
                description="Test description",
                parameters={
                    'correlation_threshold': 0.8,
                    'spread_threshold': 2.0
                },
                symbols=["AAPL", "MSFT", "TSLA"],  # Too many symbols
                risk_limits=risk_limits
            )
    
    def test_invalid_priority(self):
        """Test validation of invalid priority."""
        risk_limits = RiskLimits(
            max_position_size=Decimal('5000'),
            max_portfolio_concentration=0.1,
            max_daily_loss=Decimal('500'),
            max_drawdown=0.05,
            stop_loss_percentage=0.03
        )
        
        with pytest.raises(ValueError, match="Priority must be an integer between 1 and 10"):
            StrategyConfig(
                strategy_id="test_001",
                strategy_type=StrategyType.MOMENTUM,
                name="Test Strategy",
                description="Test description",
                parameters={'lookback_period': 20, 'momentum_threshold': 0.02},
                symbols=["AAPL"],
                risk_limits=risk_limits,
                priority=15  # Invalid priority
            )


class TestSystemConfig:
    """Test cases for SystemConfig data model."""
    
    def test_valid_system_config(self):
        """Test creating a valid system configuration."""
        alpaca_config = AlpacaConfig(
            api_key="PKTEST1234567890ABCDEF",
            secret_key="abcdef1234567890abcdef1234567890abcdef12",
            base_url="https://paper-api.alpaca.markets"
        )
        
        risk_limits = RiskLimits(
            max_position_size=Decimal('10000'),
            max_portfolio_concentration=0.2,
            max_daily_loss=Decimal('1000'),
            max_drawdown=0.1,
            stop_loss_percentage=0.05
        )
        
        config = SystemConfig(
            alpaca_config=alpaca_config,
            default_risk_limits=risk_limits,
            log_level="INFO",
            data_retention_days=365
        )
        
        assert config.log_level == "INFO"
        assert config.data_retention_days == 365
        assert isinstance(config.alpaca_config, AlpacaConfig)
    
    def test_invalid_log_level(self):
        """Test validation of invalid log level."""
        alpaca_config = AlpacaConfig(
            api_key="PKTEST1234567890ABCDEF",
            secret_key="abcdef1234567890abcdef1234567890abcdef12",
            base_url="https://paper-api.alpaca.markets"
        )
        
        risk_limits = RiskLimits(
            max_position_size=Decimal('10000'),
            max_portfolio_concentration=0.2,
            max_daily_loss=Decimal('1000'),
            max_drawdown=0.1,
            stop_loss_percentage=0.05
        )
        
        with pytest.raises(ValueError, match="Log level must be one of"):
            SystemConfig(
                alpaca_config=alpaca_config,
                default_risk_limits=risk_limits,
                log_level="INVALID"
            )
    
    def test_invalid_data_retention_days(self):
        """Test validation of invalid data retention days."""
        alpaca_config = AlpacaConfig(
            api_key="PKTEST1234567890ABCDEF",
            secret_key="abcdef1234567890abcdef1234567890abcdef12",
            base_url="https://paper-api.alpaca.markets"
        )
        
        risk_limits = RiskLimits(
            max_position_size=Decimal('10000'),
            max_portfolio_concentration=0.2,
            max_daily_loss=Decimal('1000'),
            max_drawdown=0.1,
            stop_loss_percentage=0.05
        )
        
        with pytest.raises(ValueError, match="Data retention days must be between 1 and 3650"):
            SystemConfig(
                alpaca_config=alpaca_config,
                default_risk_limits=risk_limits,
                data_retention_days=5000
            )
    
    @patch.dict(os.environ, {
        'ALPACA_API_KEY': 'PKTEST1234567890ABCDEF',
        'ALPACA_SECRET_KEY': 'abcdef1234567890abcdef1234567890abcdef12',
        'LOG_LEVEL': 'DEBUG',
        'DATA_RETENTION_DAYS': '180'
    })
    def test_from_env(self):
        """Test creating system config from environment variables."""
        config = SystemConfig.from_env()
        
        assert config.log_level == "DEBUG"
        assert config.data_retention_days == 180
        assert isinstance(config.alpaca_config, AlpacaConfig)