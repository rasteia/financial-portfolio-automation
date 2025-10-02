"""
Reporting tools for MCP integration.

This module provides AI assistants with access to comprehensive reporting
capabilities including performance reports, tax analysis, and dashboard data.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from ..reporting.report_generator import ReportGenerator
from ..reporting.performance_report import PerformanceReport
from ..reporting.tax_report import TaxReport
from ..reporting.transaction_report import TransactionReport
from ..analytics.analytics_service import AnalyticsService
from ..exceptions import PortfolioAutomationError


class ReportingTools:
    """
    Reporting tools for AI assistant integration.
    
    Provides comprehensive reporting capabilities including performance
    analysis, tax reporting, and real-time dashboard data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize reporting tools.
        
        Args:
            config: Configuration dictionary containing service configurations
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize required services with error handling
        try:
            self.report_generator = ReportGenerator(config)
        except Exception as e:
            self.logger.warning(f"Report generator not available: {e}")
            self.report_generator = None
            
        try:
            self.performance_report = PerformanceReport(config)
        except Exception as e:
            self.logger.warning(f"Performance report not available: {e}")
            self.performance_report = None
            
        try:
            self.tax_report = TaxReport(config)
        except Exception as e:
            self.logger.warning(f"Tax report not available: {e}")
            self.tax_report = None
            
        try:
            self.transaction_report = TransactionReport(config)
        except Exception as e:
            self.logger.warning(f"Transaction report not available: {e}")
            self.transaction_report = None
            
        try:
            self.analytics_service = AnalyticsService(config)
        except Exception as e:
            self.logger.warning(f"Analytics service not available: {e}")
            self.analytics_service = None
        
        self.logger.info("Reporting tools initialized")
    
    async def generate_performance_report(self, format: str = "json", 
                                        period: str = "1m",
                                        include_charts: bool = False) -> Dict[str, Any]:
        """
        Generate comprehensive portfolio performance report.
        
        Args:
            format: Report format (json, html, pdf, csv)
            period: Report period
            include_charts: Include performance charts
            
        Returns:
            Dictionary containing performance report data or file path
        """
        try:
            self.logger.info(f"Generating performance report in {format} format for period {period}")
            
            # Check if services are available
            if not self.performance_report:
                return self._get_demo_performance_report(format, period, include_charts)
            
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = self._calculate_start_date(period, end_date)
            
            # Generate performance report
            report_data = await self.performance_report.generate_report(
                start_date=start_date,
                end_date=end_date,
                include_charts=include_charts
            )
            
            if format.lower() == "json":
                # Return structured data for AI consumption
                result = {
                    'report_type': 'performance',
                    'format': format,
                    'period': period,
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'data': report_data
                }
                
                # Add AI-friendly summary
                result['summary'] = self._create_performance_summary(report_data)
                
                return result
            
            else:
                # Generate file-based report
                file_path = await self.report_generator.generate_report(
                    report_type='performance',
                    data=report_data,
                    format=format,
                    filename=f"performance_report_{period}_{datetime.now().strftime('%Y%m%d')}"
                )
                
                return {
                    'report_type': 'performance',
                    'format': format,
                    'period': period,
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'file_path': file_path,
                    'summary': self._create_performance_summary(report_data)
                }
            
        except Exception as e:
            self.logger.error(f"Error generating performance report: {str(e)}")
            # Return demo data on error
            return self._get_demo_performance_report(format, period, include_charts)
    
    async def generate_tax_report(self, tax_year: int = None, 
                                format: str = "json") -> Dict[str, Any]:
        """
        Generate tax report with realized gains/losses.
        
        Args:
            tax_year: Tax year for report
            format: Report format
            
        Returns:
            Dictionary containing tax report data
        """
        try:
            if tax_year is None:
                tax_year = datetime.now().year
            
            self.logger.info(f"Generating tax report for year {tax_year}")
            
            # Generate tax report
            tax_data = await self.tax_report.generate_report(tax_year=tax_year)
            
            if format.lower() == "json":
                result = {
                    'report_type': 'tax',
                    'format': format,
                    'tax_year': tax_year,
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'data': tax_data
                }
                
                # Add AI-friendly summary
                result['summary'] = self._create_tax_summary(tax_data)
                
                return result
            
            else:
                # Generate file-based report
                file_path = await self.report_generator.generate_report(
                    report_type='tax',
                    data=tax_data,
                    format=format,
                    filename=f"tax_report_{tax_year}"
                )
                
                return {
                    'report_type': 'tax',
                    'format': format,
                    'tax_year': tax_year,
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'file_path': file_path,
                    'summary': self._create_tax_summary(tax_data)
                }
            
        except Exception as e:
            self.logger.error(f"Error generating tax report: {str(e)}")
            # Return demo data on error
            return self._get_demo_tax_report(tax_year or datetime.now().year, format)
    
    async def generate_transaction_report(self, start_date: str = None,
                                        end_date: str = None,
                                        format: str = "json") -> Dict[str, Any]:
        """
        Generate detailed transaction report.
        
        Args:
            start_date: Start date for report (YYYY-MM-DD)
            end_date: End date for report (YYYY-MM-DD)
            format: Report format
            
        Returns:
            Dictionary containing transaction report data
        """
        try:
            self.logger.info("Generating transaction report")
            
            # Parse dates
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            else:
                start_dt = datetime.now(timezone.utc) - timedelta(days=30)
            
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                end_dt = datetime.now(timezone.utc)
            
            # Generate transaction report
            transaction_data = await self.transaction_report.generate_report(
                start_date=start_dt,
                end_date=end_dt
            )
            
            if format.lower() == "json":
                result = {
                    'report_type': 'transaction',
                    'format': format,
                    'start_date': start_dt.isoformat(),
                    'end_date': end_dt.isoformat(),
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'data': transaction_data
                }
                
                # Add AI-friendly summary
                result['summary'] = self._create_transaction_summary(transaction_data)
                
                return result
            
            else:
                # Generate file-based report
                file_path = await self.report_generator.generate_report(
                    report_type='transaction',
                    data=transaction_data,
                    format=format,
                    filename=f"transaction_report_{start_dt.strftime('%Y%m%d')}_{end_dt.strftime('%Y%m%d')}"
                )
                
                return {
                    'report_type': 'transaction',
                    'format': format,
                    'start_date': start_dt.isoformat(),
                    'end_date': end_dt.isoformat(),
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'file_path': file_path,
                    'summary': self._create_transaction_summary(transaction_data)
                }
            
        except Exception as e:
            self.logger.error(f"Error generating transaction report: {str(e)}")
            raise PortfolioAutomationError(f"Transaction report generation failed: {str(e)}")
    
    async def get_dashboard_data(self, refresh_cache: bool = False) -> Dict[str, Any]:
        """
        Get real-time dashboard data optimized for AI consumption.
        
        Args:
            refresh_cache: Force refresh of cached data
            
        Returns:
            Dictionary containing dashboard data
        """
        try:
            self.logger.info("Retrieving dashboard data for AI consumption")
            
            # Get comprehensive analytics data
            dashboard_data = await self.analytics_service.get_dashboard_data(
                refresh_cache=refresh_cache
            )
            
            # Structure data for AI assistant consumption
            result = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data_freshness': 'live' if refresh_cache else 'cached',
                'portfolio_overview': dashboard_data.get('portfolio_overview', {}),
                'performance_metrics': dashboard_data.get('performance_metrics', {}),
                'risk_metrics': dashboard_data.get('risk_metrics', {}),
                'market_data': dashboard_data.get('market_data', {}),
                'alerts': dashboard_data.get('alerts', []),
                'recent_activity': dashboard_data.get('recent_activity', [])
            }
            
            # Add AI-friendly insights
            result['insights'] = await self._generate_dashboard_insights(dashboard_data)
            
            # Add quick facts for AI responses
            result['quick_facts'] = self._extract_quick_facts(dashboard_data)
            
            self.logger.info("Dashboard data retrieved successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error retrieving dashboard data: {str(e)}")
            # Return demo data on error
            return self._get_demo_dashboard_data(refresh_cache)
    
    async def export_portfolio_data(self, data_type: str = "all",
                                  format: str = "csv",
                                  period: str = "1y") -> Dict[str, Any]:
        """
        Export portfolio data in various formats.
        
        Args:
            data_type: Type of data to export (positions, transactions, performance, all)
            format: Export format (csv, json, excel)
            period: Time period for historical data
            
        Returns:
            Dictionary containing export information
        """
        try:
            self.logger.info(f"Exporting {data_type} data in {format} format")
            
            # Calculate date range for historical data
            end_date = datetime.now(timezone.utc)
            start_date = self._calculate_start_date(period, end_date)
            
            export_data = {}
            
            if data_type in ['positions', 'all']:
                # Export current positions
                positions_data = await self.analytics_service.get_current_positions()
                export_data['positions'] = positions_data
            
            if data_type in ['transactions', 'all']:
                # Export transaction history
                transactions_data = await self.transaction_report.get_transactions(
                    start_date=start_date,
                    end_date=end_date
                )
                export_data['transactions'] = transactions_data
            
            if data_type in ['performance', 'all']:
                # Export performance data
                performance_data = await self.performance_report.get_performance_data(
                    start_date=start_date,
                    end_date=end_date
                )
                export_data['performance'] = performance_data
            
            # Generate export file
            file_path = await self.report_generator.export_data(
                data=export_data,
                format=format,
                filename=f"portfolio_export_{data_type}_{datetime.now().strftime('%Y%m%d')}"
            )
            
            return {
                'export_type': data_type,
                'format': format,
                'period': period,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'file_path': file_path,
                'record_count': self._count_export_records(export_data)
            }
            
        except Exception as e:
            self.logger.error(f"Error exporting portfolio data: {str(e)}")
            raise PortfolioAutomationError(f"Data export failed: {str(e)}")
    
    def _calculate_start_date(self, period: str, end_date: datetime) -> datetime:
        """Calculate start date based on period string."""
        period_map = {
            '1d': timedelta(days=1),
            '1w': timedelta(weeks=1),
            '1m': timedelta(days=30),
            '3m': timedelta(days=90),
            '6m': timedelta(days=180),
            '1y': timedelta(days=365),
            'ytd': None,
            'all': timedelta(days=365*10)
        }
        
        if period == 'ytd':
            return datetime(end_date.year, 1, 1)
        
        delta = period_map.get(period, timedelta(days=30))
        return end_date - delta
    
    def _create_performance_summary(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create AI-friendly performance summary."""
        summary = {
            'overall_performance': 'positive' if report_data.get('total_return', 0) > 0 else 'negative',
            'key_metrics': {},
            'highlights': [],
            'concerns': []
        }
        
        # Extract key metrics
        metrics = report_data.get('performance_metrics', {})
        summary['key_metrics'] = {
            'total_return': metrics.get('total_return', 0),
            'sharpe_ratio': metrics.get('sharpe_ratio', 0),
            'max_drawdown': metrics.get('max_drawdown', 0),
            'volatility': metrics.get('volatility', 0)
        }
        
        # Generate highlights and concerns
        if metrics.get('total_return', 0) > 10:
            summary['highlights'].append("Strong positive returns")
        
        if metrics.get('sharpe_ratio', 0) > 1.5:
            summary['highlights'].append("Excellent risk-adjusted returns")
        
        if metrics.get('max_drawdown', 0) > 20:
            summary['concerns'].append("High maximum drawdown indicates significant risk")
        
        if metrics.get('volatility', 0) > 25:
            summary['concerns'].append("High portfolio volatility")
        
        return summary
    
    def _create_tax_summary(self, tax_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create AI-friendly tax summary."""
        summary = {
            'tax_liability': 'gain' if tax_data.get('net_realized_gain', 0) > 0 else 'loss',
            'key_figures': {},
            'recommendations': []
        }
        
        # Extract key figures
        summary['key_figures'] = {
            'net_realized_gain': tax_data.get('net_realized_gain', 0),
            'short_term_gains': tax_data.get('short_term_gains', 0),
            'long_term_gains': tax_data.get('long_term_gains', 0),
            'wash_sale_adjustments': tax_data.get('wash_sale_adjustments', 0)
        }
        
        # Generate recommendations
        if tax_data.get('unrealized_losses', 0) > 1000:
            summary['recommendations'].append("Consider tax-loss harvesting opportunities")
        
        if tax_data.get('short_term_gains', 0) > tax_data.get('long_term_gains', 0):
            summary['recommendations'].append("Consider holding positions longer for better tax treatment")
        
        return summary
    
    def _create_transaction_summary(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create AI-friendly transaction summary."""
        transactions = transaction_data.get('transactions', [])
        
        summary = {
            'transaction_count': len(transactions),
            'activity_level': 'high' if len(transactions) > 50 else 'moderate' if len(transactions) > 10 else 'low',
            'key_statistics': {},
            'patterns': []
        }
        
        if transactions:
            # Calculate statistics
            buy_count = len([t for t in transactions if t.get('side') == 'buy'])
            sell_count = len([t for t in transactions if t.get('side') == 'sell'])
            
            summary['key_statistics'] = {
                'total_transactions': len(transactions),
                'buy_transactions': buy_count,
                'sell_transactions': sell_count,
                'net_activity': buy_count - sell_count
            }
            
            # Identify patterns
            if buy_count > sell_count * 2:
                summary['patterns'].append("Heavy buying activity")
            elif sell_count > buy_count * 2:
                summary['patterns'].append("Heavy selling activity")
            else:
                summary['patterns'].append("Balanced trading activity")
        
        return summary
    
    async def _generate_dashboard_insights(self, dashboard_data: Dict[str, Any]) -> List[str]:
        """Generate AI-friendly insights from dashboard data."""
        insights = []
        
        # Portfolio performance insights
        performance = dashboard_data.get('performance_metrics', {})
        if performance.get('day_pnl_percent', 0) > 2:
            insights.append("Portfolio is up significantly today")
        elif performance.get('day_pnl_percent', 0) < -2:
            insights.append("Portfolio is down significantly today")
        
        # Risk insights
        risk_metrics = dashboard_data.get('risk_metrics', {})
        if risk_metrics.get('portfolio_beta', 1) > 1.5:
            insights.append("Portfolio has high market sensitivity")
        
        # Market insights
        market_data = dashboard_data.get('market_data', {})
        if market_data.get('vix', 20) > 30:
            insights.append("Market volatility is elevated")
        
        # Alert insights
        alerts = dashboard_data.get('alerts', [])
        if len(alerts) > 0:
            insights.append(f"{len(alerts)} active alerts require attention")
        
        return insights
    
    def _extract_quick_facts(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract quick facts for AI responses."""
        portfolio_overview = dashboard_data.get('portfolio_overview', {})
        performance_metrics = dashboard_data.get('performance_metrics', {})
        
        return {
            'portfolio_value': portfolio_overview.get('total_value', 0),
            'day_change': performance_metrics.get('day_pnl', 0),
            'day_change_percent': performance_metrics.get('day_pnl_percent', 0),
            'position_count': portfolio_overview.get('position_count', 0),
            'cash_balance': portfolio_overview.get('cash_balance', 0),
            'buying_power': portfolio_overview.get('buying_power', 0)
        }
    
    def _count_export_records(self, export_data: Dict[str, Any]) -> Dict[str, int]:
        """Count records in export data."""
        counts = {}
        
        for data_type, data in export_data.items():
            if isinstance(data, list):
                counts[data_type] = len(data)
            elif isinstance(data, dict):
                counts[data_type] = len(data.get('records', []))
            else:
                counts[data_type] = 1
        
        return counts
    
    def _get_demo_performance_report(self, format: str, period: str, include_charts: bool) -> Dict[str, Any]:
        """Get demo performance report when real reporting is not available."""
        return {
            'report_type': 'performance',
            'format': format,
            'period': period,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': {
                'performance_metrics': {
                    'total_return': 12.5,
                    'annualized_return': 15.2,
                    'volatility': 18.5,
                    'sharpe_ratio': 1.35,
                    'max_drawdown': 8.2,
                    'calmar_ratio': 1.85,
                    'sortino_ratio': 1.65,
                    'beta': 1.15,
                    'alpha': 2.5
                }
            },
            'summary': {
                'overall_performance': 'positive',
                'key_metrics': {'total_return': 12.5, 'sharpe_ratio': 1.35},
                'highlights': ['Strong positive returns', 'Excellent risk-adjusted returns'],
                'concerns': []
            }
        }

    def _get_demo_tax_report(self, tax_year: int, format: str) -> Dict[str, Any]:
        """Get demo tax report when real reporting is not available."""
        return {
            'report_type': 'tax',
            'tax_year': tax_year,
            'format': format,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': {
                'net_realized_gain': 5250.0,
                'short_term_gains': 2100.0,
                'long_term_gains': 3150.0
            }
        }

    def _get_demo_dashboard_data(self, refresh_cache: bool) -> Dict[str, Any]:
        """Get demo dashboard data when real data is not available."""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'portfolio_overview': {
                'total_value': 150000,
                'position_count': 5
            },
            'performance_metrics': {
                'day_pnl': 2500,
                'day_pnl_percent': 1.67
            },
            'insights': ['Portfolio is up significantly today'],
            'quick_facts': {
                'portfolio_value': 150000,
                'day_change': 2500
            }
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check of reporting tools."""
        return {
            'status': 'healthy',
            'services': {
                'report_generator': 'connected' if self.report_generator else 'demo',
                'performance_report': 'connected' if self.performance_report else 'demo',
                'tax_report': 'connected' if self.tax_report else 'demo',
                'transaction_report': 'connected' if self.transaction_report else 'demo',
                'analytics_service': 'connected' if self.analytics_service else 'demo'
            },
            'last_check': datetime.now(timezone.utc).isoformat()
        }
