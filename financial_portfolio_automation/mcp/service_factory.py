"""
Service Factory for MCP Tools

This module provides a factory for creating properly initialized services
with correct dependency injection for MCP tool integration.
"""

import logging
from typing import Dict, Any, Optional

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


class ServiceFactory:
    """Factory for creating properly initialized services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize service factory.
        
        Args:
            config: Configuration dictionary or None to load from system
        """
        self.logger = logging.getLogger(__name__)
        
        # Load system configuration
        if config is None:
            try:
                system_config = get_config()
                self.config = system_config
            except Exception as e:
                self.logger.warning(f"Could not load system config: {e}")
                self.config = None
        else:
            # Convert dict config to proper objects if needed
            if isinstance(config, dict):
                self.config = self._convert_dict_config(config)
            else:
                self.config = config
        
        # Initialize core services
        self._data_store = None
        self._data_cache = None
        self._alpaca_client = None
        self._portfolio_analyzer = None
        self._trade_logger = None
    
    def _convert_dict_config(self, config_dict: Dict[str, Any]) -> SystemConfig:
        """Convert dictionary config to SystemConfig object."""
        try:
            # Extract alpaca config
            alpaca_data = config_dict.get('alpaca', {})
            if not alpaca_data and 'api_key' in config_dict:
                # Handle flat structure
                alpaca_config = AlpacaConfig(
                    api_key=config_dict.get('api_key', ''),
                    secret_key=config_dict.get('secret_key', ''),
                    base_url=config_dict.get('base_url', 'https://paper-api.alpaca.markets'),
                    data_feed=DataFeed.IEX,
                    environment=Environment.PAPER
                )
            else:
                # Handle nested structure
                alpaca_config = AlpacaConfig(
                    api_key=alpaca_data.get('api_key', ''),
                    secret_key=alpaca_data.get('secret_key', ''),
                    base_url=alpaca_data.get('base_url', 'https://paper-api.alpaca.markets'),
                    data_feed=DataFeed.IEX,
                    environment=Environment.PAPER
                )
            
            # Create minimal SystemConfig
            from ..config.settings import SystemConfig, RiskLimits, DatabaseConfig, LoggingConfig, NotificationConfig
            
            return SystemConfig(
                alpaca=alpaca_config,
                risk_limits=RiskLimits(),
                database=DatabaseConfig(),
                logging=LoggingConfig(),
                notifications=NotificationConfig()
            )
        except Exception as e:
            self.logger.error(f"Failed to convert config: {e}")
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
        """Get or create Alpaca client instance."""
        if self._alpaca_client is None:
            try:
                if self.config and hasattr(self.config, 'alpaca'):
                    self._alpaca_client = AlpacaClient(self.config.alpaca)
                else:
                    self.logger.warning("No Alpaca configuration available")
                    return None
            except Exception as e:
                self.logger.warning(f"Could not create Alpaca client: {e}")
                return None
        return self._alpaca_client
    
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