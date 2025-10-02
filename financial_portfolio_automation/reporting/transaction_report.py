"""
Transaction Report Generator.

This module generates comprehensive transaction history reports including
execution analysis, commission tracking, and order fill quality metrics.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from ..models.core import Order, Position
from ..data.store import DataStore
from ..execution.trade_logger import TradeLogger


class TransactionType(Enum):
    """Transaction classification types."""
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    SPLIT = "split"
    TRANSFER = "transfer"


class ExecutionQuality(Enum):
    """Order execution quality ratings."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class TransactionSummary:
    """Summary statistics for transactions."""
    total_transactions: int
    total_volume: Decimal
    total_commissions: Decimal
    buy_transactions: int
    sell_transactions: int
    average_trade_size: Decimal
    largest_trade: Decimal
    smallest_trade: Decimal


@dataclass
class ExecutionAnalysis:
    """Order execution quality analysis."""
    order_id: str
    symbol: str
    execution_quality: ExecutionQuality
    price_improvement: Decimal
    market_impact: Decimal
    fill_rate: Decimal
    time_to_fill_seconds: Optional[int]
    slippage: Decimal


@dataclass
class CommissionAnalysis:
    """Commission and fee analysis."""
    total_commissions: Decimal
    commission_per_share: Decimal
    commission_percentage: Decimal
    sec_fees: Decimal
    other_fees: Decimal
    total_fees: Decimal


