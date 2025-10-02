"""
Data Aggregator for multi-timeframe data aggregation.

This module aggregates portfolio data across different timeframes
for efficient dashboard consumption and analysis.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging

from ..models.core import PortfolioSnapshot
from ..data.store import DataStore


@dataclass
class AggregatedDataPoint:
    """Single aggregated data point."""
    timestamp: datetime
    open_value: Decimal
    high_value: Decimal
    low_value: Decimal
    close_value: Decimal
    volume: Decimal  # Total transaction volume for period
    pnl: Decimal
    positions_count: int


class DataAggregator:
    """
    Data aggregator for multi-timeframe portfolio data.
    
    Aggregates portfolio snapshots into different timeframes
    for efficient dashboard consumption and chart display.
    """
    
    def __init__(self, data_store: DataStore):
        """
        Initialize data aggregator.
        
        Args:
            data_store: Data storage interface
        """
        self.data_store = data_store
        self.logger = logging.getLogger(__name__)
    
    def aggregate_data(
        self,
        start_date: date,
        end_date: date,
        timeframe: str = 'daily'
    ) -> Dict[str, Any]:
        """
        Aggregate portfolio data for the specified timeframe.
        
        Args:
            start_date: Start date for aggregation
            end_date: End date for aggregation
            timeframe: Aggregation timeframe ('hourly', 'daily', 'weekly', 'monthly')
            
        Returns:
            Aggregated data dictionary
        """
        try:
            # Get raw portfolio snapshots
            snapshots = self.data_store.get_portfolio_snapshots(
                start_date=start_date,
                end_date=end_date
            )
            
            if not snapshots:
                return self._empty_aggregation_result(start_date, end_date, timeframe)
            
            # Aggregate based on timeframe
            if timeframe == 'hourly':
                aggregated_points = self._aggregate_hourly(snapshots)
            elif timeframe == 'daily':
                aggregated_points = self._aggregate_daily(snapshots)
            elif timeframe == 'weekly':
                aggregated_points = self._aggregate_weekly(snapshots)
            elif timeframe == 'monthly':
                aggregated_points = self._aggregate_monthly(snapshots)
            else:
                raise ValueError(f"Unsupported timeframe: {timeframe}")
            
            # Calculate additional metrics
            summary_metrics = self._calculate_summary_metrics(aggregated_points)
            
            # Prepare chart data
            chart_data = self._prepare_chart_data(aggregated_points)
            
            return {
                'timeframe': timeframe,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'data_points': len(aggregated_points),
                'aggregated_data': [self._serialize_data_point(dp) for dp in aggregated_points],
                'summary_metrics': summary_metrics,
                'chart_data': chart_data
            }
            
        except Exception as e:
            self.logger.error(f"Error aggregating data: {e}")
            return self._empty_aggregation_result(start_date, end_date, timeframe)
    
    def aggregate_performance_data(
        self,
        start_date: date,
        end_date: date,
        timeframe: str = 'daily'
    ) -> Dict[str, Any]:
        """
        Aggregate performance-specific data.
        
        Args:
            start_date: Start date for aggregation
            end_date: End date for aggregation
            timeframe: Aggregation timeframe
            
        Returns:
            Performance aggregation data
        """
        base_aggregation = self.aggregate_data(start_date, end_date, timeframe)
        
        if not base_aggregation.get('aggregated_data'):
            return base_aggregation
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(
            base_aggregation['aggregated_data']
        )
        
        # Calculate rolling metrics
        rolling_metrics = self._calculate_rolling_metrics(
            base_aggregation['aggregated_data']
        )
        
        base_aggregation.update({
            'performance_metrics': performance_metrics,
            'rolling_metrics': rolling_metrics
        })
        
        return base_aggregation
    
    def aggregate_risk_data(
        self,
        start_date: date,
        end_date: date,
        window_size: int = 30
    ) -> Dict[str, Any]:
        """
        Aggregate risk-specific data with rolling windows.
        
        Args:
            start_date: Start date for aggregation
            end_date: End date for aggregation
            window_size: Rolling window size in days
            
        Returns:
            Risk aggregation data
        """
        # Get daily aggregation first
        daily_data = self.aggregate_data(start_date, end_date, 'daily')
        
        if not daily_data.get('aggregated_data'):
            return daily_data
        
        # Calculate rolling risk metrics
        risk_metrics = self._calculate_rolling_risk_metrics(
            daily_data['aggregated_data'],
            window_size
        )
        
        daily_data.update({
            'risk_metrics': risk_metrics,
            'window_size': window_size
        })
        
        return daily_data
    
    def _aggregate_hourly(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> List[AggregatedDataPoint]:
        """Aggregate snapshots by hour."""
        hourly_groups = {}
        
        for snapshot in snapshots:
            # Group by date and hour
            hour_key = snapshot.timestamp.replace(minute=0, second=0, microsecond=0)
            
            if hour_key not in hourly_groups:
                hourly_groups[hour_key] = []
            
            hourly_groups[hour_key].append(snapshot)
        
        # Create aggregated points
        aggregated_points = []
        for hour_key, hour_snapshots in sorted(hourly_groups.items()):
            aggregated_point = self._create_aggregated_point(hour_key, hour_snapshots)
            aggregated_points.append(aggregated_point)
        
        return aggregated_points
    
    def _aggregate_daily(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> List[AggregatedDataPoint]:
        """Aggregate snapshots by day."""
        daily_groups = {}
        
        for snapshot in snapshots:
            # Group by date
            date_key = snapshot.timestamp.date()
            
            if date_key not in daily_groups:
                daily_groups[date_key] = []
            
            daily_groups[date_key].append(snapshot)
        
        # Create aggregated points
        aggregated_points = []
        for date_key, day_snapshots in sorted(daily_groups.items()):
            # Use end of day timestamp
            timestamp = datetime.combine(date_key, datetime.min.time().replace(hour=23, minute=59))
            aggregated_point = self._create_aggregated_point(timestamp, day_snapshots)
            aggregated_points.append(aggregated_point)
        
        return aggregated_points
    
    def _aggregate_weekly(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> List[AggregatedDataPoint]:
        """Aggregate snapshots by week."""
        weekly_groups = {}
        
        for snapshot in snapshots:
            # Group by week (Monday as start of week)
            date = snapshot.timestamp.date()
            week_start = date - timedelta(days=date.weekday())
            
            if week_start not in weekly_groups:
                weekly_groups[week_start] = []
            
            weekly_groups[week_start].append(snapshot)
        
        # Create aggregated points
        aggregated_points = []
        for week_start, week_snapshots in sorted(weekly_groups.items()):
            # Use end of week timestamp
            week_end = week_start + timedelta(days=6)
            timestamp = datetime.combine(week_end, datetime.min.time().replace(hour=23, minute=59))
            aggregated_point = self._create_aggregated_point(timestamp, week_snapshots)
            aggregated_points.append(aggregated_point)
        
        return aggregated_points
    
    def _aggregate_monthly(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> List[AggregatedDataPoint]:
        """Aggregate snapshots by month."""
        monthly_groups = {}
        
        for snapshot in snapshots:
            # Group by year and month
            date = snapshot.timestamp.date()
            month_key = date.replace(day=1)
            
            if month_key not in monthly_groups:
                monthly_groups[month_key] = []
            
            monthly_groups[month_key].append(snapshot)
        
        # Create aggregated points
        aggregated_points = []
        for month_key, month_snapshots in sorted(monthly_groups.items()):
            # Use end of month timestamp
            if month_key.month == 12:
                next_month = month_key.replace(year=month_key.year + 1, month=1)
            else:
                next_month = month_key.replace(month=month_key.month + 1)
            
            month_end = next_month - timedelta(days=1)
            timestamp = datetime.combine(month_end, datetime.min.time().replace(hour=23, minute=59))
            aggregated_point = self._create_aggregated_point(timestamp, month_snapshots)
            aggregated_points.append(aggregated_point)
        
        return aggregated_points
    
    def _create_aggregated_point(
        self,
        timestamp: datetime,
        snapshots: List[PortfolioSnapshot]
    ) -> AggregatedDataPoint:
        """Create an aggregated data point from a group of snapshots."""
        if not snapshots:
            raise ValueError("Cannot create aggregated point from empty snapshots")
        
        # Sort snapshots by timestamp
        sorted_snapshots = sorted(snapshots, key=lambda s: s.timestamp)
        
        # OHLC values
        open_value = sorted_snapshots[0].total_value
        close_value = sorted_snapshots[-1].total_value
        
        values = [s.total_value for s in sorted_snapshots]
        high_value = max(values)
        low_value = min(values)
        
        # Calculate total P&L for the period
        pnl = close_value - open_value
        
        # Calculate average positions count
        avg_positions = sum(len(s.positions) for s in sorted_snapshots) / len(sorted_snapshots)
        
        # Estimate volume (simplified - would need actual transaction data)
        volume = sum(abs(s.day_pnl) for s in sorted_snapshots)
        
        return AggregatedDataPoint(
            timestamp=timestamp,
            open_value=open_value,
            high_value=high_value,
            low_value=low_value,
            close_value=close_value,
            volume=volume,
            pnl=pnl,
            positions_count=int(avg_positions)
        )
    
    def _calculate_summary_metrics(
        self, 
        aggregated_points: List[AggregatedDataPoint]
    ) -> Dict[str, Any]:
        """Calculate summary metrics from aggregated data."""
        if not aggregated_points:
            return {}
        
        # Basic metrics
        start_value = aggregated_points[0].open_value
        end_value = aggregated_points[-1].close_value
        total_return = end_value - start_value
        total_return_pct = (total_return / start_value * 100) if start_value > 0 else 0
        
        # High/Low metrics
        all_highs = [dp.high_value for dp in aggregated_points]
        all_lows = [dp.low_value for dp in aggregated_points]
        period_high = max(all_highs)
        period_low = min(all_lows)
        
        # Volume metrics
        total_volume = sum(dp.volume for dp in aggregated_points)
        avg_volume = total_volume / len(aggregated_points)
        
        # P&L metrics
        total_pnl = sum(dp.pnl for dp in aggregated_points)
        positive_periods = sum(1 for dp in aggregated_points if dp.pnl > 0)
        win_rate = positive_periods / len(aggregated_points) * 100
        
        return {
            'start_value': float(start_value),
            'end_value': float(end_value),
            'total_return': float(total_return),
            'total_return_pct': float(total_return_pct),
            'period_high': float(period_high),
            'period_low': float(period_low),
            'total_volume': float(total_volume),
            'avg_volume': float(avg_volume),
            'total_pnl': float(total_pnl),
            'win_rate_pct': win_rate,
            'total_periods': len(aggregated_points)
        }
    
    def _prepare_chart_data(
        self, 
        aggregated_points: List[AggregatedDataPoint]
    ) -> Dict[str, Any]:
        """Prepare data for chart consumption."""
        if not aggregated_points:
            return {}
        
        timestamps = [dp.timestamp.isoformat() for dp in aggregated_points]
        
        # OHLC data
        ohlc_data = [
            {
                'timestamp': dp.timestamp.isoformat(),
                'open': float(dp.open_value),
                'high': float(dp.high_value),
                'low': float(dp.low_value),
                'close': float(dp.close_value),
                'volume': float(dp.volume)
            }
            for dp in aggregated_points
        ]
        
        # Line chart data (closing values)
        line_data = {
            'timestamps': timestamps,
            'values': [float(dp.close_value) for dp in aggregated_points]
        }
        
        # Volume chart data
        volume_data = {
            'timestamps': timestamps,
            'volumes': [float(dp.volume) for dp in aggregated_points]
        }
        
        # P&L chart data
        pnl_data = {
            'timestamps': timestamps,
            'pnl_values': [float(dp.pnl) for dp in aggregated_points]
        }
        
        return {
            'ohlc_data': ohlc_data,
            'line_data': line_data,
            'volume_data': volume_data,
            'pnl_data': pnl_data
        }
    
    def _calculate_performance_metrics(
        self, 
        aggregated_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate performance metrics from aggregated data."""
        if len(aggregated_data) < 2:
            return {}
        
        # Calculate period returns
        returns = []
        for i in range(1, len(aggregated_data)):
            prev_close = aggregated_data[i-1]['close_value']
            curr_close = aggregated_data[i]['close_value']
            
            if prev_close > 0:
                period_return = (curr_close - prev_close) / prev_close
                returns.append(period_return)
        
        if not returns:
            return {}
        
        # Calculate metrics
        avg_return = sum(returns) / len(returns)
        
        # Calculate volatility
        if len(returns) > 1:
            variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
            volatility = variance ** 0.5
        else:
            volatility = 0
        
        # Calculate Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = avg_return / volatility if volatility > 0 else 0
        
        # Calculate maximum drawdown
        max_drawdown = self._calculate_max_drawdown_from_data(aggregated_data)
        
        return {
            'avg_period_return': avg_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown,
            'total_periods': len(returns)
        }
    
    def _calculate_rolling_metrics(
        self, 
        aggregated_data: List[Dict[str, Any]],
        window_size: int = 20
    ) -> Dict[str, Any]:
        """Calculate rolling metrics."""
        if len(aggregated_data) < window_size:
            return {}
        
        rolling_returns = []
        rolling_volatilities = []
        
        for i in range(window_size, len(aggregated_data)):
            window_data = aggregated_data[i-window_size:i]
            
            # Calculate returns for window
            window_returns = []
            for j in range(1, len(window_data)):
                prev_close = window_data[j-1]['close_value']
                curr_close = window_data[j]['close_value']
                
                if prev_close > 0:
                    ret = (curr_close - prev_close) / prev_close
                    window_returns.append(ret)
            
            if window_returns:
                avg_return = sum(window_returns) / len(window_returns)
                rolling_returns.append(avg_return)
                
                if len(window_returns) > 1:
                    variance = sum((r - avg_return) ** 2 for r in window_returns) / (len(window_returns) - 1)
                    volatility = variance ** 0.5
                    rolling_volatilities.append(volatility)
        
        return {
            'rolling_returns': rolling_returns,
            'rolling_volatilities': rolling_volatilities,
            'window_size': window_size
        }
    
    def _calculate_rolling_risk_metrics(
        self, 
        aggregated_data: List[Dict[str, Any]],
        window_size: int
    ) -> Dict[str, Any]:
        """Calculate rolling risk metrics."""
        if len(aggregated_data) < window_size:
            return {}
        
        rolling_var_95 = []
        rolling_var_99 = []
        rolling_max_dd = []
        
        for i in range(window_size, len(aggregated_data)):
            window_data = aggregated_data[i-window_size:i]
            
            # Calculate returns for window
            window_returns = []
            for j in range(1, len(window_data)):
                prev_close = window_data[j-1]['close_value']
                curr_close = window_data[j]['close_value']
                
                if prev_close > 0:
                    ret = (curr_close - prev_close) / prev_close
                    window_returns.append(ret)
            
            if window_returns:
                # Calculate VaR
                sorted_returns = sorted(window_returns)
                
                var_95_idx = int(0.05 * len(sorted_returns))
                var_99_idx = int(0.01 * len(sorted_returns))
                
                if var_95_idx < len(sorted_returns):
                    rolling_var_95.append(sorted_returns[var_95_idx] * 100)
                
                if var_99_idx < len(sorted_returns):
                    rolling_var_99.append(sorted_returns[var_99_idx] * 100)
                
                # Calculate max drawdown for window
                window_max_dd = self._calculate_max_drawdown_from_data(window_data)
                rolling_max_dd.append(window_max_dd)
        
        return {
            'rolling_var_95': rolling_var_95,
            'rolling_var_99': rolling_var_99,
            'rolling_max_drawdown': rolling_max_dd,
            'window_size': window_size
        }
    
    def _calculate_max_drawdown_from_data(
        self, 
        aggregated_data: List[Dict[str, Any]]
    ) -> float:
        """Calculate maximum drawdown from aggregated data."""
        if not aggregated_data:
            return 0
        
        values = [dp['close_value'] for dp in aggregated_data]
        
        max_drawdown = 0
        peak = values[0]
        
        for value in values:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown * 100
    
    def _serialize_data_point(self, dp: AggregatedDataPoint) -> Dict[str, Any]:
        """Serialize aggregated data point to dictionary."""
        return {
            'timestamp': dp.timestamp.isoformat(),
            'open_value': float(dp.open_value),
            'high_value': float(dp.high_value),
            'low_value': float(dp.low_value),
            'close_value': float(dp.close_value),
            'volume': float(dp.volume),
            'pnl': float(dp.pnl),
            'positions_count': dp.positions_count
        }
    
    def _empty_aggregation_result(
        self, 
        start_date: date, 
        end_date: date, 
        timeframe: str
    ) -> Dict[str, Any]:
        """Return empty aggregation result."""
        return {
            'timeframe': timeframe,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'data_points': 0,
            'aggregated_data': [],
            'summary_metrics': {},
            'chart_data': {}
        }