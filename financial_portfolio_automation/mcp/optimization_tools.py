"""
Portfolio optimization tools for MCP integration.

This module provides AI assistants with advanced portfolio optimization
and rebalancing capabilities.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

from ..analysis.portfolio_analyzer import PortfolioAnalyzer
from ..analysis.risk_manager import RiskManager
from ..strategy.backtester import Backtester
from ..models.core import Position, OptimizationResult, RebalanceRecommendation
from ..config.settings import Settings
from ..exceptions import ValidationError

logger = logging.getLogger(__name__)


class OptimizationTools:
    """MCP tools for portfolio optimization and rebalancing."""
    
    def __init__(self, settings: Settings):
        """Initialize optimization tools with required services."""
        self.settings = settings
        self.portfolio_analyzer = PortfolioAnalyzer(settings)
        self.risk_manager = RiskManager(settings)
        self.backtester = Backtester(settings)
        
    async def optimize_portfolio(
        self,
        target_symbols: List[str],
        optimization_objective: str = "sharpe",
        constraints: Optional[Dict[str, Any]] = None,
        lookback_days: int = 252
    ) -> Dict[str, Any]:
        """
        Optimize portfolio allocation using modern portfolio theory.
        
        Args:
            target_symbols: List of symbols to include in optimization
            optimization_objective: Objective function (sharpe, min_variance, max_return)
            constraints: Portfolio constraints (weights, sectors, etc.)
            lookback_days: Historical data lookback period
            
        Returns:
            Dict containing optimization results
        """
        try:
            if not target_symbols:
                raise ValidationError("Target symbols list cannot be empty")
                
            if optimization_objective not in ["sharpe", "min_variance", "max_return", "risk_parity"]:
                raise ValidationError(f"Invalid optimization objective: {optimization_objective}")
                
            if lookback_days < 30 or lookback_days > 1260:
                raise ValidationError("Lookback days must be between 30 and 1260")
            
            # Set default constraints if none provided
            if not constraints:
                constraints = {
                    "min_weight": 0.0,
                    "max_weight": 0.3,
                    "max_sector_weight": 0.4,
                    "min_positions": 5,
                    "max_positions": 20
                }
            
            # Run portfolio optimization
            optimization_result = await self.portfolio_analyzer.optimize_portfolio(
                symbols=target_symbols,
                objective=optimization_objective,
                constraints=constraints,
                lookback_days=lookback_days
            )
            
            # Calculate expected performance metrics
            expected_metrics = await self._calculate_expected_metrics(
                optimization_result.weights, lookback_days
            )
            
            # Get current portfolio for comparison
            from ..monitoring.portfolio_monitor import PortfolioMonitor
            monitor = PortfolioMonitor(self.settings)
            current_positions = await monitor.get_positions()
            current_weights = await self._calculate_current_weights(current_positions)
            
            result = {
                "success": True,
                "optimization_objective": optimization_objective,
                "lookback_days": lookback_days,
                "symbols_analyzed": len(target_symbols),
                "optimal_weights": {
                    symbol: float(weight) 
                    for symbol, weight in optimization_result.weights.items()
                    if weight > 0.001  # Filter out very small weights
                },
                "expected_metrics": {
                    "annual_return": float(expected_metrics.expected_return),
                    "annual_volatility": float(expected_metrics.expected_volatility),
                    "sharpe_ratio": float(expected_metrics.sharpe_ratio),
                    "max_drawdown": float(expected_metrics.max_drawdown),
                    "value_at_risk": float(expected_metrics.value_at_risk),
                    "diversification_ratio": float(expected_metrics.diversification_ratio)
                },
                "optimization_details": {
                    "convergence_status": optimization_result.convergence_status,
                    "iterations": optimization_result.iterations,
                    "objective_value": float(optimization_result.objective_value),
                    "constraints_satisfied": optimization_result.constraints_satisfied
                }
            }
            
            # Add comparison with current portfolio
            if current_weights:
                current_metrics = await self._calculate_expected_metrics(current_weights, lookback_days)
                result["current_vs_optimal"] = {
                    "current_sharpe": float(current_metrics.sharpe_ratio),
                    "optimal_sharpe": float(expected_metrics.sharpe_ratio),
                    "sharpe_improvement": float(expected_metrics.sharpe_ratio - current_metrics.sharpe_ratio),
                    "current_volatility": float(current_metrics.expected_volatility),
                    "optimal_volatility": float(expected_metrics.expected_volatility),
                    "volatility_reduction": float(current_metrics.expected_volatility - expected_metrics.expected_volatility)
                }
            
            # Add sector allocation breakdown
            sector_allocation = await self._calculate_sector_allocation(optimization_result.weights)
            result["sector_allocation"] = sector_allocation
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_rebalance_recommendations(
        self,
        target_weights: Optional[Dict[str, float]] = None,
        rebalance_threshold: float = 0.05,
        min_trade_size: float = 100.0
    ) -> Dict[str, Any]:
        """
        Generate portfolio rebalancing recommendations.
        
        Args:
            target_weights: Target portfolio weights (if None, uses strategic allocation)
            rebalance_threshold: Minimum deviation to trigger rebalancing
            min_trade_size: Minimum trade size in dollars
            
        Returns:
            Dict containing rebalancing recommendations
        """
        try:
            if rebalance_threshold <= 0 or rebalance_threshold > 0.5:
                raise ValidationError("Rebalance threshold must be between 0 and 0.5")
                
            if min_trade_size <= 0:
                raise ValidationError("Minimum trade size must be positive")
            
            # Get current portfolio state
            from ..monitoring.portfolio_monitor import PortfolioMonitor
            monitor = PortfolioMonitor(self.settings)
            portfolio_state = await monitor.get_portfolio_state()
            current_positions = await monitor.get_positions()
            
            # Calculate current weights
            current_weights = await self._calculate_current_weights(current_positions)
            
            # Use strategic allocation if no target weights provided
            if not target_weights:
                target_weights = await self._get_strategic_allocation()
            
            # Generate rebalancing recommendations
            rebalance_recs = await self.portfolio_analyzer.generate_rebalance_recommendations(
                current_weights=current_weights,
                target_weights=target_weights,
                portfolio_value=portfolio_state.total_value,
                cash_available=portfolio_state.cash_balance,
                rebalance_threshold=rebalance_threshold,
                min_trade_size=min_trade_size
            )
            
            result = {
                "success": True,
                "rebalance_needed": len(rebalance_recs.trades) > 0,
                "portfolio_value": float(portfolio_state.total_value),
                "cash_available": float(portfolio_state.cash_balance),
                "rebalance_threshold": rebalance_threshold,
                "current_weights": {k: float(v) for k, v in current_weights.items()},
                "target_weights": {k: float(v) for k, v in target_weights.items()},
                "weight_deviations": {},
                "recommended_trades": []
            }
            
            # Calculate weight deviations
            for symbol in set(list(current_weights.keys()) + list(target_weights.keys())):
                current_weight = current_weights.get(symbol, 0.0)
                target_weight = target_weights.get(symbol, 0.0)
                deviation = current_weight - target_weight
                
                if abs(deviation) > rebalance_threshold:
                    result["weight_deviations"][symbol] = {
                        "current_weight": float(current_weight),
                        "target_weight": float(target_weight),
                        "deviation": float(deviation),
                        "deviation_percent": float(deviation * 100)
                    }
            
            # Format trade recommendations
            total_trade_value = 0.0
            for trade in rebalance_recs.trades:
                trade_value = abs(float(trade.quantity * trade.estimated_price))
                total_trade_value += trade_value
                
                result["recommended_trades"].append({
                    "symbol": trade.symbol,
                    "action": trade.side.lower(),
                    "quantity": float(trade.quantity),
                    "estimated_price": float(trade.estimated_price),
                    "estimated_value": trade_value,
                    "current_weight": float(current_weights.get(trade.symbol, 0.0)),
                    "target_weight": float(target_weights.get(trade.symbol, 0.0)),
                    "priority": trade.priority,
                    "rationale": trade.rationale
                })
            
            result["rebalance_summary"] = {
                "total_trades": len(rebalance_recs.trades),
                "total_trade_value": total_trade_value,
                "estimated_commission": float(rebalance_recs.estimated_commission),
                "net_cash_impact": float(rebalance_recs.net_cash_impact),
                "tracking_error_reduction": float(rebalance_recs.tracking_error_reduction)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating rebalance recommendations: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def backtest_strategy(
        self,
        strategy_config: Dict[str, Any],
        start_date: str,
        end_date: str,
        initial_capital: float = 100000.0,
        benchmark: str = "SPY"
    ) -> Dict[str, Any]:
        """
        Backtest a trading strategy or portfolio allocation.
        
        Args:
            strategy_config: Strategy configuration
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            initial_capital: Initial capital for backtest
            benchmark: Benchmark symbol for comparison
            
        Returns:
            Dict containing backtest results
        """
        try:
            if not strategy_config:
                raise ValidationError("Strategy configuration is required")
                
            if initial_capital <= 0:
                raise ValidationError("Initial capital must be positive")
            
            # Parse dates
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise ValidationError("Dates must be in YYYY-MM-DD format")
                
            if start_dt >= end_dt:
                raise ValidationError("Start date must be before end date")
                
            if end_dt > datetime.now():
                raise ValidationError("End date cannot be in the future")
            
            # Run backtest
            backtest_result = await self.backtester.run_backtest(
                strategy_config=strategy_config,
                start_date=start_dt,
                end_date=end_dt,
                initial_capital=initial_capital,
                benchmark=benchmark
            )
            
            result = {
                "success": True,
                "backtest_period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "trading_days": backtest_result.trading_days,
                    "years": float(backtest_result.years)
                },
                "performance_metrics": {
                    "total_return": float(backtest_result.total_return),
                    "total_return_percent": float(backtest_result.total_return_percent),
                    "annualized_return": float(backtest_result.annualized_return),
                    "annualized_volatility": float(backtest_result.annualized_volatility),
                    "sharpe_ratio": float(backtest_result.sharpe_ratio),
                    "sortino_ratio": float(backtest_result.sortino_ratio),
                    "max_drawdown": float(backtest_result.max_drawdown),
                    "max_drawdown_duration": backtest_result.max_drawdown_duration,
                    "calmar_ratio": float(backtest_result.calmar_ratio),
                    "win_rate": float(backtest_result.win_rate),
                    "profit_factor": float(backtest_result.profit_factor)
                },
                "benchmark_comparison": {
                    "benchmark_symbol": benchmark,
                    "benchmark_return": float(backtest_result.benchmark_return),
                    "benchmark_volatility": float(backtest_result.benchmark_volatility),
                    "alpha": float(backtest_result.alpha),
                    "beta": float(backtest_result.beta),
                    "information_ratio": float(backtest_result.information_ratio),
                    "tracking_error": float(backtest_result.tracking_error)
                },
                "trade_statistics": {
                    "total_trades": backtest_result.total_trades,
                    "winning_trades": backtest_result.winning_trades,
                    "losing_trades": backtest_result.losing_trades,
                    "average_trade_return": float(backtest_result.average_trade_return),
                    "average_winning_trade": float(backtest_result.average_winning_trade),
                    "average_losing_trade": float(backtest_result.average_losing_trade),
                    "largest_winning_trade": float(backtest_result.largest_winning_trade),
                    "largest_losing_trade": float(backtest_result.largest_losing_trade)
                }
            }
            
            # Add monthly/yearly returns breakdown
            if hasattr(backtest_result, 'monthly_returns'):
                result["returns_breakdown"] = {
                    "monthly_returns": {
                        month.strftime("%Y-%m"): float(ret)
                        for month, ret in backtest_result.monthly_returns.items()
                    },
                    "yearly_returns": {
                        str(year): float(ret)
                        for year, ret in backtest_result.yearly_returns.items()
                    }
                }
            
            # Add drawdown periods
            if hasattr(backtest_result, 'drawdown_periods'):
                result["drawdown_analysis"] = {
                    "major_drawdowns": [
                        {
                            "start_date": dd.start_date.strftime("%Y-%m-%d"),
                            "end_date": dd.end_date.strftime("%Y-%m-%d"),
                            "duration_days": dd.duration_days,
                            "max_drawdown": float(dd.max_drawdown),
                            "recovery_date": dd.recovery_date.strftime("%Y-%m-%d") if dd.recovery_date else None
                        }
                        for dd in backtest_result.drawdown_periods[:5]  # Top 5 drawdowns
                    ]
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def optimize_risk_adjusted_returns(
        self,
        symbols: List[str],
        risk_target: float,
        return_target: Optional[float] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Optimize portfolio for risk-adjusted returns.
        
        Args:
            symbols: List of symbols to optimize
            risk_target: Target portfolio volatility
            return_target: Target portfolio return (optional)
            constraints: Additional constraints
            
        Returns:
            Dict containing risk-adjusted optimization results
        """
        try:
            if not symbols:
                raise ValidationError("Symbols list cannot be empty")
                
            if risk_target <= 0 or risk_target > 1.0:
                raise ValidationError("Risk target must be between 0 and 1.0")
                
            if return_target is not None and return_target <= 0:
                raise ValidationError("Return target must be positive")
            
            # Run risk-adjusted optimization
            optimization_result = await self.portfolio_analyzer.optimize_risk_adjusted_portfolio(
                symbols=symbols,
                risk_target=risk_target,
                return_target=return_target,
                constraints=constraints or {}
            )
            
            # Calculate efficient frontier points
            efficient_frontier = await self.portfolio_analyzer.calculate_efficient_frontier(
                symbols, num_points=20
            )
            
            result = {
                "success": True,
                "risk_target": risk_target,
                "return_target": return_target,
                "optimal_allocation": {
                    symbol: float(weight)
                    for symbol, weight in optimization_result.weights.items()
                    if weight > 0.001
                },
                "achieved_metrics": {
                    "expected_return": float(optimization_result.expected_return),
                    "expected_volatility": float(optimization_result.expected_volatility),
                    "sharpe_ratio": float(optimization_result.sharpe_ratio),
                    "risk_target_achieved": abs(float(optimization_result.expected_volatility) - risk_target) < 0.01
                },
                "efficient_frontier": [
                    {
                        "risk": float(point.risk),
                        "return": float(point.return_val),
                        "sharpe": float(point.sharpe)
                    }
                    for point in efficient_frontier
                ],
                "risk_decomposition": await self._calculate_risk_decomposition(optimization_result.weights)
            }
            
            # Add comparison with equal-weight portfolio
            equal_weights = {symbol: 1.0/len(symbols) for symbol in symbols}
            equal_weight_metrics = await self._calculate_expected_metrics(equal_weights, 252)
            
            result["equal_weight_comparison"] = {
                "equal_weight_return": float(equal_weight_metrics.expected_return),
                "equal_weight_volatility": float(equal_weight_metrics.expected_volatility),
                "equal_weight_sharpe": float(equal_weight_metrics.sharpe_ratio),
                "optimization_improvement": {
                    "return_improvement": float(optimization_result.expected_return - equal_weight_metrics.expected_return),
                    "risk_reduction": float(equal_weight_metrics.expected_volatility - optimization_result.expected_volatility),
                    "sharpe_improvement": float(optimization_result.sharpe_ratio - equal_weight_metrics.sharpe_ratio)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing risk-adjusted returns: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _calculate_current_weights(self, positions: List[Position]) -> Dict[str, float]:
        """Calculate current portfolio weights from positions."""
        total_value = sum(float(pos.market_value) for pos in positions)
        if total_value == 0:
            return {}
        
        return {
            pos.symbol: float(pos.market_value) / total_value
            for pos in positions
        }
    
    async def _calculate_expected_metrics(self, weights: Dict[str, float], lookback_days: int):
        """Calculate expected portfolio metrics from weights."""
        return await self.portfolio_analyzer.calculate_portfolio_metrics(
            weights, lookback_days
        )
    
    async def _get_strategic_allocation(self) -> Dict[str, float]:
        """Get strategic asset allocation from settings."""
        # This would typically come from user settings or a strategic allocation model
        # For now, return a default balanced allocation
        return {
            "SPY": 0.6,  # US Large Cap
            "EFA": 0.2,  # International Developed
            "EEM": 0.1,  # Emerging Markets
            "AGG": 0.1   # Bonds
        }
    
    async def _calculate_sector_allocation(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate sector allocation from symbol weights."""
        # This would map symbols to sectors and aggregate weights
        # Simplified implementation for now
        sector_mapping = await self.portfolio_analyzer.get_sector_mapping(list(weights.keys()))
        
        sector_weights = {}
        for symbol, weight in weights.items():
            sector = sector_mapping.get(symbol, "Unknown")
            sector_weights[sector] = sector_weights.get(sector, 0.0) + weight
        
        return sector_weights
    
    async def _calculate_risk_decomposition(self, weights: Dict[str, float]) -> Dict[str, Any]:
        """Calculate risk decomposition for the portfolio."""
        risk_decomp = await self.risk_manager.decompose_portfolio_risk(weights)
        
        return {
            "individual_contributions": {
                symbol: float(contrib)
                for symbol, contrib in risk_decomp.individual_contributions.items()
            },
            "diversification_benefit": float(risk_decomp.diversification_benefit),
            "concentration_risk": float(risk_decomp.concentration_risk)
        }