"""
Risk management tools for MCP integration.

This module provides AI assistants with comprehensive risk assessment
and management capabilities.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from ..analysis.risk_manager import RiskManager
from ..execution.risk_controller import RiskController
from ..models.core import Position, RiskAssessment, StressTestResult
from ..config.settings import Settings
from ..exceptions import ValidationError

logger = logging.getLogger(__name__)


class RiskTools:
    """MCP tools for risk assessment and management."""
    
    def __init__(self, settings: Settings):
        """Initialize risk tools with required services."""
        self.settings = settings
        self.risk_manager = RiskManager(settings)
        self.risk_controller = RiskController(settings)
        
    async def assess_portfolio_risk(
        self,
        include_stress_test: bool = False,
        confidence_level: float = 0.95,
        time_horizon_days: int = 1
    ) -> Dict[str, Any]:
        """
        Comprehensive portfolio risk assessment.
        
        Args:
            include_stress_test: Whether to include stress test scenarios
            confidence_level: Confidence level for VaR calculation
            time_horizon_days: Time horizon for risk metrics
            
        Returns:
            Dict containing comprehensive risk assessment
        """
        try:
            if not 0.5 <= confidence_level <= 0.99:
                raise ValidationError("Confidence level must be between 0.5 and 0.99")
                
            if time_horizon_days < 1 or time_horizon_days > 252:
                raise ValidationError("Time horizon must be between 1 and 252 days")
            
            # Calculate core risk metrics
            risk_metrics = await self.risk_manager.calculate_portfolio_risk(
                confidence_level=confidence_level,
                time_horizon=time_horizon_days
            )
            
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "confidence_level": confidence_level,
                "time_horizon_days": time_horizon_days,
                "risk_metrics": {
                    "value_at_risk": float(risk_metrics.value_at_risk),
                    "expected_shortfall": float(risk_metrics.expected_shortfall),
                    "portfolio_volatility": float(risk_metrics.volatility),
                    "portfolio_beta": float(risk_metrics.portfolio_beta),
                    "sharpe_ratio": float(risk_metrics.sharpe_ratio),
                    "sortino_ratio": float(risk_metrics.sortino_ratio),
                    "max_drawdown": float(risk_metrics.max_drawdown),
                    "correlation_risk": float(risk_metrics.correlation_risk),
                    "concentration_risk": float(risk_metrics.concentration_risk),
                    "leverage_ratio": float(risk_metrics.leverage_ratio),
                    "liquidity_risk": float(risk_metrics.liquidity_risk)
                }
            }
            
            # Add position-level risk breakdown
            position_risks = await self.risk_manager.calculate_position_risks()
            result["position_risks"] = [
                {
                    "symbol": pos_risk.symbol,
                    "position_var": float(pos_risk.value_at_risk),
                    "beta": float(pos_risk.beta),
                    "volatility": float(pos_risk.volatility),
                    "correlation_with_portfolio": float(pos_risk.correlation),
                    "contribution_to_portfolio_risk": float(pos_risk.risk_contribution),
                    "liquidity_score": float(pos_risk.liquidity_score),
                    "concentration_weight": float(pos_risk.weight)
                }
                for pos_risk in position_risks
            ]
            
            # Add sector and geographic risk breakdown
            sector_risks = await self.risk_manager.calculate_sector_risks()
            result["sector_risks"] = {
                sector: {
                    "weight": float(risk.weight),
                    "volatility": float(risk.volatility),
                    "beta": float(risk.beta),
                    "risk_contribution": float(risk.risk_contribution)
                }
                for sector, risk in sector_risks.items()
            }
            
            # Include stress test if requested
            if include_stress_test:
                stress_results = await self.risk_manager.run_stress_test()
                result["stress_test"] = await self._format_stress_test_results(stress_results)
            
            # Add risk limit violations
            violations = await self._check_risk_limit_violations(risk_metrics)
            if violations:
                result["risk_violations"] = violations
            
            return result
            
        except Exception as e:
            logger.error(f"Error assessing portfolio risk: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_trade_risk(
        self,
        symbol: str,
        quantity: float,
        side: str,
        current_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Validate the risk impact of a proposed trade.
        
        Args:
            symbol: Stock symbol for the trade
            quantity: Number of shares
            side: Trade side (buy/sell)
            current_price: Current market price (optional)
            
        Returns:
            Dict containing trade risk validation results
        """
        try:
            if not symbol or not isinstance(symbol, str):
                raise ValidationError("Symbol must be a non-empty string")
                
            if quantity <= 0:
                raise ValidationError("Quantity must be positive")
                
            if side not in ["buy", "sell"]:
                raise ValidationError("Side must be 'buy' or 'sell'")
            
            # Create a hypothetical order for risk assessment
            from ..models.core import Order, OrderType
            order = Order(
                symbol=symbol,
                quantity=Decimal(str(quantity)),
                order_type=OrderType.MARKET,
                side=side.upper()
            )
            
            # Validate with risk controller
            risk_check = await self.risk_controller.validate_order(order)
            
            # Calculate impact on portfolio risk
            risk_impact = await self.risk_manager.calculate_trade_risk_impact(
                symbol, quantity, side, current_price
            )
            
            result = {
                "success": True,
                "trade_approved": risk_check.approved,
                "risk_check_reason": risk_check.reason,
                "trade_details": {
                    "symbol": symbol,
                    "quantity": quantity,
                    "side": side,
                    "estimated_value": float(risk_impact.trade_value),
                    "current_price": float(current_price) if current_price else None
                },
                "risk_impact": {
                    "portfolio_var_change": float(risk_impact.var_change),
                    "portfolio_var_change_percent": float(risk_impact.var_change_percent),
                    "concentration_change": float(risk_impact.concentration_change),
                    "beta_change": float(risk_impact.beta_change),
                    "correlation_impact": float(risk_impact.correlation_impact),
                    "liquidity_impact": float(risk_impact.liquidity_impact)
                },
                "position_limits": {
                    "current_position_value": float(risk_impact.current_position_value),
                    "new_position_value": float(risk_impact.new_position_value),
                    "position_limit": float(risk_impact.position_limit),
                    "limit_utilization_percent": float(risk_impact.limit_utilization)
                }
            }
            
            # Add warnings if any risk thresholds are approached
            warnings = []
            if risk_impact.limit_utilization > 0.8:
                warnings.append("Position limit utilization above 80%")
            if abs(risk_impact.var_change_percent) > 0.05:
                warnings.append("Trade would increase portfolio VaR by more than 5%")
            if risk_impact.concentration_change > 0.02:
                warnings.append("Trade would increase concentration risk")
                
            if warnings:
                result["warnings"] = warnings
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating trade risk: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_scenario_analysis(
        self,
        scenarios: List[Dict[str, Any]],
        include_correlations: bool = True
    ) -> Dict[str, Any]:
        """
        Run scenario analysis on the portfolio.
        
        Args:
            scenarios: List of scenario definitions
            include_correlations: Whether to include correlation analysis
            
        Returns:
            Dict containing scenario analysis results
        """
        try:
            if not scenarios:
                raise ValidationError("At least one scenario must be provided")
            
            # Validate scenario format
            for i, scenario in enumerate(scenarios):
                if "name" not in scenario:
                    raise ValidationError(f"Scenario {i} missing 'name' field")
                if "market_moves" not in scenario:
                    raise ValidationError(f"Scenario {i} missing 'market_moves' field")
            
            results = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "scenarios_analyzed": len(scenarios),
                "scenario_results": []
            }
            
            for scenario in scenarios:
                scenario_result = await self.risk_manager.run_scenario(
                    scenario["name"],
                    scenario["market_moves"],
                    scenario.get("correlation_shock", 0.0)
                )
                
                results["scenario_results"].append({
                    "scenario_name": scenario["name"],
                    "market_moves": scenario["market_moves"],
                    "portfolio_impact": {
                        "total_pnl": float(scenario_result.total_pnl),
                        "total_pnl_percent": float(scenario_result.total_pnl_percent),
                        "worst_position": scenario_result.worst_position,
                        "worst_position_pnl": float(scenario_result.worst_position_pnl),
                        "best_position": scenario_result.best_position,
                        "best_position_pnl": float(scenario_result.best_position_pnl)
                    },
                    "position_impacts": [
                        {
                            "symbol": pos.symbol,
                            "pnl": float(pos.pnl),
                            "pnl_percent": float(pos.pnl_percent),
                            "contribution_to_total": float(pos.contribution)
                        }
                        for pos in scenario_result.position_impacts
                    ]
                })
            
            # Add correlation analysis if requested
            if include_correlations:
                correlation_analysis = await self.risk_manager.analyze_scenario_correlations(scenarios)
                results["correlation_analysis"] = {
                    "average_correlation": float(correlation_analysis.average_correlation),
                    "correlation_range": {
                        "min": float(correlation_analysis.min_correlation),
                        "max": float(correlation_analysis.max_correlation)
                    },
                    "diversification_ratio": float(correlation_analysis.diversification_ratio),
                    "correlation_clusters": correlation_analysis.correlation_clusters
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Error running scenario analysis: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def calculate_optimal_position_sizes(
        self,
        target_symbols: List[str],
        risk_budget: float,
        optimization_method: str = "mean_variance"
    ) -> Dict[str, Any]:
        """
        Calculate optimal position sizes based on risk budget.
        
        Args:
            target_symbols: List of symbols to optimize
            risk_budget: Total risk budget (as portfolio VaR)
            optimization_method: Optimization method (mean_variance, risk_parity, min_variance)
            
        Returns:
            Dict containing optimal position sizes
        """
        try:
            if not target_symbols:
                raise ValidationError("Target symbols list cannot be empty")
                
            if risk_budget <= 0:
                raise ValidationError("Risk budget must be positive")
                
            if optimization_method not in ["mean_variance", "risk_parity", "min_variance"]:
                raise ValidationError(f"Invalid optimization method: {optimization_method}")
            
            # Calculate optimal weights
            optimization_result = await self.risk_manager.optimize_portfolio(
                target_symbols,
                risk_budget,
                optimization_method
            )
            
            # Get current portfolio value for position sizing
            from ..monitoring.portfolio_monitor import PortfolioMonitor
            monitor = PortfolioMonitor(self.settings)
            portfolio_state = await monitor.get_portfolio_state()
            
            result = {
                "success": True,
                "optimization_method": optimization_method,
                "risk_budget": risk_budget,
                "portfolio_value": float(portfolio_state.total_value),
                "optimal_weights": {
                    symbol: float(weight) 
                    for symbol, weight in optimization_result.weights.items()
                },
                "position_sizes": {},
                "expected_metrics": {
                    "expected_return": float(optimization_result.expected_return),
                    "expected_volatility": float(optimization_result.expected_volatility),
                    "expected_sharpe": float(optimization_result.expected_sharpe),
                    "expected_var": float(optimization_result.expected_var)
                }
            }
            
            # Calculate actual position sizes in shares and dollars
            for symbol, weight in optimization_result.weights.items():
                target_value = float(portfolio_state.total_value) * weight
                
                # Get current price for share calculation
                from ..api.market_data_client import MarketDataClient
                market_client = MarketDataClient(self.settings)
                current_price = await market_client.get_current_price(symbol)
                
                if current_price:
                    shares = int(target_value / float(current_price))
                    actual_value = shares * float(current_price)
                    
                    result["position_sizes"][symbol] = {
                        "target_weight": float(weight),
                        "target_value": target_value,
                        "shares": shares,
                        "actual_value": actual_value,
                        "current_price": float(current_price)
                    }
            
            # Add risk decomposition
            risk_decomposition = await self.risk_manager.decompose_portfolio_risk(
                optimization_result.weights
            )
            result["risk_decomposition"] = {
                "individual_contributions": {
                    symbol: float(contrib)
                    for symbol, contrib in risk_decomposition.individual_contributions.items()
                },
                "interaction_effects": {
                    f"{s1}-{s2}": float(effect)
                    for (s1, s2), effect in risk_decomposition.interaction_effects.items()
                },
                "diversification_benefit": float(risk_decomposition.diversification_benefit)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating optimal position sizes: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _format_stress_test_results(self, stress_results: StressTestResult) -> Dict[str, Any]:
        """Format stress test results for API response."""
        return {
            "market_crash_scenario": {
                "portfolio_loss": float(stress_results.market_crash_loss),
                "portfolio_loss_percent": float(stress_results.market_crash_loss_percent),
                "worst_position": stress_results.worst_position_crash,
                "worst_position_loss": float(stress_results.worst_position_loss),
                "recovery_time_estimate_days": stress_results.estimated_recovery_days
            },
            "interest_rate_shock": {
                "rate_increase_100bp": float(stress_results.interest_rate_impact_100bp),
                "rate_decrease_100bp": float(stress_results.interest_rate_impact_neg_100bp),
                "duration_risk": float(stress_results.duration_risk)
            },
            "liquidity_stress": {
                "liquidation_cost_percent": float(stress_results.liquidation_cost_percent),
                "time_to_liquidate_days": stress_results.liquidation_time_days,
                "fire_sale_discount": float(stress_results.fire_sale_discount)
            },
            "correlation_breakdown": {
                "normal_correlation": float(stress_results.normal_correlation),
                "stress_correlation": float(stress_results.stress_correlation),
                "correlation_increase": float(stress_results.correlation_increase)
            }
        }
    
    async def _check_risk_limit_violations(self, risk_metrics) -> List[Dict[str, Any]]:
        """Check for risk limit violations."""
        violations = []
        
        # Get risk limits from settings
        risk_limits = self.settings.risk_limits
        
        # Check VaR limit
        if hasattr(risk_limits, 'max_portfolio_var') and risk_limits.max_portfolio_var:
            if risk_metrics.value_at_risk > risk_limits.max_portfolio_var:
                violations.append({
                    "metric": "value_at_risk",
                    "current_value": float(risk_metrics.value_at_risk),
                    "limit": float(risk_limits.max_portfolio_var),
                    "excess": float(risk_metrics.value_at_risk - risk_limits.max_portfolio_var),
                    "severity": "HIGH"
                })
        
        # Check concentration limit
        if hasattr(risk_limits, 'max_concentration') and risk_limits.max_concentration:
            if risk_metrics.concentration_risk > risk_limits.max_concentration:
                violations.append({
                    "metric": "concentration_risk",
                    "current_value": float(risk_metrics.concentration_risk),
                    "limit": float(risk_limits.max_concentration),
                    "excess": float(risk_metrics.concentration_risk - risk_limits.max_concentration),
                    "severity": "MEDIUM"
                })
        
        # Check leverage limit
        if hasattr(risk_limits, 'max_leverage') and risk_limits.max_leverage:
            if risk_metrics.leverage_ratio > risk_limits.max_leverage:
                violations.append({
                    "metric": "leverage_ratio",
                    "current_value": float(risk_metrics.leverage_ratio),
                    "limit": float(risk_limits.max_leverage),
                    "excess": float(risk_metrics.leverage_ratio - risk_limits.max_leverage),
                    "severity": "HIGH"
                })
        
        return violations