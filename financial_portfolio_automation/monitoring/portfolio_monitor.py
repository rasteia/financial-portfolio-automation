"""
Real-time portfolio monitoring system for tracking positions, price movements, and market volatility.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from ..models.core import Position, Quote, PortfolioSnapshot
from ..analysis.portfolio_analyzer import PortfolioAnalyzer
from ..analysis.technical_analysis import TechnicalAnalysis
from ..data.cache import DataCache
from ..exceptions import MonitoringError


class AlertSeverity(Enum):
    """Alert severity levels for portfolio monitoring."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MonitoringAlert:
    """Represents a portfolio monitoring alert."""
    alert_id: str
    timestamp: datetime
    severity: AlertSeverity
    alert_type: str
    symbol: Optional[str]
    message: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringThresholds:
    """Configuration for portfolio monitoring thresholds."""
    # Position-level thresholds
    position_change_percent: float = 5.0  # Alert on 5% position value change
    position_change_amount: Decimal = Decimal('1000')  # Alert on $1000 position change
    
    # Portfolio-level thresholds
    portfolio_change_percent: float = 2.0  # Alert on 2% portfolio value change
    daily_pnl_threshold: Decimal = Decimal('5000')  # Alert on $5000 daily P&L
    drawdown_threshold: float = 10.0  # Alert on 10% drawdown
    
    # Market volatility thresholds
    volatility_threshold: float = 0.3  # Alert on 30% annualized volatility
    price_movement_percent: float = 10.0  # Alert on 10% price movement
    volume_spike_multiplier: float = 3.0  # Alert on 3x average volume
    
    # Time-based settings
    monitoring_interval: int = 5  # Monitor every 5 seconds
    volatility_window: int = 20  # 20-period volatility calculation


