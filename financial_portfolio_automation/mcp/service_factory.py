"""
Service Factory for MCP Tools

This module provides a factory for creating properly initialized services
with correct dependency injection for MCP tool integration.
"""

import logging
from typing import Dict, Any, Optional, List

from ..config.settings import get_config, SystemConfig
from ..data.store import DataStore
from ..data.cache import DataCache
from ..analytics.analytics_service import AnalyticsService, AnalyticsConfig
from ..analysis.portfolio_analyzer import PortfolioAnalyzer
from ..analysis.risk_manager import RiskManager
from ..api.alpaca_client import AlpacaClient
from ..models.config import AlpacaConfig, Environment, DataFeed
from ..monitoring.portfolio_monitor import PortfolioMonitor
from ..reporting.report_generator import ReportGenerator
from ..reporting.performance_report import PerformanceReport
from ..reporting.tax_report import TaxReport
from ..reporting.transaction_report import TransactionReport
from ..execution.trade_logger import TradeLogger
from ..strategy.registry import StrategyRegistry
from ..exceptions import PortfolioAutomationError


class ConfigurationError(PortfolioAutomationError):
    """Raised when configuration is invalid or incomplete."""
    pass


class ServiceFactory:
    """Factory for creating properly initialized services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize service factory.
        
        Args:
            config: Configuration dictionary or None to load from system
        """
        self.logger = logging.getLogger(__name__)
        
        # Load system configuration with comprehensive error handling
        if config is None:
            try:
                system_config = get_config()
                self.config = system_config
                self.logger.info("Successfully loaded system configuration")
            except FileNotFoundError as e:
                self.logger.error(
                    f"Configuration file not found: {e}\n"
                    "Resolution steps:\n"
                    "  - Ensure configuration file exists in the expected location\n"
                    "  - Check file permissions and accessibility\n"
                    "  - Verify configuration file path is correct"
                )
                self.config = None
            except PermissionError as e:
                self.logger.error(
                    f"Permission denied accessing configuration: {e}\n"
                    "Resolution steps:\n"
                    "  - Check file permissions for configuration files\n"
                    "  - Ensure the application has read access to config directory\n"
                    "  - Run with appropriate user permissions"
                )
                self.config = None
            except ValueError as e:
                self.logger.error(
                    f"Invalid configuration format or values: {e}\n"
                    "Resolution steps:\n"
                    "  - Validate configuration file syntax (JSON/YAML)\n"
                    "  - Check for required configuration fields\n"
                    "  - Verify configuration value formats and ranges"
                )
                self.config = None
            except Exception as e:
                self.logger.error(
                    f"Unexpected error loading system configuration: {e}\n"
                    "Resolution steps:\n"
                    "  - Check system logs for additional error details\n"
                    "  - Verify configuration file integrity\n"
                    "  - Try restarting the application\n"
                    "  - Contact support if the issue persists"
                )
                self.config = None
        else:
            # Convert dict config to proper objects if needed
            if isinstance(config, dict):
                self.logger.info("Converting provided dictionary configuration")
                self.config = self._convert_dict_config(config)
            else:
                self.logger.info("Using provided configuration object")
                self.config = config
        
        # Initialize core services
        self._data_store = None
        self._data_cache = None
        self._alpaca_client = None
        self._portfolio_analyzer = None
        self._trade_logger = None
    
    def _convert_dict_config(self, config_dict: Dict[str, Any]) -> Optional[SystemConfig]:
        """
        Convert dictionary config to SystemConfig object with comprehensive error handling.
        
        Args:
            config_dict: Dictionary containing configuration data
            
        Returns:
            SystemConfig object or None if conversion fails
        """
        try:
            # Extract alpaca config with better error handling
            alpaca_data = config_dict.get('alpaca', {})
            
            if not alpaca_data and 'api_key' in config_dict:
                # Handle flat structure
                self.logger.info("Converting flat configuration structure to AlpacaConfig")
                alpaca_config = self._create_alpaca_config_from_flat(config_dict)
            else:
                # Handle nested structure
                self.logger.info("Converting nested configuration structure to AlpacaConfig")
                alpaca_config = self._create_alpaca_config_from_nested(alpaca_data)
            
            if not alpaca_config:
                self.logger.error("Failed to create AlpacaConfig from provided data")
                return None
            
            # Create minimal SystemConfig
            from ..config.settings import SystemConfig, RiskLimits, DatabaseConfig, LoggingConfig, NotificationConfig
            
            system_config = SystemConfig(
                alpaca=alpaca_config,
                risk_limits=RiskLimits(),
                database=DatabaseConfig(),
                logging=LoggingConfig(),
                notifications=NotificationConfig()
            )
            
            self.logger.info("Successfully converted dictionary config to SystemConfig")
            return system_config
            
        except ImportError as e:
            self.logger.error(
                f"Failed to import required configuration classes: {e}\n"
                "This may indicate missing dependencies or circular imports."
            )
            return None
            
        except ValueError as e:
            self.logger.error(
                f"Invalid configuration values provided: {e}\n"
                "Please check your configuration format and values."
            )
            return None
            
        except Exception as e:
            self.logger.error(
                f"Unexpected error during config conversion: {e}\n"
                "Please verify your configuration structure and try again."
            )
            return None
    
    def _create_alpaca_config_from_flat(self, config_dict: Dict[str, Any]) -> Optional[AlpacaConfig]:
        """Create AlpacaConfig from flat dictionary structure."""
        try:
            from ..models.config import AlpacaConfig, DataFeed, Environment
            
            # Extract environment with proper handling
            env_str = config_dict.get('environment', 'paper').lower()
            try:
                environment = Environment(env_str)
            except ValueError:
                self.logger.warning(f"Invalid environment '{env_str}', defaulting to paper")
                environment = Environment.PAPER
            
            # Extract data feed with proper handling
            feed_str = config_dict.get('data_feed', 'iex').lower()
            try:
                data_feed = DataFeed(feed_str)
            except ValueError:
                self.logger.warning(f"Invalid data feed '{feed_str}', defaulting to IEX")
                data_feed = DataFeed.IEX
            
            # Set appropriate base URL based on environment if not provided
            base_url = config_dict.get('base_url')
            if not base_url:
                if environment == Environment.PAPER:
                    base_url = 'https://paper-api.alpaca.markets'
                else:
                    base_url = 'https://api.alpaca.markets'
                self.logger.info(f"Using default base URL for {environment.value}: {base_url}")
            
            return AlpacaConfig(
                api_key=config_dict.get('api_key', ''),
                secret_key=config_dict.get('secret_key', ''),
                base_url=base_url,
                data_feed=data_feed,
                environment=environment
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create AlpacaConfig from flat structure: {e}")
            return None
    
    def _create_alpaca_config_from_nested(self, alpaca_data: Dict[str, Any]) -> Optional[AlpacaConfig]:
        """Create AlpacaConfig from nested dictionary structure."""
        try:
            from ..models.config import AlpacaConfig, DataFeed, Environment
            
            # Extract environment with proper handling
            env_str = alpaca_data.get('environment', 'paper').lower()
            try:
                environment = Environment(env_str)
            except ValueError:
                self.logger.warning(f"Invalid environment '{env_str}', defaulting to paper")
                environment = Environment.PAPER
            
            # Extract data feed with proper handling
            feed_str = alpaca_data.get('data_feed', 'iex').lower()
            try:
                data_feed = DataFeed(feed_str)
            except ValueError:
                self.logger.warning(f"Invalid data feed '{feed_str}', defaulting to IEX")
                data_feed = DataFeed.IEX
            
            # Set appropriate base URL based on environment if not provided
            base_url = alpaca_data.get('base_url')
            if not base_url:
                if environment == Environment.PAPER:
                    base_url = 'https://paper-api.alpaca.markets'
                else:
                    base_url = 'https://api.alpaca.markets'
                self.logger.info(f"Using default base URL for {environment.value}: {base_url}")
            
            return AlpacaConfig(
                api_key=alpaca_data.get('api_key', ''),
                secret_key=alpaca_data.get('secret_key', ''),
                base_url=base_url,
                data_feed=data_feed,
                environment=environment
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create AlpacaConfig from nested structure: {e}")
            return None
    
    def get_data_store(self) -> Optional[DataStore]:
        """Get or create data store instance."""
        if self._data_store is None:
            try:
                self._data_store = DataStore()
            except Exception as e:
                self.logger.warning(f"Could not create data store: {e}")
                return None
        return self._data_store
    
    def get_data_cache(self) -> Optional[DataCache]:
        """Get or create data cache instance."""
        if self._data_cache is None:
            try:
                self._data_cache = DataCache()
            except Exception as e:
                self.logger.warning(f"Could not create data cache: {e}")
                return None
        return self._data_cache
    
    def get_alpaca_client(self) -> Optional[AlpacaClient]:
        """Get or create Alpaca client instance with comprehensive error handling."""
        if self._alpaca_client is None:
            try:
                # Validate configuration availability
                if not self.config:
                    self.logger.error(
                        "Alpaca client creation failed: No system configuration available. "
                        "Please ensure configuration is properly loaded or provided."
                    )
                    return None
                
                # Check for alpaca configuration
                if not hasattr(self.config, 'alpaca') or self.config.alpaca is None:
                    self.logger.error(
                        "Alpaca client creation failed: Missing Alpaca configuration. "
                        "Required configuration: api_key, secret_key, base_url, environment. "
                        "Please add Alpaca configuration to your system config."
                    )
                    return None
                
                # Validate alpaca configuration completeness
                alpaca_config = self.config.alpaca
                validation_errors = self._validate_alpaca_config(alpaca_config)
                
                if validation_errors:
                    error_msg = "Alpaca client creation failed due to configuration issues:\n"
                    for i, error in enumerate(validation_errors, 1):
                        error_msg += f"  {i}. {error}\n"
                    error_msg += "\nResolution steps:\n"
                    error_msg += "  - Verify all required Alpaca configuration fields are set\n"
                    error_msg += "  - Check that API keys are valid and not expired\n"
                    error_msg += "  - Ensure environment matches the intended trading mode (paper/live)\n"
                    error_msg += "  - Verify base_url corresponds to the selected environment"
                    
                    self.logger.error(error_msg)
                    return None
                
                # Attempt to create Alpaca client
                self.logger.info(f"Creating Alpaca client for {alpaca_config.environment.value} environment")
                self._alpaca_client = AlpacaClient(alpaca_config)
                self.logger.info("Alpaca client created successfully")
                
            except ConfigurationError as e:
                self.logger.error(
                    f"Alpaca client creation failed due to configuration error: {e}\n"
                    "Resolution steps:\n"
                    "  - Review and correct the Alpaca configuration\n"
                    "  - Ensure all required fields are properly set\n"
                    "  - Validate API credentials with Alpaca"
                )
                return None
                
            except ValueError as e:
                self.logger.error(
                    f"Alpaca client creation failed due to invalid configuration values: {e}\n"
                    "Resolution steps:\n"
                    "  - Check configuration value formats and ranges\n"
                    "  - Ensure environment is 'paper' or 'live'\n"
                    "  - Verify URL format and protocol (https://)"
                )
                return None
                
            except ImportError as e:
                self.logger.error(
                    f"Alpaca client creation failed due to missing dependencies: {e}\n"
                    "Resolution steps:\n"
                    "  - Install required Alpaca SDK: pip install alpaca-trade-api\n"
                    "  - Verify all trading dependencies are installed\n"
                    "  - Check for version compatibility issues"
                )
                return None
                
            except Exception as e:
                self.logger.error(
                    f"Alpaca client creation failed due to unexpected error: {e}\n"
                    "Resolution steps:\n"
                    "  - Check system logs for additional error details\n"
                    "  - Verify network connectivity to Alpaca services\n"
                    "  - Ensure API credentials are valid and active\n"
                    "  - Try restarting the application"
                )
                return None
        
        return self._alpaca_client
    
    def _validate_alpaca_config(self, config: AlpacaConfig) -> List[str]:
        """
        Validate Alpaca configuration and return list of validation errors.
        
        Args:
            config: AlpacaConfig instance to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        try:
            # Check required string fields
            if not config.api_key or not isinstance(config.api_key, str):
                errors.append("API key is missing or invalid")
            elif len(config.api_key.strip()) < 8:
                errors.append("API key appears to be too short or empty")
            
            if not config.secret_key or not isinstance(config.secret_key, str):
                errors.append("Secret key is missing or invalid")
            elif len(config.secret_key.strip()) < 8:
                errors.append("Secret key appears to be too short or empty")
            
            if not config.base_url or not isinstance(config.base_url, str):
                errors.append("Base URL is missing or invalid")
            elif not config.base_url.startswith(('http://', 'https://')):
                errors.append("Base URL must start with http:// or https://")
            
            # Check environment field exists and is valid
            if not hasattr(config, 'environment') or config.environment is None:
                errors.append("Environment field is missing (required: 'paper' or 'live')")
            elif not isinstance(config.environment, Environment):
                errors.append("Environment must be Environment.PAPER or Environment.LIVE")
            
            # Check data_feed field
            if not hasattr(config, 'data_feed') or config.data_feed is None:
                errors.append("Data feed field is missing")
            elif not isinstance(config.data_feed, DataFeed):
                errors.append("Data feed must be a valid DataFeed enum value")
            
            # Validate environment-URL consistency
            if hasattr(config, 'environment') and config.environment and config.base_url:
                if config.environment == Environment.PAPER and "paper" not in config.base_url.lower():
                    errors.append("Paper trading environment requires paper trading URL")
                elif config.environment == Environment.LIVE and "paper" in config.base_url.lower():
                    errors.append("Live trading environment cannot use paper trading URL")
            
        except Exception as e:
            errors.append(f"Configuration validation failed: {e}")
        
        return errors
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """
        Get comprehensive configuration status for diagnostics.
        
        Returns:
            Dictionary containing configuration status and validation results
        """
        status = {
            'config_loaded': self.config is not None,
            'alpaca_config_available': False,
            'alpaca_config_valid': False,
            'validation_errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        if not self.config:
            status['warnings'].append("No system configuration loaded")
            status['recommendations'].extend([
                "Load configuration from file or provide configuration dictionary",
                "Ensure configuration file exists and is accessible",
                "Check configuration file format and syntax"
            ])
            return status
        
        # Check Alpaca configuration availability
        if hasattr(self.config, 'alpaca') and self.config.alpaca:
            status['alpaca_config_available'] = True
            
            # Validate Alpaca configuration
            validation_errors = self._validate_alpaca_config(self.config.alpaca)
            status['validation_errors'] = validation_errors
            status['alpaca_config_valid'] = len(validation_errors) == 0
            
            if validation_errors:
                status['recommendations'].extend([
                    "Review and correct Alpaca configuration errors",
                    "Ensure all required fields are properly set",
                    "Validate API credentials with Alpaca"
                ])
            else:
                status['recommendations'].append("Alpaca configuration is valid and ready for use")
        else:
            status['warnings'].append("Alpaca configuration not found")
            status['recommendations'].extend([
                "Add Alpaca configuration to system config",
                "Provide api_key, secret_key, base_url, and environment",
                "Ensure environment matches intended trading mode (paper/live)"
            ])
        
        return status
    
    def log_configuration_diagnostics(self) -> None:
        """Log comprehensive configuration diagnostics."""
        status = self.get_configuration_status()
        
        self.logger.info("=== Configuration Diagnostics ===")
        self.logger.info(f"Configuration loaded: {status['config_loaded']}")
        self.logger.info(f"Alpaca config available: {status['alpaca_config_available']}")
        self.logger.info(f"Alpaca config valid: {status['alpaca_config_valid']}")
        
        if status['validation_errors']:
            self.logger.warning("Configuration validation errors:")
            for i, error in enumerate(status['validation_errors'], 1):
                self.logger.warning(f"  {i}. {error}")
        
        if status['warnings']:
            self.logger.warning("Configuration warnings:")
            for warning in status['warnings']:
                self.logger.warning(f"  - {warning}")
        
        if status['recommendations']:
            self.logger.info("Recommendations:")
            for rec in status['recommendations']:
                self.logger.info(f"  - {rec}")
        
        self.logger.info("=== End Configuration Diagnostics ===")
    
    def can_create_alpaca_client(self) -> bool:
        """
        Check if Alpaca client can be created with current configuration.
        
        Returns:
            True if Alpaca client can be created, False otherwise
        """
        if not self.config or not hasattr(self.config, 'alpaca') or not self.config.alpaca:
            return False
        
        validation_errors = self._validate_alpaca_config(self.config.alpaca)
        return len(validation_errors) == 0
    
    def get_portfolio_analyzer(self) -> Optional[PortfolioAnalyzer]:
        """Get or create portfolio analyzer instance."""
        if self._portfolio_analyzer is None:
            try:
                # PortfolioAnalyzer takes no constructor arguments
                self._portfolio_analyzer = PortfolioAnalyzer()
            except Exception as e:
                self.logger.warning(f"Could not create portfolio analyzer: {e}")
                return None
        return self._portfolio_analyzer
    
    def get_trade_logger(self) -> Optional[TradeLogger]:
        """Get or create trade logger instance."""
        if self._trade_logger is None:
            try:
                data_store = self.get_data_store()
                if data_store:
                    self._trade_logger = TradeLogger(data_store)
                else:
                    self.logger.warning("Data store not available for trade logger")
                    return None
            except Exception as e:
                self.logger.warning(f"Could not create trade logger: {e}")
                return None
        return self._trade_logger
    
    def get_analytics_service(self) -> Optional[AnalyticsService]:
        """Get or create analytics service instance."""
        try:
            data_store = self.get_data_store()
            data_cache = self.get_data_cache()
            portfolio_analyzer = self.get_portfolio_analyzer()
            
            if data_store and data_cache and portfolio_analyzer:
                return AnalyticsService(
                    data_store=data_store,
                    data_cache=data_cache,
                    portfolio_analyzer=portfolio_analyzer,
                    config=AnalyticsConfig()
                )
            else:
                self.logger.warning("Dependencies not available for analytics service")
                return None
        except Exception as e:
            self.logger.warning(f"Could not create analytics service: {e}")
            return None
    
    def get_risk_manager(self) -> Optional[RiskManager]:
        """Get or create risk manager instance."""
        try:
            portfolio_analyzer = self.get_portfolio_analyzer()
            if portfolio_analyzer:
                return RiskManager(portfolio_analyzer)
            else:
                self.logger.warning("Portfolio analyzer not available for risk manager")
                return None
        except Exception as e:
            self.logger.warning(f"Could not create risk manager: {e}")
            return None
    
    def get_portfolio_monitor(self) -> Optional[PortfolioMonitor]:
        """Get or create portfolio monitor instance."""
        try:
            alpaca_client = self.get_alpaca_client()
            data_store = self.get_data_store()
            if alpaca_client and data_store:
                return PortfolioMonitor(alpaca_client, data_store)
            else:
                self.logger.warning("Dependencies not available for portfolio monitor")
                return None
        except Exception as e:
            self.logger.warning(f"Could not create portfolio monitor: {e}")
            return None
    
    def get_report_generator(self) -> Optional[ReportGenerator]:
        """Get or create report generator instance."""
        try:
            portfolio_analyzer = self.get_portfolio_analyzer()
            trade_logger = self.get_trade_logger()
            if portfolio_analyzer and trade_logger:
                return ReportGenerator(portfolio_analyzer, trade_logger)
            else:
                self.logger.warning("Dependencies not available for report generator")
                return None
        except Exception as e:
            self.logger.warning(f"Could not create report generator: {e}")
            return None
    
    def get_performance_report(self) -> Optional[PerformanceReport]:
        """Get or create performance report instance."""
        try:
            portfolio_analyzer = self.get_portfolio_analyzer()
            if portfolio_analyzer:
                return PerformanceReport(portfolio_analyzer)
            else:
                self.logger.warning("Portfolio analyzer not available for performance report")
                return None
        except Exception as e:
            self.logger.warning(f"Could not create performance report: {e}")
            return None
    
    def get_tax_report(self) -> Optional[TaxReport]:
        """Get or create tax report instance."""
        try:
            trade_logger = self.get_trade_logger()
            if trade_logger:
                return TaxReport(trade_logger)
            else:
                self.logger.warning("Trade logger not available for tax report")
                return None
        except Exception as e:
            self.logger.warning(f"Could not create tax report: {e}")
            return None
    
    def get_transaction_report(self) -> Optional[TransactionReport]:
        """Get or create transaction report instance."""
        try:
            trade_logger = self.get_trade_logger()
            if trade_logger:
                return TransactionReport(trade_logger)
            else:
                self.logger.warning("Trade logger not available for transaction report")
                return None
        except Exception as e:
            self.logger.warning(f"Could not create transaction report: {e}")
            return None
    
    def get_strategy_registry(self) -> Optional[StrategyRegistry]:
        """Get or create strategy registry instance."""
        try:
            return StrategyRegistry()
        except Exception as e:
            self.logger.warning(f"Could not create strategy registry: {e}")
            return None