class TransactionReport:
    """
    Transaction history report generator.
    
    Generates comprehensive transaction reports with execution analysis,
    commission tracking, and performance attribution.
    """
    
    def __init__(
        self,
        data_store: DataStore,
        trade_logger: TradeLogger
    ):
        """
        Initialize transaction report generator.
        
        Args:
            data_store: Data storage interface
            trade_logger: Trade logging system
        """
        self.data_store = data_store
        self.trade_logger = trade_logger
        self.logger = logging.getLogger(__name__)
    
    def generate_data(
        self,
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None,
        include_details: bool = True
    ) -> Dict[str, Any]:
        """
        Generate transaction report data.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            symbols: Optional symbol filter
            include_details: Whether to include detailed analysis
            
        Returns:
            Dictionary containing all transaction report data
        """
        self.logger.info(
            f"Generating transaction report data: {start_date} to {end_date}"
        )
        
        # Get all transactions for the period
        transactions = self._get_transactions(start_date, end_date, symbols)
        
        if not transactions:
            return self._empty_report(start_date, end_date, symbols)
        
        # Generate summary statistics
        summary = self._calculate_transaction_summary(transactions)
        
        # Prepare transaction details
        transaction_details = self._prepare_transaction_details(transactions)
        
        # Generate execution analysis if requested
        execution_analysis = []
        commission_analysis = None
        
        if include_details:
            execution_analysis = self._analyze_execution_quality(transactions)
            commission_analysis = self._analyze_commissions(transactions)
        
        # Generate performance attribution
        performance_attribution = self._calculate_performance_attribution(
            transactions
        )
        
        # Generate trading patterns analysis
        trading_patterns = self._analyze_trading_patterns(transactions)
        
        return {
            'report_metadata': {
                'generated_at': datetime.now(),
                'start_date': start_date,
                'end_date': end_date,
                'symbols_filter': symbols,
                'include_details': include_details
            },
            'transaction_summary': summary,
            'transaction_details': transaction_details,
            'execution_analysis': execution_analysis,
            'commission_analysis': commission_analysis,
            'performance_attribution': performance_attribution,
            'trading_patterns': trading_patterns
        }
    
    def _get_transactions(
        self,
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None
    ) -> List[Order]:
        """Get all transactions for the specified period."""
        orders = self.data_store.get_orders(
            start_date=start_date,
            end_date=end_date,
            status='FILLED'
        )
        
        if symbols:
            orders = [o for o in orders if o.symbol in symbols]
        
        return sorted(orders, key=lambda o: o.filled_at or o.created_at)
    
    def _calculate_transaction_summary(
        self, 
        transactions: List[Order]
    ) -> TransactionSummary:
        """Calculate summary statistics for transactions."""
        if not transactions:
            return TransactionSummary(
                total_transactions=0,
                total_volume=Decimal('0'),
                total_commissions=Decimal('0'),
                buy_transactions=0,
                sell_transactions=0,
                average_trade_size=Decimal('0'),
                largest_trade=Decimal('0'),
                smallest_trade=Decimal('0')
            )
        
        total_volume = sum(
            t.filled_quantity * t.average_fill_price 
            for t in transactions
        )
        
        total_commissions = sum(
            getattr(t, 'commission', Decimal('0')) 
            for t in transactions
        )
        
        buy_transactions = len([t for t in transactions if t.side == 'BUY'])
        sell_transactions = len([t for t in transactions if t.side == 'SELL'])
        
        trade_sizes = [
            t.filled_quantity * t.average_fill_price 
            for t in transactions
        ]
        
        return TransactionSummary(
            total_transactions=len(transactions),
            total_volume=total_volume,
            total_commissions=total_commissions,
            buy_transactions=buy_transactions,
            sell_transactions=sell_transactions,
            average_trade_size=total_volume / len(transactions),
            largest_trade=max(trade_sizes),
            smallest_trade=min(trade_sizes)
        )
    
    def _prepare_transaction_details(
        self, 
        transactions: List[Order]
    ) -> List[Dict[str, Any]]:
        """Prepare detailed transaction list."""
        details = []
        
        for transaction in transactions:
            details.append({
                'order_id': transaction.order_id,
                'symbol': transaction.symbol,
                'side': transaction.side,
                'quantity': float(transaction.filled_quantity),
                'price': float(transaction.average_fill_price),
                'value': float(transaction.filled_quantity * transaction.average_fill_price),
                'order_type': transaction.order_type,
                'time_in_force': getattr(transaction, 'time_in_force', 'DAY'),
                'created_at': (transaction.created_at).isoformat(),
                'filled_at': (transaction.filled_at or transaction.created_at).isoformat(),
                'commission': float(getattr(transaction, 'commission', Decimal('0'))),
                'fees': float(getattr(transaction, 'fees', Decimal('0'))),
                'status': transaction.status
            })
        
        return details
    
    def _analyze_execution_quality(
        self, 
        transactions: List[Order]
    ) -> List[ExecutionAnalysis]:
        """Analyze order execution quality."""
        analysis = []
        
        for transaction in transactions:
            # Calculate execution metrics (simplified)
            execution_quality = self._assess_execution_quality(transaction)
            price_improvement = self._calculate_price_improvement(transaction)
            market_impact = self._calculate_market_impact(transaction)
            fill_rate = self._calculate_fill_rate(transaction)
            time_to_fill = self._calculate_time_to_fill(transaction)
            slippage = self._calculate_slippage(transaction)
            
            analysis.append(ExecutionAnalysis(
                order_id=transaction.order_id,
                symbol=transaction.symbol,
                execution_quality=execution_quality,
                price_improvement=price_improvement,
                market_impact=market_impact,
                fill_rate=fill_rate,
                time_to_fill_seconds=time_to_fill,
                slippage=slippage
            ))
        
        return analysis
    
    def _analyze_commissions(
        self, 
        transactions: List[Order]
    ) -> CommissionAnalysis:
        """Analyze commission and fee structure."""
        total_commissions = sum(
            getattr(t, 'commission', Decimal('0')) 
            for t in transactions
        )
        
        total_shares = sum(t.filled_quantity for t in transactions)
        total_value = sum(
            t.filled_quantity * t.average_fill_price 
            for t in transactions
        )
        
        commission_per_share = (
            total_commissions / total_shares if total_shares > 0 
            else Decimal('0')
        )
        
        commission_percentage = (
            total_commissions / total_value * 100 if total_value > 0 
            else Decimal('0')
        )
        
        # Estimate fees (simplified)
        sec_fees = total_value * Decimal('0.0000051')  # SEC fee rate
        other_fees = sum(
            getattr(t, 'fees', Decimal('0')) 
            for t in transactions
        )
        
        total_fees = total_commissions + sec_fees + other_fees
        
        return CommissionAnalysis(
            total_commissions=total_commissions,
            commission_per_share=commission_per_share,
            commission_percentage=commission_percentage,
            sec_fees=sec_fees,
            other_fees=other_fees,
            total_fees=total_fees
        )
    
    def _calculate_performance_attribution(
        self, 
        transactions: List[Order]
    ) -> Dict[str, Any]:
        """Calculate performance attribution by symbol and strategy."""
        attribution = {}
        
        # Group transactions by symbol
        by_symbol = {}
        for transaction in transactions:
            if transaction.symbol not in by_symbol:
                by_symbol[transaction.symbol] = []
            by_symbol[transaction.symbol].append(transaction)
        
        # Calculate attribution for each symbol
        for symbol, symbol_transactions in by_symbol.items():
            buys = [t for t in symbol_transactions if t.side == 'BUY']
            sells = [t for t in symbol_transactions if t.side == 'SELL']
            
            total_bought = sum(t.filled_quantity for t in buys)
            total_sold = sum(t.filled_quantity for t in sells)
            
            buy_value = sum(
                t.filled_quantity * t.average_fill_price 
                for t in buys
            )
            sell_value = sum(
                t.filled_quantity * t.average_fill_price 
                for t in sells
            )
            
            # Calculate realized P&L (simplified)
            if total_sold > 0 and total_bought > 0:
                avg_buy_price = buy_value / total_bought
                avg_sell_price = sell_value / total_sold
                realized_pnl = min(total_sold, total_bought) * (avg_sell_price - avg_buy_price)
            else:
                realized_pnl = Decimal('0')
            
            attribution[symbol] = {
                'transactions': len(symbol_transactions),
                'total_bought': float(total_bought),
                'total_sold': float(total_sold),
                'buy_value': float(buy_value),
                'sell_value': float(sell_value),
                'realized_pnl': float(realized_pnl),
                'net_position': float(total_bought - total_sold)
            }
        
        return attribution
    
    def _analyze_trading_patterns(
        self, 
        transactions: List[Order]
    ) -> Dict[str, Any]:
        """Analyze trading patterns and behavior."""
        patterns = {}
        
        # Time-based analysis
        hourly_distribution = self._analyze_hourly_distribution(transactions)
        daily_distribution = self._analyze_daily_distribution(transactions)
        
        # Size analysis
        size_distribution = self._analyze_size_distribution(transactions)
        
        # Frequency analysis
        frequency_analysis = self._analyze_trading_frequency(transactions)
        
        patterns.update({
            'hourly_distribution': hourly_distribution,
            'daily_distribution': daily_distribution,
            'size_distribution': size_distribution,
            'frequency_analysis': frequency_analysis
        })
        
        return patterns
    
    def _assess_execution_quality(self, transaction: Order) -> ExecutionQuality:
        """Assess execution quality for a transaction."""
        # Simplified assessment based on order type and fill
        if transaction.order_type == 'MARKET':
            return ExecutionQuality.GOOD
        elif transaction.order_type == 'LIMIT':
            # Check if limit was improved upon
            return ExecutionQuality.EXCELLENT
        else:
            return ExecutionQuality.FAIR
    
    def _calculate_price_improvement(self, transaction: Order) -> Decimal:
        """Calculate price improvement for the transaction."""
        # Simplified calculation - would need market data at execution time
        return Decimal('0')
    
    def _calculate_market_impact(self, transaction: Order) -> Decimal:
        """Calculate market impact of the transaction."""
        # Simplified calculation based on trade size
        trade_value = transaction.filled_quantity * transaction.average_fill_price
        
        if trade_value > 100000:  # Large trade
            return Decimal('0.05')  # 5 bps
        elif trade_value > 10000:  # Medium trade
            return Decimal('0.02')  # 2 bps
        else:  # Small trade
            return Decimal('0.01')  # 1 bp
    
    def _calculate_fill_rate(self, transaction: Order) -> Decimal:
        """Calculate fill rate for the transaction."""
        if transaction.quantity > 0:
            return transaction.filled_quantity / transaction.quantity * 100
        return Decimal('100')
    
    def _calculate_time_to_fill(self, transaction: Order) -> Optional[int]:
        """Calculate time to fill in seconds."""
        if transaction.filled_at and transaction.created_at:
            return int((transaction.filled_at - transaction.created_at).total_seconds())
        return None
    
    def _calculate_slippage(self, transaction: Order) -> Decimal:
        """Calculate slippage for the transaction."""
        # Simplified calculation - would need market data at order time
        return Decimal('0')
    
    def _analyze_hourly_distribution(
        self, 
        transactions: List[Order]
    ) -> Dict[int, int]:
        """Analyze transaction distribution by hour of day."""
        hourly_counts = {hour: 0 for hour in range(24)}
        
        for transaction in transactions:
            hour = (transaction.filled_at or transaction.created_at).hour
            hourly_counts[hour] += 1
        
        return hourly_counts
    
    def _analyze_daily_distribution(
        self, 
        transactions: List[Order]
    ) -> Dict[str, int]:
        """Analyze transaction distribution by day of week."""
        daily_counts = {
            'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 
            'Thursday': 0, 'Friday': 0, 'Saturday': 0, 'Sunday': 0
        }
        
        day_names = list(daily_counts.keys())
        
        for transaction in transactions:
            day_of_week = (transaction.filled_at or transaction.created_at).weekday()
            daily_counts[day_names[day_of_week]] += 1
        
        return daily_counts
    
    def _analyze_size_distribution(
        self, 
        transactions: List[Order]
    ) -> Dict[str, int]:
        """Analyze transaction size distribution."""
        size_buckets = {
            'Small (<$1K)': 0,
            'Medium ($1K-$10K)': 0,
            'Large ($10K-$100K)': 0,
            'Very Large (>$100K)': 0
        }
        
        for transaction in transactions:
            value = float(transaction.filled_quantity * transaction.average_fill_price)
            
            if value < 1000:
                size_buckets['Small (<$1K)'] += 1
            elif value < 10000:
                size_buckets['Medium ($1K-$10K)'] += 1
            elif value < 100000:
                size_buckets['Large ($10K-$100K)'] += 1
            else:
                size_buckets['Very Large (>$100K)'] += 1
        
        return size_buckets
    
    def _analyze_trading_frequency(
        self, 
        transactions: List[Order]
    ) -> Dict[str, Any]:
        """Analyze trading frequency patterns."""
        if not transactions:
            return {}
        
        # Calculate date range
        start_date = min(
            (t.filled_at or t.created_at).date() 
            for t in transactions
        )
        end_date = max(
            (t.filled_at or t.created_at).date() 
            for t in transactions
        )
        
        total_days = (end_date - start_date).days + 1
        trading_days = len(set(
            (t.filled_at or t.created_at).date() 
            for t in transactions
        ))
        
        return {
            'total_transactions': len(transactions),
            'total_days': total_days,
            'trading_days': trading_days,
            'transactions_per_day': len(transactions) / total_days,
            'transactions_per_trading_day': len(transactions) / trading_days if trading_days > 0 else 0,
            'trading_day_percentage': trading_days / total_days * 100 if total_days > 0 else 0
        }
    
    def _empty_report(
        self, 
        start_date: date, 
        end_date: date, 
        symbols: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Return empty report structure when no transactions found."""
        return {
            'report_metadata': {
                'generated_at': datetime.now(),
                'start_date': start_date,
                'end_date': end_date,
                'symbols_filter': symbols,
                'include_details': True
            },
            'transaction_summary': TransactionSummary(
                total_transactions=0,
                total_volume=Decimal('0'),
                total_commissions=Decimal('0'),
                buy_transactions=0,
                sell_transactions=0,
                average_trade_size=Decimal('0'),
                largest_trade=Decimal('0'),
                smallest_trade=Decimal('0')
            ),
            'transaction_details': [],
            'execution_analysis': [],
            'commission_analysis': None,
            'performance_attribution': {},
            'trading_patterns': {}
        }