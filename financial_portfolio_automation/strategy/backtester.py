"""
Backtesting engine for strategy performance testing and validation.

This module provides comprehensive backtesting capabilities including historical simulation,
transaction cost modeling, slippage estimation, walk-forward analysis, and Monte Carlo simulation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy

from .base import Strategy, StrategySignal, SignalType
from ..models.core import Quote, Position, Order, PortfolioSnapshot, OrderSide, OrderType, OrderStatus
from ..models.config import StrategyConfig
from ..analysis.portfolio_analyzer import PortfolioAnalyzer
from ..analysis.technical_analysis import TechnicalAnalysis


logger = logging.getLogger(__name__)


@dataclass
class TransactionCosts:
    """Configuration for transaction costs and market impact."""
    
    commission_per_share: Decimal = Decimal('0.005')  # $0.005 per share
    commission_minimum: Decimal = Decimal('1.00')     # $1.00 minimum
    commission_maximum: Decimal = Decimal('5.00')     # $5.00 maximum
    spread_cost_factor: Decimal = Decimal('0.5')      # 50% of spread as cost
    market_impact_factor: Decimal = Decimal('0.001')  # 0.1% market impact
    slippage_factor: Decimal = Decimal('0.0005')      # 0.05% slippage


@dataclass
class BacktestTrade:
    """Represents a trade executed during backtesting."""
    
    timestamp: datetime
    symbol: str
    side: OrderSide
    quantity: int
    price: Decimal
    commission: Decimal
    slippage: Decimal
    market_impact: Decimal
    strategy_id: str
    signal_strength: float
    
    @property
    def total_cost(self) -> Decimal:
        """Calculate total transaction cost."""
        return self.commission + self.slippage + self.market_impact
    
    @property
    def net_amount(self) -> Decimal:
        """Calculate net amount (including costs)."""
        gross_amount = self.price * self.quantity
        if self.side == OrderSide.BUY:
            return gross_amount + self.total_cost
        else:
            return gross_amount - self.total_cost


@dataclass
class BacktestResults:
    """Results from a backtesting run."""
    
    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    final_value: Decimal
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_commission: Decimal
    total_slippage: Decimal
    trades: List[BacktestTrade] = field(default_factory=list)
    portfolio_history: List[PortfolioSnapshot] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


class Backtester:
    """
    Comprehensive backtesting engine for strategy validation and optimization.
    
    Provides historical simulation with realistic transaction costs, slippage modeling,
    walk-forward analysis, and Monte Carlo simulation capabilities.
    """
    
    def __init__(self, 
                 transaction_costs: Optional[TransactionCosts] = None,
                 initial_capital: Decimal = Decimal('100000')):
        """
        Initialize the backtester.
        
        Args:
            transaction_costs: Transaction cost configuration
            initial_capital: Initial capital for backtesting
        """
        self.transaction_costs = transaction_costs or TransactionCosts()
        self.initial_capital = initial_capital
        self.logger = logging.getLogger(__name__)
        self.portfolio_analyzer = PortfolioAnalyzer()
        self.technical_analyzer = TechnicalAnalysis()
        
        # Backtesting state
        self._current_portfolio: Optional[PortfolioSnapshot] = None
        self._current_positions: Dict[str, Position] = {}
        self._cash_balance: Decimal = initial_capital
        self._trades: List[BacktestTrade] = []
        self._portfolio_history: List[PortfolioSnapshot] = []
    
    def run_backtest(self,
                     strategy: Strategy,
                     historical_data: Dict[str, List[Quote]],
                     start_date: datetime,
                     end_date: datetime,
                     rebalance_frequency: str = 'daily') -> BacktestResults:
        """
        Run a comprehensive backtest for a strategy.
        
        Args:
            strategy: Strategy to backtest
            historical_data: Historical market data by symbol
            start_date: Backtest start date
            end_date: Backtest end date
            rebalance_frequency: How often to rebalance ('daily', 'weekly', 'monthly')
            
        Returns:
            BacktestResults containing performance metrics and trade history
        """
        try:
            self.logger.info(f"Starting backtest for strategy {strategy.strategy_id}")
            self.logger.info(f"Period: {start_date} to {end_date}")
            self.logger.info(f"Initial capital: ${self.initial_capital}")
            
            # Reset backtesting state
            self._reset_state()
            
            # Validate inputs
            self._validate_backtest_inputs(historical_data, start_date, end_date)
            
            # Get all trading dates
            trading_dates = self._get_trading_dates(historical_data, start_date, end_date)
            
            if not trading_dates:
                raise ValueError("No trading dates found in the specified period")
            
            # Run simulation
            for i, current_date in enumerate(trading_dates):
                # Get market data for current date
                market_data = self._get_market_data_for_date(historical_data, current_date)
                
                if not market_data:
                    continue
                
                # Get historical data up to current date for strategy analysis
                historical_subset = self._get_historical_subset(
                    historical_data, trading_dates[:i+1]
                )
                
                # Update portfolio with current market prices
                self._update_portfolio_values(market_data, current_date)
                
                # Generate signals
                signals = strategy.generate_signals(
                    market_data, self._current_portfolio, historical_subset
                )
                
                # Execute trades based on signals
                for signal in signals:
                    if strategy.validate_signal(signal):
                        self._execute_signal(signal, market_data[signal.symbol], current_date)
                
                # Update strategy state
                strategy.update_state(market_data, self._current_portfolio)
                
                # Record portfolio snapshot
                self._record_portfolio_snapshot(current_date)
            
            # Calculate final results
            results = self._calculate_backtest_results(
                strategy.strategy_id, start_date, end_date
            )
            
            self.logger.info(f"Backtest completed. Total return: {results.total_return:.2%}")
            self.logger.info(f"Sharpe ratio: {results.sharpe_ratio:.2f}")
            self.logger.info(f"Max drawdown: {results.max_drawdown:.2%}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            raise
    
    def run_walk_forward_analysis(self,
                                  strategy: Strategy,
                                  historical_data: Dict[str, List[Quote]],
                                  start_date: datetime,
                                  end_date: datetime,
                                  training_period_months: int = 12,
                                  testing_period_months: int = 3,
                                  step_months: int = 1) -> Dict[str, Any]:
        """
        Run walk-forward analysis to test strategy robustness.
        
        Args:
            strategy: Strategy to test
            historical_data: Historical market data
            start_date: Analysis start date
            end_date: Analysis end date
            training_period_months: Months of data for training
            testing_period_months: Months of data for testing
            step_months: Step size in months
            
        Returns:
            Dictionary containing walk-forward analysis results
        """
        try:
            self.logger.info("Starting walk-forward analysis")
            
            results = []
            current_start = start_date
            
            while current_start < end_date:
                # Define training period
                training_end = current_start + timedelta(days=training_period_months * 30)
                
                # Define testing period
                testing_start = training_end
                testing_end = testing_start + timedelta(days=testing_period_months * 30)
                
                if testing_end > end_date:
                    break
                
                self.logger.info(f"Walk-forward period: {testing_start} to {testing_end}")
                
                # Run backtest for this period
                period_result = self.run_backtest(
                    strategy, historical_data, testing_start, testing_end
                )
                
                results.append({
                    'period_start': testing_start,
                    'period_end': testing_end,
                    'total_return': period_result.total_return,
                    'sharpe_ratio': period_result.sharpe_ratio,
                    'max_drawdown': period_result.max_drawdown,
                    'win_rate': period_result.win_rate,
                    'total_trades': period_result.total_trades
                })
                
                # Move to next period
                current_start += timedelta(days=step_months * 30)
            
            # Calculate aggregate statistics
            if results:
                returns = [r['total_return'] for r in results]
                sharpe_ratios = [r['sharpe_ratio'] for r in results if r['sharpe_ratio'] is not None]
                drawdowns = [r['max_drawdown'] for r in results]
                
                aggregate_stats = {
                    'periods_tested': len(results),
                    'average_return': np.mean(returns),
                    'return_std': np.std(returns),
                    'average_sharpe': np.mean(sharpe_ratios) if sharpe_ratios else 0,
                    'average_drawdown': np.mean(drawdowns),
                    'worst_drawdown': max(drawdowns) if drawdowns else 0,
                    'positive_periods': sum(1 for r in returns if r > 0),
                    'consistency_ratio': sum(1 for r in returns if r > 0) / len(returns)
                }
            else:
                aggregate_stats = {}
            
            return {
                'period_results': results,
                'aggregate_statistics': aggregate_stats,
                'parameters': {
                    'training_period_months': training_period_months,
                    'testing_period_months': testing_period_months,
                    'step_months': step_months
                }
            }
            
        except Exception as e:
            self.logger.error(f"Walk-forward analysis failed: {e}")
            raise
    
    def run_monte_carlo_simulation(self,
                                   strategy: Strategy,
                                   historical_data: Dict[str, List[Quote]],
                                   start_date: datetime,
                                   end_date: datetime,
                                   num_simulations: int = 1000,
                                   confidence_levels: List[float] = [0.05, 0.95]) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation to assess strategy performance distribution.
        
        Args:
            strategy: Strategy to simulate
            historical_data: Historical market data
            start_date: Simulation start date
            end_date: Simulation end date
            num_simulations: Number of Monte Carlo runs
            confidence_levels: Confidence levels for VaR calculation
            
        Returns:
            Dictionary containing Monte Carlo simulation results
        """
        try:
            self.logger.info(f"Starting Monte Carlo simulation with {num_simulations} runs")
            
            # Prepare randomized data sets
            randomized_datasets = self._generate_randomized_datasets(
                historical_data, num_simulations
            )
            
            # Run simulations in parallel
            simulation_results = []
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                
                for i, dataset in enumerate(randomized_datasets):
                    future = executor.submit(
                        self._run_single_simulation,
                        copy.deepcopy(strategy),
                        dataset,
                        start_date,
                        end_date,
                        i
                    )
                    futures.append(future)
                
                # Collect results
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        simulation_results.append(result)
                    except Exception as e:
                        self.logger.warning(f"Simulation failed: {e}")
            
            if not simulation_results:
                raise ValueError("All Monte Carlo simulations failed")
            
            # Analyze results
            returns = [r.total_return for r in simulation_results]
            sharpe_ratios = [r.sharpe_ratio for r in simulation_results if r.sharpe_ratio is not None]
            drawdowns = [r.max_drawdown for r in simulation_results]
            
            # Calculate statistics
            statistics = {
                'simulations_completed': len(simulation_results),
                'mean_return': np.mean(returns),
                'median_return': np.median(returns),
                'std_return': np.std(returns),
                'min_return': np.min(returns),
                'max_return': np.max(returns),
                'mean_sharpe': np.mean(sharpe_ratios) if sharpe_ratios else 0,
                'mean_drawdown': np.mean(drawdowns),
                'worst_drawdown': np.max(drawdowns) if drawdowns else 0,
                'positive_returns_pct': sum(1 for r in returns if r > 0) / len(returns) * 100
            }
            
            # Calculate Value at Risk (VaR) and Conditional VaR
            var_results = {}
            for confidence_level in confidence_levels:
                percentile = confidence_level * 100
                var_value = np.percentile(returns, percentile)
                
                # Conditional VaR (Expected Shortfall)
                if confidence_level < 0.5:
                    cvar_returns = [r for r in returns if r <= var_value]
                else:
                    cvar_returns = [r for r in returns if r >= var_value]
                
                cvar_value = np.mean(cvar_returns) if cvar_returns else var_value
                
                var_results[f'var_{int(percentile)}'] = var_value
                var_results[f'cvar_{int(percentile)}'] = cvar_value
            
            return {
                'statistics': statistics,
                'var_analysis': var_results,
                'simulation_results': simulation_results,
                'parameters': {
                    'num_simulations': num_simulations,
                    'confidence_levels': confidence_levels
                }
            }
            
        except Exception as e:
            self.logger.error(f"Monte Carlo simulation failed: {e}")
            raise
    
    def _reset_state(self) -> None:
        """Reset backtesting state for a new run."""
        self._current_positions = {}
        self._cash_balance = self.initial_capital
        self._trades = []
        self._portfolio_history = []
        self._current_portfolio = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=self.initial_capital,
            buying_power=self.initial_capital,
            day_pnl=Decimal('0'),
            total_pnl=Decimal('0'),
            positions=[]
        )
    
    def _validate_backtest_inputs(self,
                                  historical_data: Dict[str, List[Quote]],
                                  start_date: datetime,
                                  end_date: datetime) -> None:
        """Validate backtest inputs."""
        if not historical_data:
            raise ValueError("Historical data cannot be empty")
        
        if start_date >= end_date:
            raise ValueError("Start date must be before end date")
        
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        
        # Check data availability
        for symbol, quotes in historical_data.items():
            if not quotes:
                raise ValueError(f"No quotes available for symbol {symbol}")
            
            # Check date range coverage
            quote_dates = [q.timestamp.date() for q in quotes]
            min_date = min(quote_dates)
            max_date = max(quote_dates)
            
            if start_date.date() < min_date or end_date.date() > max_date:
                self.logger.warning(
                    f"Symbol {symbol} data range ({min_date} to {max_date}) "
                    f"doesn't fully cover backtest period ({start_date.date()} to {end_date.date()})"
                )
    
    def _get_trading_dates(self,
                           historical_data: Dict[str, List[Quote]],
                           start_date: datetime,
                           end_date: datetime) -> List[datetime]:
        """Get sorted list of trading dates from historical data."""
        all_dates = set()
        
        for quotes in historical_data.values():
            for quote in quotes:
                quote_date = quote.timestamp.date()
                if start_date.date() <= quote_date <= end_date.date():
                    all_dates.add(quote.timestamp.replace(hour=16, minute=0, second=0, microsecond=0))
        
        return sorted(list(all_dates))
    
    def _get_market_data_for_date(self,
                                  historical_data: Dict[str, List[Quote]],
                                  target_date: datetime) -> Dict[str, Quote]:
        """Get market data for a specific date."""
        market_data = {}
        target_date_only = target_date.date()
        
        for symbol, quotes in historical_data.items():
            # Find quote for the target date
            for quote in quotes:
                if quote.timestamp.date() == target_date_only:
                    market_data[symbol] = quote
                    break
        
        return market_data
    
    def _get_historical_subset(self,
                               historical_data: Dict[str, List[Quote]],
                               dates_up_to: List[datetime]) -> Dict[str, List[Quote]]:
        """Get historical data subset up to specified dates."""
        subset = {}
        max_date = max(dates_up_to).date() if dates_up_to else None
        
        if max_date is None:
            return subset
        
        for symbol, quotes in historical_data.items():
            subset[symbol] = [
                quote for quote in quotes
                if quote.timestamp.date() <= max_date
            ]
        
        return subset
    
    def _update_portfolio_values(self,
                                 market_data: Dict[str, Quote],
                                 current_date: datetime) -> None:
        """Update portfolio values based on current market prices."""
        total_value = self._cash_balance
        day_pnl = Decimal('0')
        
        updated_positions = []
        
        for symbol, position in self._current_positions.items():
            if symbol in market_data:
                quote = market_data[symbol]
                current_price = quote.mid_price
                
                # Calculate new market value
                new_market_value = abs(position.quantity) * current_price
                if position.quantity < 0:  # Short position
                    new_market_value = -new_market_value
                
                # Calculate PnL
                pnl_change = new_market_value - position.market_value
                
                # Update position
                updated_position = Position(
                    symbol=symbol,
                    quantity=position.quantity,
                    market_value=new_market_value,
                    cost_basis=position.cost_basis,
                    unrealized_pnl=new_market_value - position.cost_basis,
                    day_pnl=pnl_change
                )
                
                updated_positions.append(updated_position)
                total_value += new_market_value
                day_pnl += pnl_change
            else:
                # Keep existing position if no market data
                updated_positions.append(position)
                total_value += position.market_value
        
        # Update current portfolio
        self._current_portfolio = PortfolioSnapshot(
            timestamp=current_date,
            total_value=total_value,
            buying_power=self._cash_balance,
            day_pnl=day_pnl,
            total_pnl=total_value - self.initial_capital,
            positions=updated_positions
        )
        
        # Update positions dictionary
        self._current_positions = {pos.symbol: pos for pos in updated_positions}
    
    def _execute_signal(self,
                        signal: StrategySignal,
                        quote: Quote,
                        timestamp: datetime) -> None:
        """Execute a trading signal with realistic costs and slippage."""
        try:
            # Determine order details
            if signal.signal_type in [SignalType.BUY, SignalType.SELL]:
                side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL
                
                # Calculate position size if not specified
                if signal.quantity is None:
                    # Use a simple position sizing based on signal strength and available capital
                    max_position_value = self._cash_balance * Decimal('0.1')  # Max 10% per position
                    signal_factor = Decimal(str(signal.strength))
                    position_value = max_position_value * signal_factor
                    quantity = int(position_value / quote.mid_price)
                else:
                    quantity = signal.quantity
                
                if quantity <= 0:
                    return
                
                # Calculate execution price with slippage
                execution_price = self._calculate_execution_price(quote, side, quantity)
                
                # Calculate transaction costs
                commission = self._calculate_commission(quantity, execution_price)
                slippage_cost = self._calculate_slippage_cost(quote, side, quantity)
                market_impact = self._calculate_market_impact(quantity, execution_price)
                
                # Check if we have sufficient capital
                total_cost = quantity * execution_price + commission + slippage_cost + market_impact
                if side == OrderSide.BUY and total_cost > self._cash_balance:
                    # Reduce quantity to fit available capital
                    available_for_shares = self._cash_balance - commission - slippage_cost - market_impact
                    quantity = max(1, int(available_for_shares / execution_price))
                    total_cost = quantity * execution_price + commission + slippage_cost + market_impact
                    
                    if total_cost > self._cash_balance:
                        self.logger.debug(f"Insufficient capital for {signal.symbol} trade")
                        return
                
                # Execute the trade
                self._execute_trade(
                    symbol=signal.symbol,
                    side=side,
                    quantity=quantity,
                    price=execution_price,
                    commission=commission,
                    slippage=slippage_cost,
                    market_impact=market_impact,
                    timestamp=timestamp,
                    strategy_id=signal.metadata.get('strategy_id', 'unknown'),
                    signal_strength=signal.strength
                )
                
        except Exception as e:
            self.logger.error(f"Failed to execute signal for {signal.symbol}: {e}")
    
    def _calculate_execution_price(self, quote: Quote, side: OrderSide, quantity: int) -> Decimal:
        """Calculate realistic execution price including slippage."""
        base_price = quote.ask if side == OrderSide.BUY else quote.bid
        
        # Add slippage based on quantity and spread
        spread = quote.spread
        slippage_factor = min(Decimal('0.01'), self.transaction_costs.slippage_factor * Decimal(str(quantity / 1000)))
        slippage = spread * slippage_factor
        
        if side == OrderSide.BUY:
            return base_price + slippage
        else:
            return base_price - slippage
    
    def _calculate_commission(self, quantity: int, price: Decimal) -> Decimal:
        """Calculate commission costs."""
        commission = Decimal(str(quantity)) * self.transaction_costs.commission_per_share
        commission = max(commission, self.transaction_costs.commission_minimum)
        commission = min(commission, self.transaction_costs.commission_maximum)
        return commission
    
    def _calculate_slippage_cost(self, quote: Quote, side: OrderSide, quantity: int) -> Decimal:
        """Calculate slippage costs."""
        spread = quote.spread
        slippage_cost = spread * self.transaction_costs.spread_cost_factor
        return slippage_cost * Decimal(str(quantity))
    
    def _calculate_market_impact(self, quantity: int, price: Decimal) -> Decimal:
        """Calculate market impact costs."""
        trade_value = Decimal(str(quantity)) * price
        return trade_value * self.transaction_costs.market_impact_factor
    
    def _execute_trade(self,
                       symbol: str,
                       side: OrderSide,
                       quantity: int,
                       price: Decimal,
                       commission: Decimal,
                       slippage: Decimal,
                       market_impact: Decimal,
                       timestamp: datetime,
                       strategy_id: str,
                       signal_strength: float) -> None:
        """Execute a trade and update portfolio state."""
        # Create trade record
        trade = BacktestTrade(
            timestamp=timestamp,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            commission=commission,
            slippage=slippage,
            market_impact=market_impact,
            strategy_id=strategy_id,
            signal_strength=signal_strength
        )
        
        self._trades.append(trade)
        
        # Update cash balance
        if side == OrderSide.BUY:
            self._cash_balance -= trade.net_amount
        else:
            self._cash_balance += trade.net_amount
        
        # Update positions
        if symbol in self._current_positions:
            existing_position = self._current_positions[symbol]
            
            if side == OrderSide.BUY:
                new_quantity = existing_position.quantity + quantity
                new_cost_basis = existing_position.cost_basis + (price * quantity)
            else:
                new_quantity = existing_position.quantity - quantity
                # For sells, we don't change cost basis of remaining shares
                new_cost_basis = existing_position.cost_basis
                if new_quantity == 0:
                    new_cost_basis = Decimal('0')
            
            if new_quantity == 0:
                # Position closed
                del self._current_positions[symbol]
            else:
                # Update existing position
                new_market_value = abs(new_quantity) * price
                if new_quantity < 0:
                    new_market_value = -new_market_value
                
                self._current_positions[symbol] = Position(
                    symbol=symbol,
                    quantity=new_quantity,
                    market_value=new_market_value,
                    cost_basis=new_cost_basis,
                    unrealized_pnl=new_market_value - new_cost_basis,
                    day_pnl=Decimal('0')
                )
        else:
            # New position
            if side == OrderSide.BUY:
                new_quantity = quantity
                new_cost_basis = price * quantity
            else:
                new_quantity = -quantity
                new_cost_basis = -(price * quantity)
            
            new_market_value = abs(new_quantity) * price
            if new_quantity < 0:
                new_market_value = -new_market_value
            
            self._current_positions[symbol] = Position(
                symbol=symbol,
                quantity=new_quantity,
                market_value=new_market_value,
                cost_basis=new_cost_basis,
                unrealized_pnl=new_market_value - new_cost_basis,
                day_pnl=Decimal('0')
            )
    
    def _record_portfolio_snapshot(self, timestamp: datetime) -> None:
        """Record current portfolio state."""
        if self._current_portfolio:
            snapshot = PortfolioSnapshot(
                timestamp=timestamp,
                total_value=self._current_portfolio.total_value,
                buying_power=self._cash_balance,
                day_pnl=self._current_portfolio.day_pnl,
                total_pnl=self._current_portfolio.total_pnl,
                positions=list(self._current_positions.values())
            )
            self._portfolio_history.append(snapshot)
    
    def _calculate_backtest_results(self,
                                    strategy_id: str,
                                    start_date: datetime,
                                    end_date: datetime) -> BacktestResults:
        """Calculate comprehensive backtest results."""
        if not self._portfolio_history:
            raise ValueError("No portfolio history available for results calculation")
        
        final_value = self._portfolio_history[-1].total_value
        total_return = float((final_value - self.initial_capital) / self.initial_capital)
        
        # Calculate time-based metrics
        days = (end_date - start_date).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else total_return
        
        # Calculate risk metrics using portfolio analyzer
        risk_metrics = {}
        if len(self._portfolio_history) > 1:
            try:
                risk_metrics = self.portfolio_analyzer.calculate_risk_metrics(self._portfolio_history)
            except Exception as e:
                self.logger.warning(f"Failed to calculate risk metrics: {e}")
        
        # Calculate trade statistics
        winning_trades = [t for t in self._trades if self._is_winning_trade(t)]
        losing_trades = [t for t in self._trades if not self._is_winning_trade(t)]
        
        win_rate = len(winning_trades) / len(self._trades) if self._trades else 0
        
        # Calculate profit factor
        gross_profit = sum(self._calculate_trade_pnl(t) for t in winning_trades)
        gross_loss = abs(sum(self._calculate_trade_pnl(t) for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calculate total costs
        total_commission = sum(t.commission for t in self._trades)
        total_slippage = sum(t.slippage for t in self._trades)
        
        return BacktestResults(
            strategy_id=strategy_id,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_value=final_value,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=risk_metrics.get('max_drawdown', 0),
            sharpe_ratio=risk_metrics.get('sharpe_ratio', 0),
            sortino_ratio=risk_metrics.get('sortino_ratio', 0),
            calmar_ratio=risk_metrics.get('calmar_ratio', 0),
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(self._trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            total_commission=total_commission,
            total_slippage=total_slippage,
            trades=self._trades.copy(),
            portfolio_history=self._portfolio_history.copy(),
            performance_metrics=risk_metrics
        )
    
    def _is_winning_trade(self, trade: BacktestTrade) -> bool:
        """Determine if a trade was profitable (simplified)."""
        # This is a simplified approach - in reality, you'd need to track
        # the complete round-trip trade to determine profitability
        return trade.side == OrderSide.SELL  # Assume sells are profit-taking
    
    def _calculate_trade_pnl(self, trade: BacktestTrade) -> Decimal:
        """Calculate P&L for a trade (simplified)."""
        # Simplified calculation - in reality, you'd need complete trade pairs
        if trade.side == OrderSide.SELL:
            return trade.price * trade.quantity - trade.total_cost
        else:
            return -(trade.price * trade.quantity + trade.total_cost)
    
    def _generate_randomized_datasets(self,
                                      historical_data: Dict[str, List[Quote]],
                                      num_datasets: int) -> List[Dict[str, List[Quote]]]:
        """Generate randomized datasets for Monte Carlo simulation."""
        datasets = []
        
        for _ in range(num_datasets):
            randomized_data = {}
            
            for symbol, quotes in historical_data.items():
                if len(quotes) < 2:
                    randomized_data[symbol] = quotes.copy()
                    continue
                
                # Bootstrap sampling with replacement
                randomized_quotes = random.choices(quotes, k=len(quotes))
                
                # Sort by timestamp to maintain chronological order
                randomized_quotes.sort(key=lambda q: q.timestamp)
                
                randomized_data[symbol] = randomized_quotes
            
            datasets.append(randomized_data)
        
        return datasets
    
    def _run_single_simulation(self,
                               strategy: Strategy,
                               historical_data: Dict[str, List[Quote]],
                               start_date: datetime,
                               end_date: datetime,
                               simulation_id: int) -> BacktestResults:
        """Run a single Monte Carlo simulation."""
        try:
            # Create a fresh backtester instance for this simulation
            sim_backtester = Backtester(self.transaction_costs, self.initial_capital)
            
            # Run backtest
            result = sim_backtester.run_backtest(
                strategy, historical_data, start_date, end_date
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Simulation {simulation_id} failed: {e}")
            raise