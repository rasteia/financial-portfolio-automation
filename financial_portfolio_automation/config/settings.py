"""
Configuration management for the portfolio automation system.

This module handles loading and validation of configuration settings
from environment variables and configuration files.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from decimal import Decimal
import json
from pathlib import Path

from ..exceptions import ConfigurationError


@dataclass
class AlpacaConfig:
    """Configuration for Alpaca Markets API."""
    api_key: str
    secret_key: str
    base_url: str = "https://paper-api.alpaca.markets"  # Default to paper trading
    data_feed: str = "iex"  # Default to IEX data feed
    
    def __post_init__(self):
        if not self.api_key or not self.secret_key:
            raise ConfigurationError("Alpaca API key and secret key are required")


@dataclass
class RiskLimits:
    """Risk management configuration."""
    max_position_size: Decimal = Decimal("10000.00")
    max_portfolio_concentration: float = 0.20  # 20% max per position
    max_daily_loss: Decimal = Decimal("1000.00")
    max_drawdown: float = 0.10  # 10% max drawdown
    stop_loss_percentage: float = 0.05  # 5% stop loss
    
    def __post_init__(self):
        if self.max_portfolio_concentration <= 0 or self.max_portfolio_concentration > 1:
            raise ConfigurationError("Portfolio concentration must be between 0 and 1")
        if self.max_drawdown <= 0 or self.max_drawdown > 1:
            raise ConfigurationError("Max drawdown must be between 0 and 1")


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = "sqlite:///portfolio_automation.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class NotificationConfig:
    """Notification system configuration."""
    email_enabled: bool = False
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)
    
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    webhook_timeout: int = 30


@dataclass
class SystemConfig:
    """Main system configuration."""
    alpaca: AlpacaConfig
    risk_limits: RiskLimits = field(default_factory=RiskLimits)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    
    # Cache settings
    cache_ttl_quotes: int = 1  # seconds
    cache_ttl_account: int = 30  # seconds
    cache_ttl_historical: int = 3600  # 1 hour
    
    # Trading settings
    trading_enabled: bool = False  # Safety default
    paper_trading: bool = True
    
    # MCP settings
    mcp_enabled: bool = True
    mcp_port: int = 8080


class ConfigManager:
    """Manages system configuration loading and validation."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or os.getenv("PORTFOLIO_CONFIG_FILE")
        self._config: Optional[SystemConfig] = None
    
    def load_config(self) -> SystemConfig:
        """Load configuration from environment variables and config file."""
        if self._config is not None:
            return self._config
        
        # Start with environment variables
        config_data = self._load_from_env()
        
        # Override with config file if provided
        if self.config_file and Path(self.config_file).exists():
            file_config = self._load_from_file(self.config_file)
            config_data.update(file_config)
        
        # Create configuration objects
        try:
            alpaca_config = AlpacaConfig(
                api_key=config_data.get("ALPACA_API_KEY", ""),
                secret_key=config_data.get("ALPACA_SECRET_KEY", ""),
                base_url=config_data.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
                data_feed=config_data.get("ALPACA_DATA_FEED", "iex")
            )
            
            risk_limits = RiskLimits(
                max_position_size=Decimal(config_data.get("MAX_POSITION_SIZE", "10000.00")),
                max_portfolio_concentration=float(config_data.get("MAX_PORTFOLIO_CONCENTRATION", "0.20")),
                max_daily_loss=Decimal(config_data.get("MAX_DAILY_LOSS", "1000.00")),
                max_drawdown=float(config_data.get("MAX_DRAWDOWN", "0.10")),
                stop_loss_percentage=float(config_data.get("STOP_LOSS_PERCENTAGE", "0.05"))
            )
            
            database_config = DatabaseConfig(
                url=config_data.get("DATABASE_URL", "sqlite:///portfolio_automation.db"),
                echo=config_data.get("DATABASE_ECHO", "false").lower() == "true",
                pool_size=int(config_data.get("DATABASE_POOL_SIZE", "5")),
                max_overflow=int(config_data.get("DATABASE_MAX_OVERFLOW", "10"))
            )
            
            logging_config = LoggingConfig(
                level=config_data.get("LOG_LEVEL", "INFO"),
                format=config_data.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                file_path=config_data.get("LOG_FILE_PATH"),
                max_file_size=int(config_data.get("LOG_MAX_FILE_SIZE", str(10 * 1024 * 1024))),
                backup_count=int(config_data.get("LOG_BACKUP_COUNT", "5"))
            )
            
            notification_config = NotificationConfig(
                email_enabled=config_data.get("EMAIL_ENABLED", "false").lower() == "true",
                email_smtp_server=config_data.get("EMAIL_SMTP_SERVER"),
                email_smtp_port=int(config_data.get("EMAIL_SMTP_PORT", "587")),
                email_username=config_data.get("EMAIL_USERNAME"),
                email_password=config_data.get("EMAIL_PASSWORD"),
                email_recipients=config_data.get("EMAIL_RECIPIENTS", "").split(",") if config_data.get("EMAIL_RECIPIENTS") else [],
                webhook_enabled=config_data.get("WEBHOOK_ENABLED", "false").lower() == "true",
                webhook_url=config_data.get("WEBHOOK_URL"),
                webhook_timeout=int(config_data.get("WEBHOOK_TIMEOUT", "30"))
            )
            
            self._config = SystemConfig(
                alpaca=alpaca_config,
                risk_limits=risk_limits,
                database=database_config,
                logging=logging_config,
                notifications=notification_config,
                cache_ttl_quotes=int(config_data.get("CACHE_TTL_QUOTES", "1")),
                cache_ttl_account=int(config_data.get("CACHE_TTL_ACCOUNT", "30")),
                cache_ttl_historical=int(config_data.get("CACHE_TTL_HISTORICAL", "3600")),
                trading_enabled=config_data.get("TRADING_ENABLED", "false").lower() == "true",
                paper_trading=config_data.get("PAPER_TRADING", "true").lower() == "true",
                mcp_enabled=config_data.get("MCP_ENABLED", "true").lower() == "true",
                mcp_port=int(config_data.get("MCP_PORT", "8080"))
            )
            
            return self._config
            
        except (ValueError, TypeError) as e:
            raise ConfigurationError(f"Invalid configuration value: {e}")
    
    def _load_from_env(self) -> Dict[str, str]:
        """Load configuration from environment variables."""
        return dict(os.environ)
    
    def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ConfigurationError(f"Failed to load config file {file_path}: {e}")
    
    def validate_config(self) -> bool:
        """Validate the current configuration."""
        config = self.load_config()
        
        # Validate Alpaca configuration
        if not config.alpaca.api_key or not config.alpaca.secret_key:
            raise ConfigurationError("Alpaca API credentials are required")
        
        # Validate risk limits
        if config.risk_limits.max_position_size <= 0:
            raise ConfigurationError("Max position size must be positive")
        
        if config.risk_limits.max_daily_loss <= 0:
            raise ConfigurationError("Max daily loss must be positive")
        
        # Validate notification settings
        if config.notifications.email_enabled:
            if not config.notifications.email_smtp_server:
                raise ConfigurationError("Email SMTP server is required when email notifications are enabled")
            if not config.notifications.email_recipients:
                raise ConfigurationError("Email recipients are required when email notifications are enabled")
        
        if config.notifications.webhook_enabled:
            if not config.notifications.webhook_url:
                raise ConfigurationError("Webhook URL is required when webhook notifications are enabled")
        
        return True


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> SystemConfig:
    """Get the current system configuration."""
    return config_manager.load_config()


def validate_config() -> bool:
    """Validate the current system configuration."""
    return config_manager.validate_config()