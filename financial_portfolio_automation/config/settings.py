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
from ..models.config import Environment, DataFeed


@dataclass
class AlpacaConfig:
    """Configuration for Alpaca Markets API."""
    api_key: str
    secret_key: str
    environment: Environment = Environment.PAPER  # Trading environment
    base_url: str = "https://paper-api.alpaca.markets"  # Default to paper trading
    data_feed: DataFeed = DataFeed.IEX  # Default to IEX data feed
    
    def __post_init__(self):
        if not self.api_key or not self.secret_key:
            raise ConfigurationError("Alpaca API key and secret key are required")
        
        if not isinstance(self.environment, Environment):
            raise ConfigurationError("Alpaca environment must be Environment.PAPER or Environment.LIVE")
        
        if not isinstance(self.data_feed, DataFeed):
            raise ConfigurationError("Alpaca data feed must be a valid DataFeed enum value")


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
            # Handle nested JSON structure or flat environment variables
            alpaca_data = config_data.get("alpaca", {})
            
            # Convert string values to enums
            environment_str = alpaca_data.get("environment") or config_data.get("ALPACA_ENVIRONMENT", "paper")
            data_feed_str = alpaca_data.get("data_feed") or config_data.get("ALPACA_DATA_FEED", "iex")
            
            try:
                environment = Environment(environment_str.lower())
            except ValueError:
                raise ConfigurationError(f"Invalid environment '{environment_str}'. Must be 'paper' or 'live'")
            
            try:
                data_feed = DataFeed(data_feed_str.lower())
            except ValueError:
                raise ConfigurationError(f"Invalid data feed '{data_feed_str}'. Must be 'iex', 'sip', or 'opra'")
            
            alpaca_config = AlpacaConfig(
                api_key=alpaca_data.get("api_key") or config_data.get("ALPACA_API_KEY", ""),
                secret_key=alpaca_data.get("secret_key") or config_data.get("ALPACA_SECRET_KEY", ""),
                environment=environment,
                base_url=alpaca_data.get("base_url") or config_data.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
                data_feed=data_feed
            )
            
            risk_data = config_data.get("risk_limits", {})
            risk_limits = RiskLimits(
                max_position_size=Decimal(risk_data.get("max_position_size") or config_data.get("MAX_POSITION_SIZE", "10000.00")),
                max_portfolio_concentration=float(risk_data.get("max_portfolio_concentration") or config_data.get("MAX_PORTFOLIO_CONCENTRATION", "0.20")),
                max_daily_loss=Decimal(risk_data.get("max_daily_loss") or config_data.get("MAX_DAILY_LOSS", "1000.00")),
                max_drawdown=float(risk_data.get("max_drawdown") or config_data.get("MAX_DRAWDOWN", "0.10")),
                stop_loss_percentage=float(risk_data.get("stop_loss_percentage") or config_data.get("STOP_LOSS_PERCENTAGE", "0.05"))
            )
            
            db_data = config_data.get("database", {})
            database_config = DatabaseConfig(
                url=db_data.get("url") or config_data.get("DATABASE_URL", "sqlite:///portfolio_automation.db"),
                echo=db_data.get("echo") or config_data.get("DATABASE_ECHO", "false").lower() == "true",
                pool_size=int(db_data.get("pool_size") or config_data.get("DATABASE_POOL_SIZE", "5")),
                max_overflow=int(db_data.get("max_overflow") or config_data.get("DATABASE_MAX_OVERFLOW", "10"))
            )
            
            log_data = config_data.get("logging", {})
            logging_config = LoggingConfig(
                level=log_data.get("level") or config_data.get("LOG_LEVEL", "INFO"),
                format=log_data.get("format") or config_data.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                file_path=log_data.get("file_path") or config_data.get("LOG_FILE_PATH"),
                max_file_size=int(log_data.get("max_file_size") or config_data.get("LOG_MAX_FILE_SIZE", str(10 * 1024 * 1024))),
                backup_count=int(log_data.get("backup_count") or config_data.get("LOG_BACKUP_COUNT", "5"))
            )
            
            notif_data = config_data.get("notifications", {})
            notification_config = NotificationConfig(
                email_enabled=notif_data.get("email_enabled") or config_data.get("EMAIL_ENABLED", "false").lower() == "true",
                email_smtp_server=notif_data.get("email_smtp_server") or config_data.get("EMAIL_SMTP_SERVER"),
                email_smtp_port=int(notif_data.get("email_smtp_port") or config_data.get("EMAIL_SMTP_PORT", "587")),
                email_username=notif_data.get("email_username") or config_data.get("EMAIL_USERNAME"),
                email_password=notif_data.get("email_password") or config_data.get("EMAIL_PASSWORD"),
                email_recipients=notif_data.get("email_recipients") or (config_data.get("EMAIL_RECIPIENTS", "").split(",") if config_data.get("EMAIL_RECIPIENTS") else []),
                webhook_enabled=notif_data.get("webhook_enabled") or config_data.get("WEBHOOK_ENABLED", "false").lower() == "true",
                webhook_url=notif_data.get("webhook_url") or config_data.get("WEBHOOK_URL"),
                webhook_timeout=int(notif_data.get("webhook_timeout") or config_data.get("WEBHOOK_TIMEOUT", "30"))
            )
            
            self._config = SystemConfig(
                alpaca=alpaca_config,
                risk_limits=risk_limits,
                database=database_config,
                logging=logging_config,
                notifications=notification_config,
                cache_ttl_quotes=int(config_data.get("cache_ttl_quotes") or config_data.get("CACHE_TTL_QUOTES", "1")),
                cache_ttl_account=int(config_data.get("cache_ttl_account") or config_data.get("CACHE_TTL_ACCOUNT", "30")),
                cache_ttl_historical=int(config_data.get("cache_ttl_historical") or config_data.get("CACHE_TTL_HISTORICAL", "3600")),
                trading_enabled=config_data.get("trading_enabled") or config_data.get("TRADING_ENABLED", "false").lower() == "true",
                paper_trading=config_data.get("paper_trading") or config_data.get("PAPER_TRADING", "true").lower() == "true",
                mcp_enabled=config_data.get("mcp_enabled") or config_data.get("MCP_ENABLED", "true").lower() == "true",
                mcp_port=int(config_data.get("mcp_port") or config_data.get("MCP_PORT", "8080"))
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