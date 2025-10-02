"""
Analytics module for dashboard data preparation and real-time metrics.

This module provides comprehensive analytics capabilities including:
- Real-time metrics calculation and caching
- Historical data aggregation and trend analysis
- Performance benchmarking and comparison
- Dashboard data serialization for web consumption
"""

from .analytics_service import AnalyticsService
from .metrics_calculator import MetricsCalculator
from .trend_analyzer import TrendAnalyzer
from .data_aggregator import DataAggregator
from .dashboard_serializer import DashboardSerializer

__all__ = [
    'AnalyticsService',
    'MetricsCalculator',
    'TrendAnalyzer',
    'DataAggregator',
    'DashboardSerializer'
]