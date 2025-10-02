"""
Monitoring tools for MCP integration.

This module provides AI assistants with real-time portfolio monitoring
and alerting capabilities.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from ..monitoring.portfolio_monitor import PortfolioMonitor
from ..analysis.portfolio_analyzer import PortfolioAnalyzer
from ..analysis.risk_manager import RiskManager
from ..models.core import Position, Alert, AlertType
from ..config.settings import Settings
from ..exceptions import ValidationError

logger = logging.getLogger(__name__)


class MonitoringTools:
    """MCP tools for portfolio monitoring and alerting."""
    
    def __init__(self, settings: Settings):
        """Initialize monitoring tools with required services."""
        self.settings = settings
        self.portfolio_monitor = PortfolioMonitor(settings)
        self.portfolio_analyzer = PortfolioAnalyzer(settings)
        self.risk_manager = RiskManager(settings)
        
    async def monitor_portfolio(
        self,
        alert_thresholds: Optional[Dict[str, float]] = None,
        include_positions: bool = True,
        include_performance: bool = True,
        include_risk_metrics: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive portfolio monitoring data.
        
        Args:
            alert_thresholds: Custom alert thresholds
            include_positions: Whether to include position details
            include_performance: Whether to include performance metrics
            include_risk_metrics: Whether to include risk metrics
            
        Returns:
            Dict containing portfolio monitoring data
        """
        try:
            # Get current portfolio state
            portfolio_state = await self.portfolio_monitor.get_portfolio_state()
            
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "portfolio_value": float(portfolio_state.total_value),
                "cash_balance": float(portfolio_state.cash_balance),
                "day_change": float(portfolio_state.day_change),
                "day_change_percent": float(portfolio_state.day_change_percent)
            }
            
            # Include position details if requested
            if include_positions:
                positions = await self.portfolio_monitor.get_positions()
                result["positions"] = [
                    {
                        "symbol": pos.symbol,
                        "quantity": float(pos.quantity),
                        "market_value": float(pos.market_value),
                        "cost_basis": float(pos.cost_basis),
                        "unrealized_pnl": float(pos.unrealized_pnl),
                        "unrealized_pnl_percent": float(pos.unrealized_pnl_percent),
                        "day_change": float(pos.day_change),
                        "day_change_percent": float(pos.day_change_percent)
                    }
                    for pos in positions
                ]
            
            # Include performance metrics if requested
            if include_performance:
                performance = await self.portfolio_analyzer.calculate_performance_metrics()
                result["performance"] = {
                    "total_return": float(performance.total_return),
                    "total_return_percent": float(performance.total_return_percent),
                    "annualized_return": float(performance.annualized_return),
                    "sharpe_ratio": float(performance.sharpe_ratio),
                    "max_drawdown": float(performance.max_drawdown),
                    "win_rate": float(performance.win_rate),
                    "profit_factor": float(performance.profit_factor)
                }
            
            # Include risk metrics if requested
            if include_risk_metrics:
                risk_metrics = await self.risk_manager.calculate_portfolio_risk()
                result["risk_metrics"] = {
                    "portfolio_beta": float(risk_metrics.portfolio_beta),
                    "value_at_risk": float(risk_metrics.value_at_risk),
                    "expected_shortfall": float(risk_metrics.expected_shortfall),
                    "volatility": float(risk_metrics.volatility),
                    "correlation_risk": float(risk_metrics.correlation_risk),
                    "concentration_risk": float(risk_metrics.concentration_risk)
                }
            
            # Check for alerts based on thresholds
            alerts = await self._check_portfolio_alerts(alert_thresholds)
            if alerts:
                result["alerts"] = [
                    {
                        "type": alert.alert_type.value,
                        "message": alert.message,
                        "severity": alert.severity.value,
                        "symbol": alert.symbol,
                        "value": float(alert.value) if alert.value else None,
                        "threshold": float(alert.threshold) if alert.threshold else None,
                        "timestamp": alert.timestamp.isoformat()
                    }
                    for alert in alerts
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"Error monitoring portfolio: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_position_alerts(
        self,
        symbol: Optional[str] = None,
        alert_types: Optional[List[str]] = None,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """
        Get position-specific alerts and notifications.
        
        Args:
            symbol: Specific symbol to check (optional)
            alert_types: Types of alerts to include
            hours_back: How many hours back to check for alerts
            
        Returns:
            Dict containing position alerts
        """
        try:
            # Get alerts from the specified time period
            start_time = datetime.now() - timedelta(hours=hours_back)
            alerts = await self.portfolio_monitor.get_alerts(
                symbol=symbol,
                alert_types=alert_types,
                start_time=start_time
            )
            
            # Group alerts by symbol
            alerts_by_symbol = {}
            for alert in alerts:
                if alert.symbol not in alerts_by_symbol:
                    alerts_by_symbol[alert.symbol] = []
                alerts_by_symbol[alert.symbol].append({
                    "type": alert.alert_type.value,
                    "message": alert.message,
                    "severity": alert.severity.value,
                    "value": float(alert.value) if alert.value else None,
                    "threshold": float(alert.threshold) if alert.threshold else None,
                    "timestamp": alert.timestamp.isoformat()
                })
            
            return {
                "success": True,
                "symbol_filter": symbol,
                "hours_back": hours_back,
                "total_alerts": len(alerts),
                "alerts_by_symbol": alerts_by_symbol
            }
            
        except Exception as e:
            logger.error(f"Error getting position alerts: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def track_performance(
        self,
        period: str = "1d",
        benchmark: Optional[str] = None,
        include_attribution: bool = False
    ) -> Dict[str, Any]:
        """
        Track portfolio performance over specified period.
        
        Args:
            period: Time period (1d, 1w, 1m, 3m, 6m, 1y, ytd)
            benchmark: Benchmark symbol for comparison
            include_attribution: Whether to include performance attribution
            
        Returns:
            Dict containing performance tracking data
        """
        try:
            if period not in ["1d", "1w", "1m", "3m", "6m", "1y", "ytd"]:
                raise ValidationError(f"Invalid period: {period}")
            
            # Calculate performance for the specified period
            performance = await self.portfolio_analyzer.calculate_period_performance(period)
            
            result = {
                "success": True,
                "period": period,
                "start_date": performance.start_date.isoformat(),
                "end_date": performance.end_date.isoformat(),
                "total_return": float(performance.total_return),
                "total_return_percent": float(performance.total_return_percent),
                "annualized_return": float(performance.annualized_return),
                "volatility": float(performance.volatility),
                "sharpe_ratio": float(performance.sharpe_ratio),
                "max_drawdown": float(performance.max_drawdown),
                "max_drawdown_date": performance.max_drawdown_date.isoformat() if performance.max_drawdown_date else None
            }
            
            # Add benchmark comparison if requested
            if benchmark:
                benchmark_performance = await self.portfolio_analyzer.calculate_benchmark_performance(
                    benchmark, period
                )
                result["benchmark"] = {
                    "symbol": benchmark,
                    "return": float(benchmark_performance.total_return),
                    "return_percent": float(benchmark_performance.total_return_percent),
                    "volatility": float(benchmark_performance.volatility),
                    "alpha": float(performance.total_return - benchmark_performance.total_return),
                    "beta": float(performance.beta) if hasattr(performance, 'beta') else None
                }
            
            # Add performance attribution if requested
            if include_attribution:
                attribution = await self.portfolio_analyzer.calculate_performance_attribution(period)
                result["attribution"] = {
                    "sector_allocation": {
                        sector: float(contrib) for sector, contrib in attribution.sector_contribution.items()
                    },
                    "security_selection": {
                        symbol: float(contrib) for symbol, contrib in attribution.security_contribution.items()
                    },
                    "top_contributors": [
                        {
                            "symbol": contrib.symbol,
                            "contribution": float(contrib.contribution),
                            "weight": float(contrib.weight)
                        }
                        for contrib in attribution.top_contributors[:10]
                    ],
                    "top_detractors": [
                        {
                            "symbol": contrib.symbol,
                            "contribution": float(contrib.contribution),
                            "weight": float(contrib.weight)
                        }
                        for contrib in attribution.top_detractors[:10]
                    ]
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error tracking performance: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def monitor_risk_metrics(
        self,
        risk_limits: Optional[Dict[str, float]] = None,
        include_stress_test: bool = False
    ) -> Dict[str, Any]:
        """
        Monitor real-time risk metrics and check against limits.
        
        Args:
            risk_limits: Custom risk limits to check against
            include_stress_test: Whether to include stress test results
            
        Returns:
            Dict containing risk monitoring data
        """
        try:
            # Calculate current risk metrics
            risk_metrics = await self.risk_manager.calculate_portfolio_risk()
            
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "risk_metrics": {
                    "portfolio_beta": float(risk_metrics.portfolio_beta),
                    "value_at_risk_1d": float(risk_metrics.value_at_risk),
                    "expected_shortfall": float(risk_metrics.expected_shortfall),
                    "volatility": float(risk_metrics.volatility),
                    "correlation_risk": float(risk_metrics.correlation_risk),
                    "concentration_risk": float(risk_metrics.concentration_risk),
                    "leverage_ratio": float(risk_metrics.leverage_ratio),
                    "liquidity_risk": float(risk_metrics.liquidity_risk)
                }
            }
            
            # Check against risk limits
            if risk_limits:
                violations = []
                for metric, limit in risk_limits.items():
                    if metric in result["risk_metrics"]:
                        current_value = result["risk_metrics"][metric]
                        if current_value > limit:
                            violations.append({
                                "metric": metric,
                                "current_value": current_value,
                                "limit": limit,
                                "excess": current_value - limit
                            })
                
                result["risk_limit_violations"] = violations
                result["risk_limits_breached"] = len(violations) > 0
            
            # Include stress test results if requested
            if include_stress_test:
                stress_results = await self.risk_manager.run_stress_test()
                result["stress_test"] = {
                    "market_crash_scenario": {
                        "portfolio_loss": float(stress_results.market_crash_loss),
                        "worst_position": stress_results.worst_position_crash,
                        "recovery_time_days": stress_results.estimated_recovery_days
                    },
                    "interest_rate_shock": {
                        "portfolio_impact": float(stress_results.interest_rate_impact),
                        "duration_risk": float(stress_results.duration_risk)
                    },
                    "liquidity_stress": {
                        "liquidation_cost": float(stress_results.liquidation_cost),
                        "time_to_liquidate_days": stress_results.liquidation_time_days
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error monitoring risk metrics: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _check_portfolio_alerts(
        self, 
        thresholds: Optional[Dict[str, float]] = None
    ) -> List[Alert]:
        """Check for portfolio alerts based on thresholds."""
        alerts = []
        
        try:
            # Use default thresholds if none provided
            if not thresholds:
                thresholds = {
                    "max_position_loss_percent": -10.0,
                    "max_portfolio_loss_percent": -5.0,
                    "min_cash_balance": 1000.0,
                    "max_concentration_percent": 20.0
                }
            
            # Get current portfolio state
            portfolio_state = await self.portfolio_monitor.get_portfolio_state()
            positions = await self.portfolio_monitor.get_positions()
            
            # Check portfolio-level alerts
            if "max_portfolio_loss_percent" in thresholds:
                if portfolio_state.day_change_percent < thresholds["max_portfolio_loss_percent"]:
                    alerts.append(Alert(
                        alert_type=AlertType.PORTFOLIO_LOSS,
                        message=f"Portfolio down {portfolio_state.day_change_percent:.2f}% today",
                        severity="HIGH",
                        value=portfolio_state.day_change_percent,
                        threshold=thresholds["max_portfolio_loss_percent"],
                        timestamp=datetime.now()
                    ))
            
            if "min_cash_balance" in thresholds:
                if portfolio_state.cash_balance < thresholds["min_cash_balance"]:
                    alerts.append(Alert(
                        alert_type=AlertType.LOW_CASH,
                        message=f"Cash balance below threshold: ${portfolio_state.cash_balance:.2f}",
                        severity="MEDIUM",
                        value=portfolio_state.cash_balance,
                        threshold=thresholds["min_cash_balance"],
                        timestamp=datetime.now()
                    ))
            
            # Check position-level alerts
            for position in positions:
                # Position loss alert
                if "max_position_loss_percent" in thresholds:
                    if position.unrealized_pnl_percent < thresholds["max_position_loss_percent"]:
                        alerts.append(Alert(
                            alert_type=AlertType.POSITION_LOSS,
                            message=f"{position.symbol} down {position.unrealized_pnl_percent:.2f}%",
                            severity="MEDIUM",
                            symbol=position.symbol,
                            value=position.unrealized_pnl_percent,
                            threshold=thresholds["max_position_loss_percent"],
                            timestamp=datetime.now()
                        ))
                
                # Concentration alert
                if "max_concentration_percent" in thresholds:
                    position_weight = (position.market_value / portfolio_state.total_value) * 100
                    if position_weight > thresholds["max_concentration_percent"]:
                        alerts.append(Alert(
                            alert_type=AlertType.HIGH_CONCENTRATION,
                            message=f"{position.symbol} represents {position_weight:.1f}% of portfolio",
                            severity="LOW",
                            symbol=position.symbol,
                            value=position_weight,
                            threshold=thresholds["max_concentration_percent"],
                            timestamp=datetime.now()
                        ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking portfolio alerts: {e}")
            return []