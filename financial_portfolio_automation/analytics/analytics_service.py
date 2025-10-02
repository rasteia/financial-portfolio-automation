"""
Analytics Service - Main interface for dashboard data preparation.

This module provides the primary interface for real-time analytics,
coordinating metrics calculation, trend analysis, and data aggregation
for dashboard consumption.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import logging
import threading
import time

from ..models.core import PortfolioSnapshot, Position
from ..data.store import DataStore
from ..data.cache import DataCache
from ..analysis.portfolio_analyzer import PortfolioAnalyzer
from ..monitoring.portfolio_monitor import PortfolioMonitor
from .metrics_calculator import MetricsCalculator
from .trend_analyzer import TrendAnalyzer
from .data_aggregator import DataAggregator
from .dashboard_serializer import DashboardSerializer


@dataclass
class AnalyticsConfig:
    """Configuration for analytics service."""
    refresh_interval_seconds: int = 30
    cache_ttl_seconds: int = 300
    enable_real_time: bool = True
    max_historical_days: int = 365
    benchmark_symbol: str = 'SPY'


@dataclass
class DashboardMetrics:
    """Real-time dashboard metrics."""
    timestamp: datetime
    portfolio_value: Decimal
    day_pnl: Decimal
    day_pnl_pct: Decimal
    total_pnl: Decimal
    total_pnl_pct: Decimal
    buying_power: Decimal
    positions_count: int
    top_gainers: List[Dict[str, Any]]
    top_losers: List[Dict[str, Any]]
    sector_allocation: Dict[str, Decimal]
    risk_metrics: Dict[str, Decimal]


class AnalyticsService:
    """
    Main analytics service for dashboard data preparation.
    
    Coordinates real-time metrics calculation, historical trend analysis,
    and data aggregation for web dashboard consumption.
    """
    
    def __init__(
        self,
        data_store: DataStore,
        data_cache: DataCache,
        portfolio_analyzer: PortfolioAnalyzer,
        portfolio_monitor: Optional[PortfolioMonitor] = None,
        config: Optional[AnalyticsConfig] = None
    ):
        """
        Initialize analytics service.
        
        Args:
            data_store: Data storage interface
            data_cache: Data caching system
            portfolio_analyzer: Portfolio analysis engine
            portfolio_monitor: Portfolio monitoring system
            config: Analytics configuration
        """
        self.data_store = data_store
        self.data_cache = data_cache
        self.portfolio_analyzer = portfolio_analyzer
        self.portfolio_monitor = portfolio_monitor
        self.config = config or AnalyticsConfig()
        
        # Initialize components
        self.metrics_calculator = MetricsCalculator(
            data_store, portfolio_analyzer
        )
        self.trend_analyzer = TrendAnalyzer(data_store)
        self.data_aggregator = DataAggregator(data_store)
        self.dashboard_serializer = DashboardSerializer()
        
        self.logger = logging.getLogger(__name__)
        
        # Real-time update thread
        self._update_thread = None
        self._stop_event = threading.Event()
        self._last_update = None
        
        # Cached metrics
        self._cached_metrics: Optional[DashboardMetrics] = None
        self._cache_timestamp: Optional[datetime] = None
    
    def start_real_time_updates(self) -> None:
        """Start real-time metrics updates."""
        if not self.config.enable_real_time:
            return
        
        if self._update_thread and self._update_thread.is_alive():
            self.logger.warning("Real-time updates already running")
            return
        
        self._stop_event.clear()
        self._update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True
        )
        self._update_thread.start()
        
        self.logger.info("Started real-time analytics updates")
    
    def stop_real_time_updates(self) -> None:
        """Stop real-time metrics updates."""
        if self._update_thread and self._update_thread.is_alive():
            self._stop_event.set()
            self._update_thread.join(timeout=5)
            
        self.logger.info("Stopped real-time analytics updates")
    
    def get_dashboard_data(
        self,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data.
        
        Args:
            force_refresh: Force refresh of cached data
            
        Returns:
            Dictionary containing all dashboard data
        """
        try:
            # Check cache first
            if not force_refresh and self._is_cache_valid():
                cached_data = self.data_cache.get('dashboard_data')
                if cached_data:
                    return cached_data
            
            self.logger.info("Generating fresh dashboard data")
            
            # Get real-time metrics
            metrics = self.get_real_time_metrics()
            
            # Get historical trends
            trends = self.get_historical_trends()
            
            # Get performance summary
            performance = self.get_performance_summary()
            
            # Get risk analysis
            risk_analysis = self.get_risk_analysis()
            
            # Get market comparison
            market_comparison = self.get_market_comparison()
            
            # Serialize for dashboard
            dashboard_data = self.dashboard_serializer.serialize_dashboard_data({
                'timestamp': datetime.now(),
                'real_time_metrics': metrics,
                'historical_trends': trends,
                'performance_summary': performance,
                'risk_analysis': risk_analysis,
                'market_comparison': market_comparison
            })
            
            # Cache the data
            self.data_cache.set(
                'dashboard_data',
                dashboard_data,
                ttl=self.config.cache_ttl_seconds
            )
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error generating dashboard data: {e}")
            raise
    
    def get_real_time_metrics(self) -> DashboardMetrics:
        """
        Get real-time portfolio metrics.
        
        Returns:
            Current dashboard metrics
        """
        # Check cached metrics
        if self._is_metrics_cache_valid():
            return self._cached_metrics
        
        # Get current portfolio snapshot
        current_snapshot = self._get_current_snapshot()
        
        if not current_snapshot:
            raise ValueError("No current portfolio data available")
        
        # Calculate metrics
        metrics = self.metrics_calculator.calculate_real_time_metrics(
            current_snapshot
        )
        
        # Get top gainers/losers
        top_gainers, top_losers = self._get_top_movers(current_snapshot)
        
        # Get sector allocation
        sector_allocation = self._get_sector_allocation(current_snapshot)
        
        # Get risk metrics
        risk_metrics = self.metrics_calculator.calculate_risk_metrics(
            current_snapshot
        )
        
        # Create dashboard metrics
        dashboard_metrics = DashboardMetrics(
            timestamp=current_snapshot.timestamp,
            portfolio_value=current_snapshot.total_value,
            day_pnl=current_snapshot.day_pnl,
            day_pnl_pct=self._calculate_pnl_percentage(
                current_snapshot.day_pnl,
                current_snapshot.total_value
            ),
            total_pnl=current_snapshot.total_pnl,
            total_pnl_pct=self._calculate_total_pnl_percentage(current_snapshot),
            buying_power=current_snapshot.buying_power,
            positions_count=len(current_snapshot.positions),
            top_gainers=top_gainers,
            top_losers=top_losers,
            sector_allocation=sector_allocation,
            risk_metrics=risk_metrics
        )
        
        # Cache metrics
        self._cached_metrics = dashboard_metrics
        self._cache_timestamp = datetime.now()
        
        return dashboard_metrics
    
    def get_historical_trends(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get historical trend analysis.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Historical trend data
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Get portfolio snapshots
        snapshots = self.data_store.get_portfolio_snapshots(
            start_date=start_date,
            end_date=end_date
        )
        
        if not snapshots:
            return {}
        
        # Analyze trends
        trends = self.trend_analyzer.analyze_trends(snapshots)
        
        return trends
    
    def get_performance_summary(
        self,
        periods: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Get performance summary for multiple periods.
        
        Args:
            periods: List of days for each period (default: [1, 7, 30, 90, 365])
            
        Returns:
            Performance summary data
        """
        if periods is None:
            periods = [1, 7, 30, 90, 365]
        
        performance_data = {}
        
        for period_days in periods:
            try:
                end_date = date.today()
                start_date = end_date - timedelta(days=period_days)
                
                snapshots = self.data_store.get_portfolio_snapshots(
                    start_date=start_date,
                    end_date=end_date
                )
                
                if len(snapshots) >= 2:
                    period_performance = self.metrics_calculator.calculate_period_performance(
                        snapshots[0], snapshots[-1], period_days
                    )
                    performance_data[f"{period_days}d"] = period_performance
                    
            except Exception as e:
                self.logger.warning(f"Error calculating {period_days}d performance: {e}")
        
        return performance_data
    
    def get_risk_analysis(self) -> Dict[str, Any]:
        """
        Get current risk analysis.
        
        Returns:
            Risk analysis data
        """
        try:
            # Get recent snapshots for risk calculation
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            snapshots = self.data_store.get_portfolio_snapshots(
                start_date=start_date,
                end_date=end_date
            )
            
            if not snapshots:
                return {}
            
            # Calculate risk metrics
            risk_analysis = self.metrics_calculator.calculate_comprehensive_risk_metrics(
                snapshots
            )
            
            return risk_analysis
            
        except Exception as e:
            self.logger.error(f"Error calculating risk analysis: {e}")
            return {}
    
    def get_market_comparison(self) -> Dict[str, Any]:
        """
        Get market comparison data.
        
        Returns:
            Market comparison data
        """
        try:
            # Get portfolio performance
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            snapshots = self.data_store.get_portfolio_snapshots(
                start_date=start_date,
                end_date=end_date
            )
            
            if len(snapshots) < 2:
                return {}
            
            portfolio_return = self._calculate_return_percentage(
                snapshots[0].total_value,
                snapshots[-1].total_value
            )
            
            # Get benchmark data (simplified - would need actual market data)
            benchmark_return = self._get_benchmark_return(
                self.config.benchmark_symbol,
                start_date,
                end_date
            )
            
            return {
                'portfolio_return': float(portfolio_return),
                'benchmark_return': float(benchmark_return) if benchmark_return else None,
                'excess_return': float(portfolio_return - benchmark_return) if benchmark_return else None,
                'benchmark_symbol': self.config.benchmark_symbol
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating market comparison: {e}")
            return {}
    
    def get_aggregated_data(
        self,
        timeframe: str = 'daily',
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get aggregated data for charts and analysis.
        
        Args:
            timeframe: Aggregation timeframe ('daily', 'hourly')
            days: Number of days to aggregate
            
        Returns:
            Aggregated data
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        return self.data_aggregator.aggregate_data(
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe
        )
    
    def _update_loop(self) -> None:
        """Real-time update loop."""
        while not self._stop_event.is_set():
            try:
                # Update cached metrics
                self.get_real_time_metrics()
                
                # Update dashboard data cache
                self.get_dashboard_data(force_refresh=True)
                
                self._last_update = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Error in update loop: {e}")
            
            # Wait for next update
            self._stop_event.wait(self.config.refresh_interval_seconds)
    
    def _get_current_snapshot(self) -> Optional[PortfolioSnapshot]:
        """Get the most recent portfolio snapshot."""
        snapshots = self.data_store.get_portfolio_snapshots(
            start_date=date.today() - timedelta(days=1),
            end_date=date.today()
        )
        
        return snapshots[-1] if snapshots else None
    
    def _get_top_movers(
        self, 
        snapshot: PortfolioSnapshot
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get top gaining and losing positions."""
        positions_with_pnl = [
            {
                'symbol': pos.symbol,
                'day_pnl': float(pos.day_pnl),
                'day_pnl_pct': float(pos.day_pnl / pos.market_value * 100) if pos.market_value > 0 else 0,
                'market_value': float(pos.market_value)
            }
            for pos in snapshot.positions
            if pos.day_pnl != 0
        ]
        
        # Sort by day P&L percentage
        sorted_positions = sorted(
            positions_with_pnl,
            key=lambda x: x['day_pnl_pct'],
            reverse=True
        )
        
        # Top 5 gainers and losers
        top_gainers = sorted_positions[:5]
        top_losers = sorted_positions[-5:]
        
        return top_gainers, top_losers
    
    def _get_sector_allocation(
        self, 
        snapshot: PortfolioSnapshot
    ) -> Dict[str, Decimal]:
        """Get sector allocation breakdown."""
        sector_values = {}
        total_value = snapshot.total_value
        
        for position in snapshot.positions:
            # Simplified sector mapping (would need actual sector data)
            sector = self._get_position_sector(position.symbol)
            
            if sector not in sector_values:
                sector_values[sector] = Decimal('0')
            
            sector_values[sector] += position.market_value
        
        # Convert to percentages
        sector_allocation = {
            sector: (value / total_value * 100) if total_value > 0 else Decimal('0')
            for sector, value in sector_values.items()
        }
        
        return sector_allocation
    
    def _get_position_sector(self, symbol: str) -> str:
        """Get sector for a position symbol."""
        # Simplified sector mapping
        tech_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
        finance_symbols = ['JPM', 'BAC', 'WFC', 'GS']
        
        if symbol in tech_symbols:
            return 'Technology'
        elif symbol in finance_symbols:
            return 'Financial'
        else:
            return 'Other'
    
    def _calculate_pnl_percentage(
        self, 
        pnl: Decimal, 
        total_value: Decimal
    ) -> Decimal:
        """Calculate P&L as percentage of total value."""
        if total_value <= 0:
            return Decimal('0')
        
        return pnl / total_value * 100
    
    def _calculate_total_pnl_percentage(
        self, 
        snapshot: PortfolioSnapshot
    ) -> Decimal:
        """Calculate total P&L percentage."""
        initial_value = snapshot.total_value - snapshot.total_pnl
        
        if initial_value <= 0:
            return Decimal('0')
        
        return snapshot.total_pnl / initial_value * 100
    
    def _calculate_return_percentage(
        self, 
        start_value: Decimal, 
        end_value: Decimal
    ) -> Decimal:
        """Calculate return percentage between two values."""
        if start_value <= 0:
            return Decimal('0')
        
        return (end_value - start_value) / start_value * 100
    
    def _get_benchmark_return(
        self, 
        symbol: str, 
        start_date: date, 
        end_date: date
    ) -> Optional[Decimal]:
        """Get benchmark return for comparison."""
        # Simplified - would need actual market data integration
        # For now, return a mock value
        return Decimal('2.5')  # 2.5% mock return
    
    def _is_cache_valid(self) -> bool:
        """Check if dashboard data cache is valid."""
        cache_key = 'dashboard_data_timestamp'
        last_cache_time = self.data_cache.get(cache_key)
        
        if not last_cache_time:
            return False
        
        cache_age = (datetime.now() - last_cache_time).total_seconds()
        return cache_age < self.config.cache_ttl_seconds
    
    def _is_metrics_cache_valid(self) -> bool:
        """Check if metrics cache is valid."""
        if not self._cached_metrics or not self._cache_timestamp:
            return False
        
        cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
        return cache_age < self.config.refresh_interval_seconds