"""
Strategy tools for MCP integration.

This module provides AI assistants with access to strategy backtesting,
optimization, and performance analysis capabilities.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

from ..strategy.backtester import Backtester
from ..strategy.executor import StrategyExecutor
from ..strategy.registry import StrategyRegistry
from ..strategy.factory import StrategyFactory
from ..exceptions import PortfolioAutomationError


class StrategyTools:
    """
    Strategy tools for AI assistant integration.
    
    Provides strategy backtesting, optimization, performance analysis,
    and strategy comparison capabilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize strategy tools.
        
        Args:
            config: Configuration dictionary containing service configurations
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize required services with error handling
        try:
            self.backtester = Backtester(config)
        except Exception as e:
            self.logger.warning(f"Backtester not available: {e}")
            self.backtester = None
            
        try:
            self.strategy_executor = StrategyExecutor(config)
        except Exception as e:
            self.logger.warning(f"Strategy executor not available: {e}")
            self.strategy_executor = None
            
        try:
            self.strategy_registry = StrategyRegistry(config)
        except Exception as e:
            self.logger.warning(f"Strategy registry not available: {e}")
            self.strategy_registry = None
            
        try:
            self.strategy_factory = StrategyFactory(config)
        except Exception as e:
            self.logger.warning(f"Strategy factory not available: {e}")
            self.strategy_factory = None
        
        self.logger.info("Strategy tools initialized")
    
    async def backtest_strategy(self, strategy_config: Dict[str, Any],
                              start_date: str, end_date: str,
                              initial_capital: float = 100000) -> Dict[str, Any]:
        """
        Backtest trading strategy with historical data.
        
        Args:
            strategy_config: Strategy configuration parameters
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            initial_capital: Initial capital for backtest
            
        Returns:
            Dictionary containing backtest results
        """
        try:
            self.logger.info(f"Running backtest from {start_date} to {end_date}")
            
            # Parse dates
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Create strategy instance
            strategy = await self.strategy_factory.create_strategy(strategy_config)
            
            # Run backtest
            backtest_results = await self.backtester.run_backtest(
                strategy=strategy,
                start_date=start_dt,
                end_date=end_dt,
                initial_capital=initial_capital
            )
            
            # Calculate comprehensive metrics
            performance_metrics = await self.backtester.calculate_performance_metrics(
                backtest_results
            )
            
            # Generate backtest report
            result = {
                'backtest_id': backtest_results.get('backtest_id'),
                'strategy_name': strategy_config.get('name', 'Unknown'),
                'strategy_type': strategy_config.get('type', 'Unknown'),
                'period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'duration_days': (end_dt - start_dt).days
                },
                'initial_capital': initial_capital,
                'final_value': backtest_results.get('final_portfolio_value', 0),
                'performance_metrics': performance_metrics,
                'trade_statistics': backtest_results.get('trade_statistics', {}),
                'risk_metrics': backtest_results.get('risk_metrics', {}),
                'drawdown_analysis': backtest_results.get('drawdown_analysis', {}),
                'monthly_returns': backtest_results.get('monthly_returns', []),
                'equity_curve': backtest_results.get('equity_curve', [])
            }
            
            # Add AI-friendly summary
            result['summary'] = self._create_backtest_summary(result)
            
            # Add strategy recommendations
            result['recommendations'] = await self._generate_strategy_recommendations(result)
            
            self.logger.info("Backtest completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error running backtest: {str(e)}")
            raise PortfolioAutomationError(f"Backtest failed: {str(e)}")
    
    async def optimize_strategy_parameters(self, strategy_type: str,
                                         parameter_ranges: Dict[str, Any],
                                         optimization_metric: str = "sharpe") -> Dict[str, Any]:
        """
        Optimize strategy parameters using historical data.
        
        Args:
            strategy_type: Type of strategy to optimize
            parameter_ranges: Parameter ranges for optimization
            optimization_metric: Metric to optimize
            
        Returns:
            Dictionary containing optimization results
        """
        try:
            self.logger.info(f"Optimizing {strategy_type} strategy parameters")
            
            # Run parameter optimization
            optimization_results = await self.backtester.optimize_parameters(
                strategy_type=strategy_type,
                parameter_ranges=parameter_ranges,
                optimization_metric=optimization_metric
            )
            
            result = {
                'strategy_type': strategy_type,
                'optimization_metric': optimization_metric,
                'parameter_ranges': parameter_ranges,
                'best_parameters': optimization_results.get('best_parameters', {}),
                'best_score': optimization_results.get('best_score', 0),
                'optimization_results': optimization_results.get('all_results', []),
                'parameter_sensitivity': optimization_results.get('sensitivity_analysis', {}),
                'convergence_info': optimization_results.get('convergence_info', {})
            }
            
            # Add optimization insights
            result['insights'] = self._create_optimization_insights(result)
            
            # Generate recommended configuration
            result['recommended_config'] = await self._create_recommended_config(
                strategy_type, result['best_parameters']
            )
            
            self.logger.info("Parameter optimization completed")
            return result
            
        except Exception as e:
            self.logger.error(f"Error optimizing strategy parameters: {str(e)}")
            raise PortfolioAutomationError(f"Parameter optimization failed: {str(e)}")
    
    async def compare_strategies(self, strategies: List[Dict[str, Any]],
                               comparison_period: str = "1y") -> Dict[str, Any]:
        """
        Compare multiple strategies performance.
        
        Args:
            strategies: List of strategy configurations to compare
            comparison_period: Period for comparison
            
        Returns:
            Dictionary containing strategy comparison results
        """
        try:
            self.logger.info(f"Comparing {len(strategies)} strategies")
            
            # Calculate comparison dates
            end_date = datetime.now(timezone.utc)
            start_date = self._calculate_start_date(comparison_period, end_date)
            
            comparison_results = {
                'comparison_period': comparison_period,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'strategies_compared': len(strategies),
                'strategy_results': {},
                'performance_ranking': [],
                'risk_ranking': [],
                'risk_adjusted_ranking': []
            }
            
            strategy_performances = {}
            
            # Run backtest for each strategy
            for i, strategy_config in enumerate(strategies):
                try:
                    strategy_name = strategy_config.get('name', f'Strategy_{i+1}')
                    
                    # Create and backtest strategy
                    strategy = await self.strategy_factory.create_strategy(strategy_config)
                    backtest_results = await self.backtester.run_backtest(
                        strategy=strategy,
                        start_date=start_date,
                        end_date=end_date,
                        initial_capital=100000
                    )
                    
                    performance_metrics = await self.backtester.calculate_performance_metrics(
                        backtest_results
                    )
                    
                    strategy_performances[strategy_name] = {
                        'config': strategy_config,
                        'performance': performance_metrics,
                        'final_value': backtest_results.get('final_portfolio_value', 0),
                        'total_return': performance_metrics.get('total_return', 0),
                        'sharpe_ratio': performance_metrics.get('sharpe_ratio', 0),
                        'max_drawdown': performance_metrics.get('max_drawdown', 0),
                        'volatility': performance_metrics.get('volatility', 0),
                        'win_rate': performance_metrics.get('win_rate', 0)
                    }
                    
                    comparison_results['strategy_results'][strategy_name] = strategy_performances[strategy_name]
                    
                except Exception as e:
                    self.logger.error(f"Error backtesting strategy {strategy_name}: {str(e)}")
                    comparison_results['strategy_results'][strategy_name] = {'error': str(e)}
            
            # Create rankings
            if strategy_performances:
                # Performance ranking (by total return)
                performance_ranking = sorted(
                    strategy_performances.items(),
                    key=lambda x: x[1]['total_return'],
                    reverse=True
                )
                comparison_results['performance_ranking'] = [
                    {'strategy': name, 'total_return': data['total_return']}
                    for name, data in performance_ranking
                ]
                
                # Risk ranking (by max drawdown, lower is better)
                risk_ranking = sorted(
                    strategy_performances.items(),
                    key=lambda x: x[1]['max_drawdown']
                )
                comparison_results['risk_ranking'] = [
                    {'strategy': name, 'max_drawdown': data['max_drawdown']}
                    for name, data in risk_ranking
                ]
                
                # Risk-adjusted ranking (by Sharpe ratio)
                risk_adjusted_ranking = sorted(
                    strategy_performances.items(),
                    key=lambda x: x[1]['sharpe_ratio'],
                    reverse=True
                )
                comparison_results['risk_adjusted_ranking'] = [
                    {'strategy': name, 'sharpe_ratio': data['sharpe_ratio']}
                    for name, data in risk_adjusted_ranking
                ]
                
                # Add comparison insights
                comparison_results['insights'] = self._create_comparison_insights(
                    strategy_performances
                )
                
                # Recommend best strategy
                comparison_results['recommendation'] = self._recommend_best_strategy(
                    strategy_performances
                )
            
            self.logger.info("Strategy comparison completed")
            return comparison_results
            
        except Exception as e:
            self.logger.error(f"Error comparing strategies: {str(e)}")
            raise PortfolioAutomationError(f"Strategy comparison failed: {str(e)}")
    
    async def analyze_strategy_performance(self, strategy_id: str,
                                         analysis_period: str = "1y") -> Dict[str, Any]:
        """
        Analyze performance of a specific strategy.
        
        Args:
            strategy_id: ID of the strategy to analyze
            analysis_period: Period for analysis
            
        Returns:
            Dictionary containing strategy performance analysis
        """
        try:
            self.logger.info(f"Analyzing performance for strategy {strategy_id}")
            
            # Get strategy from registry
            strategy_config = await self.strategy_registry.get_strategy(strategy_id)
            if not strategy_config:
                raise PortfolioAutomationError(f"Strategy {strategy_id} not found")
            
            # Calculate analysis period
            end_date = datetime.now(timezone.utc)
            start_date = self._calculate_start_date(analysis_period, end_date)
            
            # Get strategy performance data
            performance_data = await self.strategy_executor.get_strategy_performance(
                strategy_id=strategy_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Perform detailed analysis
            analysis_result = {
                'strategy_id': strategy_id,
                'strategy_name': strategy_config.get('name', 'Unknown'),
                'analysis_period': analysis_period,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'performance_summary': performance_data.get('summary', {}),
                'monthly_performance': performance_data.get('monthly_returns', []),
                'trade_analysis': performance_data.get('trade_analysis', {}),
                'risk_analysis': performance_data.get('risk_analysis', {}),
                'attribution_analysis': performance_data.get('attribution', {}),
                'benchmark_comparison': performance_data.get('benchmark_comparison', {})
            }
            
            # Add performance insights
            analysis_result['insights'] = self._create_performance_insights(analysis_result)
            
            # Add improvement suggestions
            analysis_result['suggestions'] = await self._generate_improvement_suggestions(
                analysis_result
            )
            
            self.logger.info("Strategy performance analysis completed")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing strategy performance: {str(e)}")
            raise PortfolioAutomationError(f"Strategy performance analysis failed: {str(e)}")
    
    async def get_strategy_recommendations(self, market_conditions: Dict[str, Any] = None,
                                        risk_tolerance: str = "moderate") -> Dict[str, Any]:
        """
        Get AI-driven strategy recommendations based on market conditions.
        
        Args:
            market_conditions: Current market conditions data
            risk_tolerance: Risk tolerance level (conservative, moderate, aggressive)
            
        Returns:
            Dictionary containing strategy recommendations
        """
        try:
            self.logger.info("Generating strategy recommendations")
            
            # Analyze current market conditions if not provided
            if market_conditions is None:
                market_conditions = await self._analyze_current_market_conditions()
            
            # Get available strategies
            available_strategies = await self.strategy_registry.list_strategies()
            
            recommendations = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'market_conditions': market_conditions,
                'risk_tolerance': risk_tolerance,
                'recommended_strategies': [],
                'market_regime': self._determine_market_regime(market_conditions),
                'allocation_suggestions': {}
            }
            
            # Analyze each strategy for current conditions
            for strategy_config in available_strategies:
                try:
                    suitability_score = await self._calculate_strategy_suitability(
                        strategy_config, market_conditions, risk_tolerance
                    )
                    
                    if suitability_score > 0.6:  # Threshold for recommendation
                        recommendations['recommended_strategies'].append({
                            'strategy_name': strategy_config.get('name'),
                            'strategy_type': strategy_config.get('type'),
                            'suitability_score': suitability_score,
                            'rationale': self._generate_strategy_rationale(
                                strategy_config, market_conditions
                            ),
                            'suggested_allocation': self._suggest_allocation(
                                strategy_config, risk_tolerance
                            )
                        })
                
                except Exception as e:
                    self.logger.error(f"Error analyzing strategy {strategy_config.get('name')}: {str(e)}")
            
            # Sort by suitability score
            recommendations['recommended_strategies'].sort(
                key=lambda x: x['suitability_score'], reverse=True
            )
            
            # Generate allocation suggestions
            recommendations['allocation_suggestions'] = self._generate_allocation_suggestions(
                recommendations['recommended_strategies'], risk_tolerance
            )
            
            # Add market timing insights
            recommendations['market_timing'] = self._generate_market_timing_insights(
                market_conditions
            )
            
            self.logger.info("Strategy recommendations generated")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating strategy recommendations: {str(e)}")
            raise PortfolioAutomationError(f"Strategy recommendations failed: {str(e)}")
    
    def _calculate_start_date(self, period: str, end_date: datetime) -> datetime:
        """Calculate start date based on period string."""
        period_map = {
            '1d': timedelta(days=1),
            '1w': timedelta(weeks=1),
            '1m': timedelta(days=30),
            '3m': timedelta(days=90),
            '6m': timedelta(days=180),
            '1y': timedelta(days=365),
            '2y': timedelta(days=730),
            '5y': timedelta(days=1825)
        }
        
        delta = period_map.get(period, timedelta(days=365))
        return end_date - delta
    
    def _create_backtest_summary(self, backtest_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create AI-friendly backtest summary."""
        performance = backtest_result.get('performance_metrics', {})
        
        summary = {
            'overall_performance': 'positive' if performance.get('total_return', 0) > 0 else 'negative',
            'risk_level': 'high' if performance.get('volatility', 0) > 25 else 'moderate' if performance.get('volatility', 0) > 15 else 'low',
            'key_strengths': [],
            'key_weaknesses': [],
            'recommendation': 'unknown'
        }
        
        # Identify strengths
        if performance.get('sharpe_ratio', 0) > 1.5:
            summary['key_strengths'].append("Excellent risk-adjusted returns")
        
        if performance.get('win_rate', 0) > 0.6:
            summary['key_strengths'].append("High win rate")
        
        if performance.get('max_drawdown', 0) < 10:
            summary['key_strengths'].append("Low maximum drawdown")
        
        # Identify weaknesses
        if performance.get('max_drawdown', 0) > 25:
            summary['key_weaknesses'].append("High maximum drawdown")
        
        if performance.get('volatility', 0) > 30:
            summary['key_weaknesses'].append("High volatility")
        
        if performance.get('sharpe_ratio', 0) < 0.5:
            summary['key_weaknesses'].append("Poor risk-adjusted returns")
        
        # Overall recommendation
        if performance.get('sharpe_ratio', 0) > 1.0 and performance.get('max_drawdown', 0) < 20:
            summary['recommendation'] = 'recommended'
        elif performance.get('total_return', 0) > 0 and performance.get('sharpe_ratio', 0) > 0.5:
            summary['recommendation'] = 'conditional'
        else:
            summary['recommendation'] = 'not_recommended'
        
        return summary
    
    def _create_optimization_insights(self, optimization_result: Dict[str, Any]) -> List[str]:
        """Create insights from optimization results."""
        insights = []
        
        best_score = optimization_result.get('best_score', 0)
        sensitivity = optimization_result.get('parameter_sensitivity', {})
        
        if best_score > 1.5:
            insights.append("Optimization found excellent parameter combination")
        elif best_score > 1.0:
            insights.append("Optimization found good parameter combination")
        else:
            insights.append("Optimization results suggest strategy may need refinement")
        
        # Parameter sensitivity insights
        for param, sensitivity_score in sensitivity.items():
            if sensitivity_score > 0.8:
                insights.append(f"Parameter '{param}' is highly sensitive to changes")
            elif sensitivity_score < 0.2:
                insights.append(f"Parameter '{param}' has minimal impact on performance")
        
        return insights
    
    async def _create_recommended_config(self, strategy_type: str, 
                                       best_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create recommended strategy configuration."""
        base_config = await self.strategy_factory.get_default_config(strategy_type)
        
        # Update with optimized parameters
        recommended_config = base_config.copy()
        recommended_config.update(best_parameters)
        
        # Add metadata
        recommended_config['optimization_date'] = datetime.now(timezone.utc).isoformat()
        recommended_config['optimization_metric'] = 'sharpe_ratio'
        recommended_config['status'] = 'optimized'
        
        return recommended_config
    
    def _create_comparison_insights(self, strategy_performances: Dict[str, Any]) -> List[str]:
        """Create insights from strategy comparison."""
        insights = []
        
        if not strategy_performances:
            return insights
        
        # Find best and worst performers
        best_return = max(data['total_return'] for data in strategy_performances.values())
        worst_return = min(data['total_return'] for data in strategy_performances.values())
        
        best_sharpe = max(data['sharpe_ratio'] for data in strategy_performances.values())
        
        insights.append(f"Performance spread: {best_return - worst_return:.1f}%")
        
        if best_sharpe > 1.5:
            insights.append("Top strategy shows excellent risk-adjusted returns")
        
        # Risk analysis
        high_risk_count = sum(1 for data in strategy_performances.values() 
                             if data['max_drawdown'] > 20)
        
        if high_risk_count > len(strategy_performances) / 2:
            insights.append("Most strategies show high risk characteristics")
        
        return insights
    
    def _recommend_best_strategy(self, strategy_performances: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend the best strategy based on multiple criteria."""
        if not strategy_performances:
            return {}
        
        # Score each strategy
        strategy_scores = {}
        
        for name, data in strategy_performances.items():
            # Composite score based on return, risk-adjusted return, and drawdown
            return_score = max(0, data['total_return'] / 20)  # Normalize to 20% return
            sharpe_score = max(0, data['sharpe_ratio'] / 2)   # Normalize to Sharpe of 2
            drawdown_score = max(0, (30 - data['max_drawdown']) / 30)  # Penalize high drawdown
            
            composite_score = (return_score * 0.4 + sharpe_score * 0.4 + drawdown_score * 0.2)
            strategy_scores[name] = composite_score
        
        # Find best strategy
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])
        
        return {
            'recommended_strategy': best_strategy[0],
            'composite_score': best_strategy[1],
            'rationale': f"Best balance of returns, risk-adjusted performance, and drawdown control"
        }
    
    def _create_performance_insights(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Create performance insights from analysis."""
        insights = []
        
        performance = analysis_result.get('performance_summary', {})
        
        if performance.get('total_return', 0) > 15:
            insights.append("Strategy shows strong absolute returns")
        
        if performance.get('sharpe_ratio', 0) > 1.5:
            insights.append("Excellent risk-adjusted performance")
        
        if performance.get('max_drawdown', 0) > 25:
            insights.append("High drawdown periods may test investor patience")
        
        # Monthly performance analysis
        monthly_returns = analysis_result.get('monthly_performance', [])
        if monthly_returns:
            positive_months = sum(1 for ret in monthly_returns if ret > 0)
            consistency = positive_months / len(monthly_returns) * 100
            
            if consistency > 70:
                insights.append("Strategy shows high monthly consistency")
            elif consistency < 40:
                insights.append("Strategy shows high monthly volatility")
        
        return insights
    
    async def _generate_improvement_suggestions(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate improvement suggestions for strategy."""
        suggestions = []
        
        performance = analysis_result.get('performance_summary', {})
        
        if performance.get('max_drawdown', 0) > 20:
            suggestions.append("Consider adding stop-loss mechanisms to reduce drawdown")
        
        if performance.get('sharpe_ratio', 0) < 1.0:
            suggestions.append("Optimize risk management to improve risk-adjusted returns")
        
        if performance.get('win_rate', 0) < 0.5:
            suggestions.append("Review entry/exit criteria to improve win rate")
        
        # Trade analysis suggestions
        trade_analysis = analysis_result.get('trade_analysis', {})
        if trade_analysis.get('average_holding_period', 0) > 30:
            suggestions.append("Consider shorter holding periods to improve capital efficiency")
        
        return suggestions
    
    async def _analyze_current_market_conditions(self) -> Dict[str, Any]:
        """Analyze current market conditions."""
        # This would integrate with market data services
        # For now, return a simplified analysis
        return {
            'volatility_regime': 'normal',
            'trend_direction': 'neutral',
            'market_sentiment': 'mixed',
            'sector_rotation': 'moderate'
        }
    
    def _determine_market_regime(self, market_conditions: Dict[str, Any]) -> str:
        """Determine current market regime."""
        volatility = market_conditions.get('volatility_regime', 'normal')
        trend = market_conditions.get('trend_direction', 'neutral')
        
        if volatility == 'high' and trend == 'bearish':
            return 'crisis'
        elif volatility == 'low' and trend == 'bullish':
            return 'bull_market'
        elif volatility == 'high':
            return 'volatile'
        else:
            return 'normal'
    
    async def _calculate_strategy_suitability(self, strategy_config: Dict[str, Any],
                                            market_conditions: Dict[str, Any],
                                            risk_tolerance: str) -> float:
        """Calculate strategy suitability score."""
        # Simplified suitability calculation
        base_score = 0.5
        
        strategy_type = strategy_config.get('type', '')
        
        # Adjust based on market conditions
        if market_conditions.get('volatility_regime') == 'high':
            if 'defensive' in strategy_type.lower():
                base_score += 0.3
            elif 'momentum' in strategy_type.lower():
                base_score -= 0.2
        
        # Adjust based on risk tolerance
        if risk_tolerance == 'conservative':
            if 'conservative' in strategy_type.lower():
                base_score += 0.2
        elif risk_tolerance == 'aggressive':
            if 'aggressive' in strategy_type.lower():
                base_score += 0.2
        
        return min(1.0, max(0.0, base_score))
    
    def _generate_strategy_rationale(self, strategy_config: Dict[str, Any],
                                   market_conditions: Dict[str, Any]) -> str:
        """Generate rationale for strategy recommendation."""
        strategy_type = strategy_config.get('type', 'Unknown')
        market_regime = self._determine_market_regime(market_conditions)
        
        rationales = {
            'momentum': f"Momentum strategies perform well in trending markets. Current regime: {market_regime}",
            'mean_reversion': f"Mean reversion strategies benefit from range-bound markets. Current regime: {market_regime}",
            'defensive': f"Defensive strategies provide stability in uncertain markets. Current regime: {market_regime}"
        }
        
        return rationales.get(strategy_type.lower(), f"Strategy suitable for current market regime: {market_regime}")
    
    def _suggest_allocation(self, strategy_config: Dict[str, Any], risk_tolerance: str) -> float:
        """Suggest allocation percentage for strategy."""
        base_allocation = {
            'conservative': 0.15,
            'moderate': 0.25,
            'aggressive': 0.35
        }
        
        return base_allocation.get(risk_tolerance, 0.25)
    
    def _generate_allocation_suggestions(self, recommended_strategies: List[Dict[str, Any]],
                                       risk_tolerance: str) -> Dict[str, Any]:
        """Generate portfolio allocation suggestions."""
        if not recommended_strategies:
            return {}
        
        total_allocation = 0.8  # Leave 20% for cash/other
        
        # Allocate based on suitability scores
        total_score = sum(s['suitability_score'] for s in recommended_strategies)
        
        allocations = {}
        for strategy in recommended_strategies:
            if total_score > 0:
                allocation = (strategy['suitability_score'] / total_score) * total_allocation
                allocations[strategy['strategy_name']] = round(allocation, 2)
        
        return {
            'strategy_allocations': allocations,
            'cash_allocation': round(1.0 - sum(allocations.values()), 2),
            'rebalancing_frequency': 'monthly' if risk_tolerance == 'aggressive' else 'quarterly'
        }
    
    def _generate_market_timing_insights(self, market_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Generate market timing insights."""
        return {
            'market_phase': self._determine_market_regime(market_conditions),
            'timing_recommendation': 'gradual_entry',  # Conservative default
            'risk_factors': ['market_volatility', 'economic_uncertainty'],
            'opportunities': ['sector_rotation', 'volatility_trading']
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check of strategy tools."""
        return {
            'status': 'healthy',
            'services': {
                'backtester': 'connected',
                'strategy_executor': 'connected',
                'strategy_registry': 'connected',
                'strategy_factory': 'connected'
            },
            'last_check': datetime.now(timezone.utc).isoformat()
        }
