"""Tests for configuration management."""

import pytest
import os
import tempfile
import json
from decimal import Decimal
from pathlib import Path

from financial_portfolio_automation.config.settings import (
    AlpacaConfig,
    RiskLimits,
    DatabaseConfig,
    LoggingConfig,
    NotificationConfig,
    SystemConfig,
    ConfigManager
)
from financial_portfolio_automation.exceptions import ConfigurationError


class TestAlpacaConfig:
    """Test Alpaca configuration."""
    
    def test_valid_config(self):
        """Test valid Alpaca configuration."""
        config = AlpacaConfig(
            api_key="test_key",
            secret_key="test_secret",
            base_url="https://paper-api.alpaca.markets",
            data_feed="iex"
        )
        assert config.api_key == "test_key"
        assert config.secret_key == "test_secret"
        assert config.base_url == "https://paper-api.alpaca.markets"
        assert config.data_feed == "iex"
    
    def test_missing_api_key(self):
        """Test configuration with missing API key."""
        with pytest.raises(ConfigurationError):
            AlpacaConfig(api_key="", secret_key="test_secret")
    
    def test_missing_secret_key(self):
        """Test configuration with missing secret key."""
        with pytest.raises(ConfigurationError):
            AlpacaConfig(api_key="test_key", secret_key="")


class TestRiskLimits:
    """Test risk limits configuration."""
    
    def test_valid_risk_limits(self):
        """Test valid risk limits."""
        limits = RiskLimits(
            max_position_size=Decimal("5000.00"),
            max_portfolio_concentration=0.15,
            max_daily_loss=Decimal("500.00"),
            max_drawdown=0.08,
            stop_loss_percentage=0.03
        )
        assert limits.max_position_size == Decimal("5000.00")
        assert limits.max_portfolio_concentration == 0.15
        assert limits.max_daily_loss == Decimal("500.00")
        assert limits.max_drawdown == 0.08
        assert limits.stop_loss_percentage == 0.03
    
    def test_invalid_concentration(self):
        """Test invalid portfolio concentration."""
        with pytest.raises(ConfigurationError):
            RiskLimits(max_portfolio_concentration=1.5)
        
        with pytest.raises(ConfigurationError):
            RiskLimits(max_portfolio_concentration=-0.1)
    
    def test_invalid_drawdown(self):
        """Test invalid max drawdown."""
        with pytest.raises(ConfigurationError):
            RiskLimits(max_drawdown=1.5)
        
        with pytest.raises(ConfigurationError):
            RiskLimits(max_drawdown=-0.1)


class TestConfigManager:
    """Test configuration manager."""
    
    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        # Set test environment variables
        test_env = {
            "ALPACA_API_KEY": "test_key",
            "ALPACA_SECRET_KEY": "test_secret",
            "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
            "MAX_POSITION_SIZE": "5000.00",
            "TRADING_ENABLED": "true",
            "LOG_LEVEL": "DEBUG"
        }
        
        # Temporarily set environment variables
        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            manager = ConfigManager()
            config = manager.load_config()
            
            assert config.alpaca.api_key == "test_key"
            assert config.alpaca.secret_key == "test_secret"
            assert config.risk_limits.max_position_size == Decimal("5000.00")
            assert config.trading_enabled is True
            assert config.logging.level == "DEBUG"
            
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    
    def test_load_from_file(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "ALPACA_API_KEY": "file_key",
            "ALPACA_SECRET_KEY": "file_secret",
            "MAX_POSITION_SIZE": "8000.00",
            "PAPER_TRADING": "false"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            manager = ConfigManager(config_file)
            config = manager.load_config()
            
            assert config.alpaca.api_key == "file_key"
            assert config.alpaca.secret_key == "file_secret"
            assert config.risk_limits.max_position_size == Decimal("8000.00")
            assert config.paper_trading is False
            
        finally:
            os.unlink(config_file)
    
    def test_validation_success(self):
        """Test successful configuration validation."""
        # Set minimal required environment
        test_env = {
            "ALPACA_API_KEY": "test_key",
            "ALPACA_SECRET_KEY": "test_secret"
        }
        
        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            manager = ConfigManager()
            assert manager.validate_config() is True
            
        finally:
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    
    def test_validation_failure_missing_credentials(self):
        """Test validation failure with missing credentials."""
        # Clear API credentials
        original_key = os.environ.get("ALPACA_API_KEY")
        original_secret = os.environ.get("ALPACA_SECRET_KEY")
        
        os.environ.pop("ALPACA_API_KEY", None)
        os.environ.pop("ALPACA_SECRET_KEY", None)
        
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigurationError, match="Alpaca API key and secret key are required"):
                manager.validate_config()
                
        finally:
            if original_key:
                os.environ["ALPACA_API_KEY"] = original_key
            if original_secret:
                os.environ["ALPACA_SECRET_KEY"] = original_secret