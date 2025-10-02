"""
Dashboard Serializer for web dashboard data formatting.

This module serializes analytics data into formats optimized
for web dashboard consumption and real-time updates.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
import json
import logging

from ..models.core import PortfolioSnapshot, Position


class DashboardSerializer:
    """
    Serializer for dashboard data formatting.
    
    Converts analytics data into JSON-serializable formats
    optimized for web dashboard consumption.
    """
    
    def __init__(self):
        """Initialize dashboard serializer."""
        self.logger = logging.getLogger(__name__)
    
    def serialize_dashboard_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize complete dashboard data.
        
        Args:
            data: Raw dashboard data dictionary
            
        Returns:
            Serialized dashboard data
        """
        try:
            serialized = {
                'timestamp': self._serialize_datetime(data.get('timestamp')),
                'real_time_metrics': self._serialize_real_time_metrics(
                    data.get('real_time_metrics')
                ),
                'historical_trends': self._serialize_historical_trends(
                    data.get('historical_trends')
                ),
                'performance_summary': self._serialize_performance_summary(
                    data.get('performance_summary')
                ),
                'risk_analysis': self._serialize_risk_analysis(
                    data.get('risk_analysis')
                ),
                'market_comparison': self._serialize_market_comparison(
                    data.get('market_comparison')
                )
            }
            
            # Add metadata
            serialized['metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'data_version': '1.0',
                'refresh_interval': 30  # seconds
            }
            
            return serialized
            
        except Exception as e:
            self.logger.error(f"Error serializing dashboard data: {e}")
            return self._empty_dashboard_data()
    
    def serialize_real_time_metrics(
        self, 
        metrics: Any
    ) -> Dict[str, Any]:
        """
        Serialize real-time metrics for dashboard.
        
        Args:
            metrics: Real-time metrics object or dictionary
            
        Returns:
            Serialized real-time metrics
        """
        if not metrics:
            return {}
        
        return self._serialize_real_time_metrics(metrics)
    
    def serialize_chart_data(
        self, 
        chart_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Serialize chart data for dashboard consumption.
        
        Args:
            chart_data: Raw chart data
            
        Returns:
            Serialized chart data
        """
        if not chart_data:
            return {}
        
        serialized_charts = {}
        
        for chart_name, chart_info in chart_data.items():
            if isinstance(chart_info, dict):
                serialized_charts[chart_name] = self._serialize_chart_series(chart_info)
            else:
                serialized_charts[chart_name] = self._serialize_value(chart_info)
        
        return serialized_charts
    
    def serialize_portfolio_snapshot(
        self, 
        snapshot: PortfolioSnapshot
    ) -> Dict[str, Any]:
        """
        Serialize portfolio snapshot for dashboard.
        
        Args:
            snapshot: Portfolio snapshot
            
        Returns:
            Serialized snapshot data
        """
        return {
            'timestamp': self._serialize_datetime(snapshot.timestamp),
            'total_value': self._serialize_decimal(snapshot.total_value),
            'buying_power': self._serialize_decimal(snapshot.buying_power),
            'day_pnl': self._serialize_decimal(snapshot.day_pnl),
            'total_pnl': self._serialize_decimal(snapshot.total_pnl),
            'positions': [
                self._serialize_position(pos) for pos in snapshot.positions
            ],
            'positions_count': len(snapshot.positions)
        }
    
    def serialize_positions_summary(
        self, 
        positions: List[Position]
    ) -> List[Dict[str, Any]]:
        """
        Serialize positions for dashboard display.
        
        Args:
            positions: List of positions
            
        Returns:
            Serialized positions data
        """
        return [self._serialize_position(pos) for pos in positions]
    
    def serialize_performance_data(
        self, 
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Serialize performance data for dashboard.
        
        Args:
            performance_data: Raw performance data
            
        Returns:
            Serialized performance data
        """
        if not performance_data:
            return {}
        
        serialized = {}
        
        for key, value in performance_data.items():
            if isinstance(value, dict):
                serialized[key] = self.serialize_performance_data(value)
            elif isinstance(value, list):
                serialized[key] = [self._serialize_value(item) for item in value]
            else:
                serialized[key] = self._serialize_value(value)
        
        return serialized
    
    def _serialize_real_time_metrics(self, metrics: Any) -> Dict[str, Any]:
        """Serialize real-time metrics."""
        if not metrics:
            return {}
        
        # Handle both object and dictionary formats
        if hasattr(metrics, '__dict__'):
            metrics_dict = metrics.__dict__
        else:
            metrics_dict = metrics
        
        serialized = {}
        
        for key, value in metrics_dict.items():
            if key == 'timestamp':
                serialized[key] = self._serialize_datetime(value)
            elif key in ['top_gainers', 'top_losers']:
                serialized[key] = [self._serialize_position_summary(pos) for pos in value] if value else []
            elif key == 'sector_allocation':
                serialized[key] = {
                    sector: self._serialize_decimal(allocation) 
                    for sector, allocation in value.items()
                } if value else {}
            elif key == 'risk_metrics':
                serialized[key] = {
                    metric: self._serialize_decimal(val) 
                    for metric, val in value.items()
                } if value else {}
            else:
                serialized[key] = self._serialize_value(value)
        
        return serialized
    
    def _serialize_historical_trends(self, trends: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize historical trends data."""
        if not trends:
            return {}
        
        serialized = {}
        
        for key, value in trends.items():
            if isinstance(value, dict):
                serialized[key] = self._serialize_nested_dict(value)
            elif isinstance(value, list):
                serialized[key] = [self._serialize_value(item) for item in value]
            else:
                serialized[key] = self._serialize_value(value)
        
        return serialized
    
    def _serialize_performance_summary(self, performance: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize performance summary data."""
        if not performance:
            return {}
        
        serialized = {}
        
        for period, data in performance.items():
            if isinstance(data, dict):
                serialized[period] = self._serialize_nested_dict(data)
            else:
                serialized[period] = self._serialize_value(data)
        
        return serialized
    
    def _serialize_risk_analysis(self, risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize risk analysis data."""
        if not risk_data:
            return {}
        
        return self._serialize_nested_dict(risk_data)
    
    def _serialize_market_comparison(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize market comparison data."""
        if not comparison:
            return {}
        
        return self._serialize_nested_dict(comparison)
    
    def _serialize_position(self, position: Position) -> Dict[str, Any]:
        """Serialize a single position."""
        return {
            'symbol': position.symbol,
            'quantity': self._serialize_decimal(position.quantity),
            'market_value': self._serialize_decimal(position.market_value),
            'cost_basis': self._serialize_decimal(position.cost_basis),
            'unrealized_pnl': self._serialize_decimal(position.unrealized_pnl),
            'day_pnl': self._serialize_decimal(position.day_pnl),
            'unrealized_pnl_pct': self._calculate_percentage(
                position.unrealized_pnl, position.cost_basis
            ),
            'day_pnl_pct': self._calculate_percentage(
                position.day_pnl, position.market_value
            )
        }
    
    def _serialize_position_summary(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize position summary data."""
        return {
            'symbol': position_data.get('symbol'),
            'day_pnl': self._serialize_value(position_data.get('day_pnl')),
            'day_pnl_pct': self._serialize_value(position_data.get('day_pnl_pct')),
            'market_value': self._serialize_value(position_data.get('market_value'))
        }
    
    def _serialize_chart_series(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize chart series data."""
        serialized = {}
        
        for key, value in chart_data.items():
            if key in ['dates', 'timestamps']:
                # Ensure timestamps are properly formatted
                if isinstance(value, list):
                    serialized[key] = [
                        self._serialize_datetime(item) if isinstance(item, (datetime, date)) 
                        else str(item) for item in value
                    ]
                else:
                    serialized[key] = value
            elif isinstance(value, list):
                serialized[key] = [self._serialize_value(item) for item in value]
            else:
                serialized[key] = self._serialize_value(value)
        
        return serialized
    
    def _serialize_nested_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize nested dictionary data."""
        serialized = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                serialized[key] = self._serialize_nested_dict(value)
            elif isinstance(value, list):
                serialized[key] = [self._serialize_value(item) for item in value]
            else:
                serialized[key] = self._serialize_value(value)
        
        return serialized
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value."""
        if isinstance(value, Decimal):
            return self._serialize_decimal(value)
        elif isinstance(value, (datetime, date)):
            return self._serialize_datetime(value)
        elif isinstance(value, dict):
            return self._serialize_nested_dict(value)
        elif isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        elif hasattr(value, '__dict__'):
            # Handle dataclass or object with attributes
            return self._serialize_nested_dict(value.__dict__)
        else:
            return value
    
    def _serialize_decimal(self, value: Decimal) -> float:
        """Serialize Decimal to float."""
        if value is None:
            return 0.0
        return float(value)
    
    def _serialize_datetime(self, value: Union[datetime, date]) -> str:
        """Serialize datetime to ISO string."""
        if value is None:
            return ""
        
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        else:
            return str(value)
    
    def _calculate_percentage(self, numerator: Decimal, denominator: Decimal) -> float:
        """Calculate percentage safely."""
        if denominator is None or denominator == 0:
            return 0.0
        
        if numerator is None:
            return 0.0
        
        return float(numerator / denominator * 100)
    
    def _empty_dashboard_data(self) -> Dict[str, Any]:
        """Return empty dashboard data structure."""
        return {
            'timestamp': datetime.now().isoformat(),
            'real_time_metrics': {},
            'historical_trends': {},
            'performance_summary': {},
            'risk_analysis': {},
            'market_comparison': {},
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'data_version': '1.0',
                'refresh_interval': 30,
                'error': 'No data available'
            }
        }
    
    def to_json(self, data: Dict[str, Any], indent: Optional[int] = None) -> str:
        """
        Convert serialized data to JSON string.
        
        Args:
            data: Serialized data dictionary
            indent: JSON indentation (None for compact)
            
        Returns:
            JSON string
        """
        try:
            return json.dumps(data, indent=indent, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error converting to JSON: {e}")
            return json.dumps(self._empty_dashboard_data(), indent=indent)
    
    def optimize_for_mobile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize dashboard data for mobile consumption.
        
        Args:
            data: Full dashboard data
            
        Returns:
            Mobile-optimized data
        """
        # Reduce data size for mobile
        mobile_data = {
            'timestamp': data.get('timestamp'),
            'real_time_metrics': self._optimize_real_time_metrics(
                data.get('real_time_metrics', {})
            ),
            'performance_summary': self._optimize_performance_summary(
                data.get('performance_summary', {})
            ),
            'top_positions': self._get_top_positions(
                data.get('real_time_metrics', {})
            ),
            'metadata': data.get('metadata', {})
        }
        
        return mobile_data
    
    def _optimize_real_time_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize real-time metrics for mobile."""
        if not metrics:
            return {}
        
        # Keep only essential metrics
        essential_keys = [
            'portfolio_value', 'day_pnl', 'day_pnl_pct', 
            'total_pnl', 'total_pnl_pct', 'buying_power'
        ]
        
        optimized = {}
        for key in essential_keys:
            if key in metrics:
                optimized[key] = metrics[key]
        
        # Add top 3 gainers/losers only
        if 'top_gainers' in metrics:
            optimized['top_gainers'] = metrics['top_gainers'][:3]
        
        if 'top_losers' in metrics:
            optimized['top_losers'] = metrics['top_losers'][:3]
        
        return optimized
    
    def _optimize_performance_summary(self, performance: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize performance summary for mobile."""
        if not performance:
            return {}
        
        # Keep only key periods
        key_periods = ['1d', '7d', '30d']
        optimized = {}
        
        for period in key_periods:
            if period in performance:
                optimized[period] = performance[period]
        
        return optimized
    
    def _get_top_positions(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get top positions for mobile display."""
        # This would extract top positions from real-time metrics
        # For now, return empty list
        return []