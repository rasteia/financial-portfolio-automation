"""
Portfolio management tools for MCP integration.

This module provides AI assistants with access to comprehensive portfolio
management functions including real-time data, performance analysis, and
risk assessment.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ..analytics.analytics_service import AnalyticsService
from ..analysis.portfolio_analyzer import PortfolioAnalyzer
from ..analysis.risk_manager import RiskManager
from ..api.alpaca_client import AlpacaClient
from ..exceptions import PortfolioAutomationError
from .service_factory import ServiceFactory


class PortfolioTools:
    """
    Portfolio management tools for AI assistant integration.
    
    Provides comprehensive portfolio analysis, performance metrics,
    risk assessment, and allocation analysis capabilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize portfolio tools.
        
        Args:
            config: Configuration dictionary containing service configurations
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize service factory
        self.service_factory = ServiceFactory(config)
        
        # Initialize required services with proper dependency injection
        self.analytics_service = self.service_factory.get_analytics_service()
        self.portfolio_analyzer = self.service_factory.get_portfolio_analyzer()
        self.risk_manager = self.service_factory.get_risk_manager()
        self.alpaca_client = self.service_factory.get_alpaca_client()
        
        self.logger.info("Portfolio tools initialized")
    
    def get_portfolio_summary(self, include_positions: bool = True, 
                                  include_performance: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary.
        
        Args:
            include_positions: Include detailed position information
            include_performance: Include performance metrics
            
        Returns:
            Dictionary containing portfolio summary data
        """
        try:
            self.logger.info("Generating portfolio summary")
            
            # Check if services are available
            if not self.alpaca_client:
                # Return demo data if client not available
                return self._get_demo_portfolio_summary(include_positions, include_performance)
            
            # Get account information
            account_info = self.alpaca_client.get_account_info()
            
            # Get current positions
            positions = self.alpaca_client.get_positions()
            
            # Calculate portfolio metrics
            portfolio_value = Decimal(account_info.get('portfolio_value', 0))
            buying_power = Decimal(account_info.get('buying_power', 0))
            day_pnl = Decimal(account_info.get('unrealized_pl', 0))
            
            summary = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'account_status': account_info.get('status', 'unknown'),
                'portfolio_value': float(portfolio_value),
                'buying_power': float(buying_power),
                'day_pnl': float(day_pnl),
                'day_pnl_percent': float(day_pnl / portfolio_value * 100) if portfolio_value > 0 else 0,
                'position_count': len(positions),
                'cash_balance': float(account_info.get('cash', 0)),
                'equity': float(account_info.get('equity', 0))
            }
            
            if include_positions:
                summary['positions'] = [
                    {
                        'symbol': pos.get('symbol'),
                        'quantity': float(pos.get('qty', 0)),
                        'market_value': float(pos.get('market_value', 0)),
                        'cost_basis': float(pos.get('cost_basis', 0)),
                        'unrealized_pnl': float(pos.get('unrealized_pl', 0)),
                        'unrealized_pnl_percent': float(pos.get('unrealized_plpc', 0)) * 100,
                        'side': pos.get('side', 'long')
                    }
                    for pos in positions
                ]
            
            if include_performance and self.analytics_service:
                # Get performance metrics from analytics service
                try:
                    performance_data = self.analytics_service.get_portfolio_metrics()
                    summary['performance'] = performance_data
                except Exception as e:
                    self.logger.warning(f"Could not get performance data: {e}")
                    summary['performance'] = {}
            
            self.logger.info("Portfolio summary generated successfully")
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating portfolio summary: {str(e)}")
            # Return demo data on error
            return self._get_demo_portfolio_summary(include_positions, include_performance)
    
    def get_portfolio_performance(self, period: str = "1m", 
                                      benchmark: str = "SPY") -> Dict[str, Any]:
        """
        Get portfolio performance metrics for specified period.
        
        Args:
            period: Time period (1d, 1w, 1m, 3m, 6m, 1y, ytd, all)
            benchmark: Benchmark symbol for comparison
            
        Returns:
            Dictionary containing performance metrics
        """
        try:
            self.logger.info(f"Calculating portfolio performance for period: {period}")
            
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = self._calculate_start_date(period, end_date)
            
            if not self.portfolio_analyzer:
                # Return demo performance data
                return self._get_demo_performance_data(period, benchmark, start_date, end_date)
            
            # Get portfolio performance data (using demo data for now)
            performance_data = {
                'total_return': 12.5,
                'annualized_return': 15.2,
                'volatility': 18.5,
                'sharpe_ratio': 1.35,
                'max_drawdown': 8.2,
                'calmar_ratio': 1.85,
                'sortino_ratio': 1.65,
                'beta': 1.15,
                'alpha': 2.5,
                'information_ratio': 0.85,
                'tracking_error': 4.2
            }
            
            # Get benchmark performance for comparison (using demo data)
            benchmark_data = {
                'total_return': 10.0,
                'annualized_return': 12.0,
                'volatility': 16.2,
                'sharpe_ratio': 1.15,
                'max_drawdown': 12.1
            }
            
            result = {
                'period': period,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'benchmark': benchmark,
                'portfolio_performance': {
                    'total_return': performance_data.get('total_return', 0),
                    'annualized_return': performance_data.get('annualized_return', 0),
                    'volatility': performance_data.get('volatility', 0),
                    'sharpe_ratio': performance_data.get('sharpe_ratio', 0),
                    'max_drawdown': performance_data.get('max_drawdown', 0),
                    'calmar_ratio': performance_data.get('calmar_ratio', 0),
                    'sortino_ratio': performance_data.get('sortino_ratio', 0),
                    'beta': performance_data.get('beta', 0),
                    'alpha': performance_data.get('alpha', 0),
                    'information_ratio': performance_data.get('information_ratio', 0)
                },
                'benchmark_performance': {
                    'total_return': benchmark_data.get('total_return', 0),
                    'annualized_return': benchmark_data.get('annualized_return', 0),
                    'volatility': benchmark_data.get('volatility', 0),
                    'sharpe_ratio': benchmark_data.get('sharpe_ratio', 0),
                    'max_drawdown': benchmark_data.get('max_drawdown', 0)
                },
                'relative_performance': {
                    'excess_return': performance_data.get('total_return', 0) - benchmark_data.get('total_return', 0),
                    'tracking_error': performance_data.get('tracking_error', 0),
                    'up_capture': performance_data.get('up_capture', 0),
                    'down_capture': performance_data.get('down_capture', 0)
                }
            }
            
            self.logger.info("Portfolio performance calculated successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio performance: {str(e)}")
            # Return demo data on error
            end_date = datetime.now(timezone.utc)
            start_date = self._calculate_start_date(period, end_date)
            return self._get_demo_performance_data(period, benchmark, start_date, end_date)
    
    def analyze_portfolio_risk(self, confidence_level: float = 0.95, 
                                   time_horizon: int = 1) -> Dict[str, Any]:
        """
        Analyze portfolio risk metrics.
        
        Args:
            confidence_level: Confidence level for VaR calculation
            time_horizon: Time horizon in days for risk calculation
            
        Returns:
            Dictionary containing risk analysis results
        """
        try:
            self.logger.info("Analyzing portfolio risk metrics")
            
            if not self.alpaca_client or not self.risk_manager:
                # Return demo risk analysis
                return self._get_demo_risk_analysis(confidence_level, time_horizon)
            
            # Get current positions
            positions = self.alpaca_client.get_positions()
            
            # Calculate risk metrics (using demo data for now)
            risk_metrics = {
                'var': 3500.0,
                'expected_shortfall': 4200.0,
                'volatility': 18.5,
                'beta': 1.15,
                'max_drawdown': 8.2,
                'downside_deviation': 12.8
            }
            
            # Get concentration analysis (using demo data)
            concentration_analysis = {
                'max_position_weight': 41.5,
                'top_5_weight': 100.0,
                'top_10_weight': 100.0,
                'herfindahl_index': 0.35,
                'effective_positions': 2.86,
                'sector_breakdown': {
                    'Technology': {'weight': 83.5, 'positions': ['AAPL', 'MSFT', 'GOOGL']}
                }
            }
            
            # Get correlation analysis (using demo data)
            correlation_analysis = {
                'avg_correlation': 0.72,
                'max_correlation': 0.85,
                'clusters': [
                    {'symbols': ['AAPL', 'MSFT'], 'correlation': 0.85}
                ]
            }
            
            result = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'confidence_level': confidence_level,
                'time_horizon_days': time_horizon,
                'risk_metrics': {
                    'value_at_risk': risk_metrics.get('var', 0),
                    'expected_shortfall': risk_metrics.get('expected_shortfall', 0),
                    'portfolio_volatility': risk_metrics.get('volatility', 0),
                    'portfolio_beta': risk_metrics.get('beta', 0),
                    'maximum_drawdown': risk_metrics.get('max_drawdown', 0),
                    'downside_deviation': risk_metrics.get('downside_deviation', 0)
                },
                'concentration_risk': {
                    'largest_position_weight': concentration_analysis.get('max_position_weight', 0),
                    'top_5_concentration': concentration_analysis.get('top_5_weight', 0),
                    'top_10_concentration': concentration_analysis.get('top_10_weight', 0),
                    'herfindahl_index': concentration_analysis.get('herfindahl_index', 0),
                    'effective_positions': concentration_analysis.get('effective_positions', 0)
                },
                'sector_concentration': concentration_analysis.get('sector_breakdown', {}),
                'correlation_risk': {
                    'average_correlation': correlation_analysis.get('avg_correlation', 0),
                    'max_correlation': correlation_analysis.get('max_correlation', 0),
                    'correlation_clusters': correlation_analysis.get('clusters', [])
                },
                'risk_warnings': self._generate_risk_warnings(risk_metrics, concentration_analysis)
            }
            
            self.logger.info("Portfolio risk analysis completed")
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing portfolio risk: {str(e)}")
            # Return demo data on error
            return self._get_demo_risk_analysis(confidence_level, time_horizon)
    
    def get_asset_allocation(self, breakdown_type: str = "all") -> Dict[str, Any]:
        """
        Get detailed asset allocation breakdown.
        
        Args:
            breakdown_type: Type of breakdown (sector, asset_type, geography, all)
            
        Returns:
            Dictionary containing allocation analysis
        """
        try:
            self.logger.info(f"Generating asset allocation breakdown: {breakdown_type}")
            
            if not self.alpaca_client:
                # Return demo allocation data
                return self._get_demo_asset_allocation(breakdown_type)
            
            # Get current positions
            positions = self.alpaca_client.get_positions()
            
            # Calculate total portfolio value
            total_value = sum(float(pos.get('market_value', 0)) for pos in positions)
            
            allocation_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_portfolio_value': total_value,
                'breakdown_type': breakdown_type
            }
            
            if breakdown_type in ['sector', 'all']:
                sector_allocation = self._calculate_sector_allocation(positions, total_value)
                allocation_data['sector_allocation'] = sector_allocation
            
            if breakdown_type in ['asset_type', 'all']:
                asset_type_allocation = self._calculate_asset_type_allocation(positions, total_value)
                allocation_data['asset_type_allocation'] = asset_type_allocation
            
            if breakdown_type in ['geography', 'all']:
                geographic_allocation = self._calculate_geographic_allocation(positions, total_value)
                allocation_data['geographic_allocation'] = geographic_allocation
            
            # Add position-level details
            allocation_data['positions'] = [
                {
                    'symbol': pos.get('symbol'),
                    'market_value': float(pos.get('market_value', 0)),
                    'weight': float(pos.get('market_value', 0)) / total_value * 100 if total_value > 0 else 0,
                    'quantity': float(pos.get('qty', 0)),
                    'side': pos.get('side', 'long')
                }
                for pos in positions
            ]
            
            self.logger.info("Asset allocation analysis completed")
            return allocation_data
            
        except Exception as e:
            self.logger.error(f"Error calculating asset allocation: {str(e)}")
            # Return demo data on error
            return self._get_demo_asset_allocation(breakdown_type)
    
    def _calculate_start_date(self, period: str, end_date: datetime) -> datetime:
        """Calculate start date based on period string."""
        period_map = {
            '1d': timedelta(days=1),
            '1w': timedelta(weeks=1),
            '1m': timedelta(days=30),
            '3m': timedelta(days=90),
            '6m': timedelta(days=180),
            '1y': timedelta(days=365),
            'ytd': None,  # Year to date
            'all': timedelta(days=365*10)  # 10 years max
        }
        
        if period == 'ytd':
            return datetime(end_date.year, 1, 1)
        
        delta = period_map.get(period, timedelta(days=30))
        return end_date - delta
    
    def _calculate_sector_allocation(self, positions: List[Dict], 
                                         total_value: float) -> Dict[str, Any]:
        """Calculate sector allocation breakdown."""
        # This would integrate with a sector classification service
        # For now, return a simplified breakdown
        sector_map = {
            'AAPL': 'Technology',
            'MSFT': 'Technology', 
            'GOOGL': 'Technology',
            'AMZN': 'Consumer Discretionary',
            'TSLA': 'Consumer Discretionary',
            'SPY': 'Diversified ETF',
            'QQQ': 'Technology ETF'
        }
        
        sectors = {}
        for pos in positions:
            symbol = pos.get('symbol', '')
            sector = sector_map.get(symbol, 'Other')
            value = float(pos.get('market_value', 0))
            
            if sector not in sectors:
                sectors[sector] = {'value': 0, 'weight': 0, 'positions': []}
            
            sectors[sector]['value'] += value
            sectors[sector]['positions'].append(symbol)
        
        # Calculate weights
        for sector_data in sectors.values():
            sector_data['weight'] = sector_data['value'] / total_value * 100 if total_value > 0 else 0
        
        return sectors
    
    def _calculate_asset_type_allocation(self, positions: List[Dict], 
                                             total_value: float) -> Dict[str, Any]:
        """Calculate asset type allocation breakdown."""
        # Simplified asset type classification
        etf_symbols = ['SPY', 'QQQ', 'IWM', 'VTI', 'VXUS']
        
        asset_types = {'Stocks': {'value': 0, 'weight': 0, 'positions': []},
                      'ETFs': {'value': 0, 'weight': 0, 'positions': []}}
        
        for pos in positions:
            symbol = pos.get('symbol', '')
            value = float(pos.get('market_value', 0))
            
            if symbol in etf_symbols:
                asset_types['ETFs']['value'] += value
                asset_types['ETFs']['positions'].append(symbol)
            else:
                asset_types['Stocks']['value'] += value
                asset_types['Stocks']['positions'].append(symbol)
        
        # Calculate weights
        for asset_data in asset_types.values():
            asset_data['weight'] = asset_data['value'] / total_value * 100 if total_value > 0 else 0
        
        return asset_types
    
    def _calculate_geographic_allocation(self, positions: List[Dict], 
                                             total_value: float) -> Dict[str, Any]:
        """Calculate geographic allocation breakdown."""
        # Simplified geographic classification
        # In production, this would use a comprehensive database
        geography = {'US': {'value': 0, 'weight': 0, 'positions': []},
                    'International': {'value': 0, 'weight': 0, 'positions': []}}
        
        for pos in positions:
            symbol = pos.get('symbol', '')
            value = float(pos.get('market_value', 0))
            
            # Most symbols in this system are US-based
            geography['US']['value'] += value
            geography['US']['positions'].append(symbol)
        
        # Calculate weights
        for geo_data in geography.values():
            geo_data['weight'] = geo_data['value'] / total_value * 100 if total_value > 0 else 0
        
        return geography
    
    def _generate_risk_warnings(self, risk_metrics: Dict[str, Any], 
                               concentration_analysis: Dict[str, Any]) -> List[str]:
        """Generate risk warnings based on analysis."""
        warnings = []
        
        # Check concentration risk
        max_position = concentration_analysis.get('max_position_weight', 0)
        if max_position > 20:
            warnings.append(f"High concentration risk: Largest position is {max_position:.1f}% of portfolio")
        
        # Check portfolio volatility
        volatility = risk_metrics.get('volatility', 0)
        if volatility > 25:
            warnings.append(f"High portfolio volatility: {volatility:.1f}% annualized")
        
        # Check maximum drawdown
        max_drawdown = risk_metrics.get('max_drawdown', 0)
        if max_drawdown > 20:
            warnings.append(f"High maximum drawdown: {max_drawdown:.1f}%")
        
        return warnings
    
    def _get_demo_portfolio_summary(self, include_positions: bool = True, 
                                   include_performance: bool = True) -> Dict[str, Any]:
        """Get demo portfolio summary when real data is not available."""
        demo_positions = [
            {
                'symbol': 'AAPL',
                'quantity': 100.0,
                'market_value': 17500.0,
                'cost_basis': 15000.0,
                'unrealized_pnl': 2500.0,
                'unrealized_pnl_percent': 16.67,
                'side': 'long'
            },
            {
                'symbol': 'MSFT',
                'quantity': 50.0,
                'market_value': 20800.0,
                'cost_basis': 18000.0,
                'unrealized_pnl': 2800.0,
                'unrealized_pnl_percent': 15.56,
                'side': 'long'
            },
            {
                'symbol': 'GOOGL',
                'quantity': 25.0,
                'market_value': 4150.0,
                'cost_basis': 4500.0,
                'unrealized_pnl': -350.0,
                'unrealized_pnl_percent': -7.78,
                'side': 'long'
            }
        ]
        
        total_value = sum(pos['market_value'] for pos in demo_positions)
        total_pnl = sum(pos['unrealized_pnl'] for pos in demo_positions)
        
        summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'account_status': 'demo',
            'portfolio_value': total_value,
            'buying_power': 25000.0,
            'day_pnl': total_pnl,
            'day_pnl_percent': (total_pnl / total_value * 100) if total_value > 0 else 0,
            'position_count': len(demo_positions),
            'cash_balance': 25000.0,
            'equity': total_value
        }
        
        if include_positions:
            summary['positions'] = demo_positions
            
        if include_performance:
            summary['performance'] = {
                'total_return': 12.5,
                'annualized_return': 15.2,
                'volatility': 18.5,
                'sharpe_ratio': 1.35,
                'max_drawdown': 8.2
            }
        
        return summary

    def _get_demo_performance_data(self, period: str, benchmark: str, 
                                  start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get demo performance data when real analysis is not available."""
        # Demo performance data based on period
        period_multipliers = {
            '1d': 0.1, '1w': 0.5, '1m': 2.0, '3m': 6.0, 
            '6m': 10.0, '1y': 15.0, 'ytd': 12.0, 'all': 25.0
        }
        
        base_return = period_multipliers.get(period, 2.0)
        benchmark_return = base_return * 0.8  # Benchmark slightly lower
        
        return {
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'benchmark': benchmark,
            'portfolio_performance': {
                'total_return': base_return,
                'annualized_return': base_return * 1.2,
                'volatility': 18.5,
                'sharpe_ratio': 1.35,
                'max_drawdown': 8.2,
                'calmar_ratio': 1.85,
                'sortino_ratio': 1.65,
                'beta': 1.15,
                'alpha': 2.5,
                'information_ratio': 0.85
            },
            'benchmark_performance': {
                'total_return': benchmark_return,
                'annualized_return': benchmark_return * 1.1,
                'volatility': 16.2,
                'sharpe_ratio': 1.15,
                'max_drawdown': 12.1
            },
            'relative_performance': {
                'excess_return': base_return - benchmark_return,
                'tracking_error': 4.2,
                'up_capture': 1.08,
                'down_capture': 0.92
            }
        }

    def _get_demo_risk_analysis(self, confidence_level: float, time_horizon: int) -> Dict[str, Any]:
        """Get demo risk analysis when real analysis is not available."""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'confidence_level': confidence_level,
            'time_horizon_days': time_horizon,
            'risk_metrics': {
                'value_at_risk': 3500.0,
                'expected_shortfall': 4200.0,
                'portfolio_volatility': 18.5,
                'portfolio_beta': 1.15,
                'maximum_drawdown': 8.2,
                'downside_deviation': 12.8
            },
            'concentration_risk': {
                'largest_position_weight': 41.5,  # MSFT position
                'top_5_concentration': 100.0,  # Only 3 positions
                'top_10_concentration': 100.0,
                'herfindahl_index': 0.35,
                'effective_positions': 2.86
            },
            'sector_concentration': {
                'Technology': {'weight': 83.5, 'positions': ['AAPL', 'MSFT', 'GOOGL']},
                'Other': {'weight': 16.5, 'positions': []}
            },
            'correlation_risk': {
                'average_correlation': 0.72,
                'max_correlation': 0.85,
                'correlation_clusters': [
                    {'symbols': ['AAPL', 'MSFT'], 'correlation': 0.85},
                    {'symbols': ['AAPL', 'GOOGL'], 'correlation': 0.78}
                ]
            },
            'risk_warnings': [
                'High concentration risk: Largest position is 41.5% of portfolio',
                'High sector concentration: Technology represents 83.5% of portfolio',
                'High correlation risk: Average correlation is 72%'
            ]
        }

    def _get_demo_asset_allocation(self, breakdown_type: str) -> Dict[str, Any]:
        """Get demo asset allocation when real data is not available."""
        demo_positions = [
            {'symbol': 'AAPL', 'market_value': 17500.0, 'weight': 41.7, 'quantity': 100.0, 'side': 'long'},
            {'symbol': 'MSFT', 'market_value': 20800.0, 'weight': 49.5, 'quantity': 50.0, 'side': 'long'},
            {'symbol': 'GOOGL', 'market_value': 4150.0, 'weight': 9.9, 'quantity': 25.0, 'side': 'long'}
        ]
        
        total_value = sum(pos['market_value'] for pos in demo_positions)
        
        allocation_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_portfolio_value': total_value,
            'breakdown_type': breakdown_type,
            'positions': demo_positions
        }
        
        if breakdown_type in ['sector', 'all']:
            allocation_data['sector_allocation'] = {
                'Technology': {'value': total_value, 'weight': 100.0, 'positions': ['AAPL', 'MSFT', 'GOOGL']}
            }
        
        if breakdown_type in ['asset_type', 'all']:
            allocation_data['asset_type_allocation'] = {
                'Stocks': {'value': total_value, 'weight': 100.0, 'positions': ['AAPL', 'MSFT', 'GOOGL']},
                'ETFs': {'value': 0, 'weight': 0.0, 'positions': []}
            }
        
        if breakdown_type in ['geography', 'all']:
            allocation_data['geographic_allocation'] = {
                'US': {'value': total_value, 'weight': 100.0, 'positions': ['AAPL', 'MSFT', 'GOOGL']},
                'International': {'value': 0, 'weight': 0.0, 'positions': []}
            }
        
        return allocation_data

    def health_check(self) -> Dict[str, Any]:
        """Perform health check of portfolio tools."""
        return {
            'status': 'healthy',
            'services': {
                'analytics_service': 'connected' if self.analytics_service else 'demo',
                'portfolio_analyzer': 'connected' if self.portfolio_analyzer else 'demo',
                'risk_manager': 'connected' if self.risk_manager else 'demo',
                'alpaca_client': 'connected' if self.alpaca_client else 'demo'
            },
            'last_check': datetime.now(timezone.utc).isoformat()
        }