class PortfolioMonitor:
    """
    Real-time portfolio monitoring system that tracks positions, detects price movements,
    and analyzes market volatility to generate alerts.
    """
    
    def __init__(
        self,
        portfolio_analyzer: PortfolioAnalyzer,
        technical_analysis: TechnicalAnalysis,
        data_cache: DataCache,
        thresholds: Optional[MonitoringThresholds] = None
    ):
        """
        Initialize the portfolio monitor.
        
        Args:
            portfolio_analyzer: Portfolio analysis engine
            technical_analysis: Technical analysis engine
            data_cache: Data cache for market data
            thresholds: Monitoring thresholds configuration
        """
        self.portfolio_analyzer = portfolio_analyzer
        self.technical_analysis = technical_analysis
        self.data_cache = data_cache
        self.thresholds = thresholds or MonitoringThresholds()
        
        self.logger = logging.getLogger(__name__)
        self.is_monitoring = False
        self.alert_callbacks: List[Callable[[MonitoringAlert], None]] = []
        
        # Monitoring state
        self._last_portfolio_snapshot: Optional[PortfolioSnapshot] = None
        self._position_baselines: Dict[str, Decimal] = {}
        self._price_baselines: Dict[str, Decimal] = {}
        self._volatility_cache: Dict[str, List[float]] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
    
    def add_alert_callback(self, callback: Callable[[MonitoringAlert], None]) -> None:
        """Add a callback function to receive monitoring alerts."""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[MonitoringAlert], None]) -> None:
        """Remove a callback function from alert notifications."""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    async def start_monitoring(self, symbols: List[str]) -> None:
        """
        Start real-time portfolio monitoring.
        
        Args:
            symbols: List of symbols to monitor
        """
        if self.is_monitoring:
            self.logger.warning("Portfolio monitoring is already running")
            return
        
        self.logger.info(f"Starting portfolio monitoring for {len(symbols)} symbols")
        self.is_monitoring = True
        
        # Initialize baselines
        await self._initialize_baselines(symbols)
        
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(symbols))
    
    async def stop_monitoring(self) -> None:
        """Stop real-time portfolio monitoring."""
        if not self.is_monitoring:
            return
        
        self.logger.info("Stopping portfolio monitoring")
        self.is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _initialize_baselines(self, symbols: List[str]) -> None:
        """Initialize baseline values for monitoring comparisons."""
        try:
            # Get current portfolio snapshot
            positions = await self._get_current_positions()
            if positions:
                portfolio_snapshot = self.portfolio_analyzer.create_portfolio_snapshot(positions)
                self._last_portfolio_snapshot = portfolio_snapshot
                
                # Set position baselines
                for position in positions:
                    self._position_baselines[position.symbol] = position.market_value
            
            # Set price baselines
            for symbol in symbols:
                quote = await self._get_latest_quote(symbol)
                if quote:
                    mid_price = (quote.bid + quote.ask) / 2
                    self._price_baselines[symbol] = mid_price
                    self._volatility_cache[symbol] = []
            
            self.logger.info(f"Initialized baselines for {len(symbols)} symbols")
            
        except Exception as e:
            raise MonitoringError(f"Failed to initialize monitoring baselines: {e}")
    
    async def _monitoring_loop(self, symbols: List[str]) -> None:
        """Main monitoring loop that runs continuously."""
        while self.is_monitoring:
            try:
                await self._perform_monitoring_cycle(symbols)
                await asyncio.sleep(self.thresholds.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.thresholds.monitoring_interval)
    
    async def _perform_monitoring_cycle(self, symbols: List[str]) -> None:
        """Perform one complete monitoring cycle."""
        # Monitor portfolio-level changes
        await self._monitor_portfolio_changes()
        
        # Monitor position-level changes
        await self._monitor_position_changes()
        
        # Monitor price movements and volatility
        await self._monitor_market_conditions(symbols)
    
    async def _monitor_portfolio_changes(self) -> None:
        """Monitor portfolio-level changes and generate alerts."""
        try:
            positions = await self._get_current_positions()
            if not positions or not self._last_portfolio_snapshot:
                return
            
            current_snapshot = self.portfolio_analyzer.create_portfolio_snapshot(positions)
            
            # Check portfolio value change
            value_change = current_snapshot.total_value - self._last_portfolio_snapshot.total_value
            value_change_percent = float(value_change / self._last_portfolio_snapshot.total_value * 100)
            
            if abs(value_change_percent) >= self.thresholds.portfolio_change_percent:
                severity = AlertSeverity.WARNING if abs(value_change_percent) < 5.0 else AlertSeverity.CRITICAL
                await self._generate_alert(
                    alert_type="portfolio_value_change",
                    severity=severity,
                    message=f"Portfolio value changed by {value_change_percent:.2f}% (${value_change:,.2f})",
                    data={
                        "previous_value": float(self._last_portfolio_snapshot.total_value),
                        "current_value": float(current_snapshot.total_value),
                        "change_amount": float(value_change),
                        "change_percent": value_change_percent
                    }
                )
            
            # Check daily P&L threshold
            if abs(current_snapshot.day_pnl) >= self.thresholds.daily_pnl_threshold:
                severity = AlertSeverity.WARNING if current_snapshot.day_pnl > 0 else AlertSeverity.CRITICAL
                await self._generate_alert(
                    alert_type="daily_pnl_threshold",
                    severity=severity,
                    message=f"Daily P&L reached ${current_snapshot.day_pnl:,.2f}",
                    data={
                        "daily_pnl": float(current_snapshot.day_pnl),
                        "threshold": float(self.thresholds.daily_pnl_threshold)
                    }
                )
            
            # Check drawdown
            metrics = self.portfolio_analyzer.calculate_portfolio_metrics(positions)
            if "max_drawdown" in metrics and metrics["max_drawdown"] >= self.thresholds.drawdown_threshold:
                await self._generate_alert(
                    alert_type="drawdown_threshold",
                    severity=AlertSeverity.CRITICAL,
                    message=f"Portfolio drawdown reached {metrics['max_drawdown']:.2f}%",
                    data={
                        "drawdown_percent": metrics["max_drawdown"],
                        "threshold": self.thresholds.drawdown_threshold
                    }
                )
            
            self._last_portfolio_snapshot = current_snapshot
            
        except Exception as e:
            self.logger.error(f"Error monitoring portfolio changes: {e}")
    
    async def _monitor_position_changes(self) -> None:
        """Monitor individual position changes and generate alerts."""
        try:
            positions = await self._get_current_positions()
            if not positions:
                return
            
            for position in positions:
                if position.symbol not in self._position_baselines:
                    continue
                
                baseline_value = self._position_baselines[position.symbol]
                value_change = position.market_value - baseline_value
                value_change_percent = float(value_change / baseline_value * 100) if baseline_value != 0 else 0
                
                # Check position value change
                if (abs(value_change_percent) >= self.thresholds.position_change_percent or
                    abs(value_change) >= self.thresholds.position_change_amount):
                    
                    severity = AlertSeverity.INFO if abs(value_change_percent) < 10.0 else AlertSeverity.WARNING
                    await self._generate_alert(
                        alert_type="position_value_change",
                        severity=severity,
                        symbol=position.symbol,
                        message=f"{position.symbol} position changed by {value_change_percent:.2f}% (${value_change:,.2f})",
                        data={
                            "symbol": position.symbol,
                            "previous_value": float(baseline_value),
                            "current_value": float(position.market_value),
                            "change_amount": float(value_change),
                            "change_percent": value_change_percent,
                            "quantity": position.quantity
                        }
                    )
                
                # Update baseline for significant changes
                if abs(value_change_percent) >= self.thresholds.position_change_percent:
                    self._position_baselines[position.symbol] = position.market_value
            
        except Exception as e:
            self.logger.error(f"Error monitoring position changes: {e}")
    
    async def _monitor_market_conditions(self, symbols: List[str]) -> None:
        """Monitor market conditions including price movements and volatility."""
        for symbol in symbols:
            try:
                await self._monitor_price_movement(symbol)
                await self._monitor_volatility(symbol)
                
            except Exception as e:
                self.logger.error(f"Error monitoring market conditions for {symbol}: {e}")
    
    async def _monitor_price_movement(self, symbol: str) -> None:
        """Monitor price movements for a specific symbol."""
        try:
            quote = await self._get_latest_quote(symbol)
            if not quote or symbol not in self._price_baselines:
                return
            
            current_price = (quote.bid + quote.ask) / 2
            baseline_price = self._price_baselines[symbol]
            
            price_change_percent = float((current_price - baseline_price) / baseline_price * 100)
            
            if abs(price_change_percent) >= self.thresholds.price_movement_percent:
                severity = AlertSeverity.WARNING if abs(price_change_percent) < 15.0 else AlertSeverity.CRITICAL
                await self._generate_alert(
                    alert_type="price_movement",
                    severity=severity,
                    symbol=symbol,
                    message=f"{symbol} price moved {price_change_percent:.2f}% to ${current_price:.2f}",
                    data={
                        "symbol": symbol,
                        "previous_price": float(baseline_price),
                        "current_price": float(current_price),
                        "change_percent": price_change_percent,
                        "bid": float(quote.bid),
                        "ask": float(quote.ask)
                    }
                )
                
                # Update baseline for significant moves
                self._price_baselines[symbol] = current_price
            
        except Exception as e:
            self.logger.error(f"Error monitoring price movement for {symbol}: {e}")
    
    async def _monitor_volatility(self, symbol: str) -> None:
        """Monitor volatility for a specific symbol."""
        try:
            # Get recent price data for volatility calculation
            historical_data = await self._get_historical_prices(symbol, self.thresholds.volatility_window)
            if not historical_data or len(historical_data) < self.thresholds.volatility_window:
                return
            
            # Calculate volatility using technical analysis
            volatility = self.technical_analysis.calculate_volatility(historical_data)
            
            if volatility >= self.thresholds.volatility_threshold:
                await self._generate_alert(
                    alert_type="high_volatility",
                    severity=AlertSeverity.WARNING,
                    symbol=symbol,
                    message=f"{symbol} volatility reached {volatility:.1%} (annualized)",
                    data={
                        "symbol": symbol,
                        "volatility": volatility,
                        "threshold": self.thresholds.volatility_threshold,
                        "window_periods": self.thresholds.volatility_window
                    }
                )
            
        except Exception as e:
            self.logger.error(f"Error monitoring volatility for {symbol}: {e}")
    
    async def _generate_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        symbol: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Generate and dispatch a monitoring alert."""
        alert = MonitoringAlert(
            alert_id=f"{alert_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            severity=severity,
            alert_type=alert_type,
            symbol=symbol,
            message=message,
            data=data or {}
        )
        
        self.logger.info(f"Generated {severity.value} alert: {message}")
        
        # Dispatch to all registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    async def _get_current_positions(self) -> List[Position]:
        """Get current portfolio positions."""
        # This would typically integrate with the portfolio analyzer
        # For now, return empty list as placeholder
        return []
    
    async def _get_latest_quote(self, symbol: str) -> Optional[Quote]:
        """Get the latest quote for a symbol from the data cache."""
        try:
            quote_data = self.data_cache.get(f"quote:{symbol}")
            if quote_data:
                return Quote(**quote_data)
            return None
        except Exception as e:
            self.logger.error(f"Error getting quote for {symbol}: {e}")
            return None
    
    async def _get_historical_prices(self, symbol: str, periods: int) -> List[float]:
        """Get historical prices for volatility calculation."""
        try:
            # This would typically fetch from data store or cache
            # For now, return empty list as placeholder
            return []
        except Exception as e:
            self.logger.error(f"Error getting historical prices for {symbol}: {e}")
            return []
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status and statistics."""
        return {
            "is_monitoring": self.is_monitoring,
            "thresholds": {
                "position_change_percent": self.thresholds.position_change_percent,
                "portfolio_change_percent": self.thresholds.portfolio_change_percent,
                "volatility_threshold": self.thresholds.volatility_threshold,
                "monitoring_interval": self.thresholds.monitoring_interval
            },
            "monitored_symbols": list(self._price_baselines.keys()),
            "alert_callbacks_count": len(self.alert_callbacks),
            "last_portfolio_value": float(self._last_portfolio_snapshot.total_value) if self._last_portfolio_snapshot else None
        }