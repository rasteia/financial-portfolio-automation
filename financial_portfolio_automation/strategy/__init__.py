"""
Strategy engine package for the financial portfolio automation system.

This package contains the strategy framework, concrete strategy implementations,
and backtesting capabilities.
"""

from .base import Strategy, StrategySignal, SignalType, StrategyState
from .registry import StrategyRegistry, get_global_registry, register_strategy_class, create_strategy
from .executor import StrategyExecutor
from .momentum import MomentumStrategy
from .mean_reversion import MeanReversionStrategy
from .factory import (
    StrategyFactory, 
    get_global_factory, 
    create_momentum_strategy, 
    create_mean_reversion_strategy
)
from .backtester import Backtester, BacktestResults, BacktestTrade, TransactionCosts

__all__ = [
    'Strategy',
    'StrategySignal', 
    'SignalType',
    'StrategyState',
    'StrategyRegistry',
    'get_global_registry',
    'register_strategy_class',
    'create_strategy',
    'StrategyExecutor',
    'MomentumStrategy',
    'MeanReversionStrategy',
    'StrategyFactory',
    'get_global_factory',
    'create_momentum_strategy',
    'create_mean_reversion_strategy',
    'Backtester',
    'BacktestResults',
    'BacktestTrade',
    'TransactionCosts'
]