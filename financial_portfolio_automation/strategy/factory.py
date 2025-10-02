"""
Strategy factory for creating and registering trading strategies.

This module provides a factory pattern for creating strategy instances
and automatically registers all available strategy types.
"""

from typing import Dict, Type, List
import logging

from .base import Strategy
from .momentum import MomentumStrategy
from .mean_reversion import MeanReversionStrategy
from .registry import get_global_registry, StrategyRegistry
from ..models.config import StrategyConfig, StrategyType


logger = logging.getLogger(__name__)


class StrategyFactory:
    """
    Factory for creating and managing trading strategies.
    
    This class provides a centralized way to create strategy instances
    and manages the registration of strategy types.
    """
    
    def __init__(self, registry: StrategyRegistry = None):
        """
        Initialize strategy factory.
        
        Args:
            registry: Strategy registry to use (uses global if None)
        """
        self.registry = registry or get_global_registry()
        self._strategy_classes: Dict[StrategyType, Type[Strategy]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Register built-in strategies
        self._register_builtin_strategies()
    
    def _register_builtin_strategies(self) -> None:
        """Register all built-in strategy types."""
        builtin_strategies = {
            StrategyType.MOMENTUM: MomentumStrategy,
            StrategyType.MEAN_REVERSION: MeanReversionStrategy,
        }
        
        for strategy_type, strategy_class in builtin_strategies.items():
            try:
                self.registry.register_strategy_class(strategy_type, strategy_class)
                self._strategy_classes[strategy_type] = strategy_class
                self.logger.info(f"Registered built-in strategy: {strategy_type}")
            except Exception as e:
                self.logger.error(f"Failed to register strategy {strategy_type}: {e}")
    
    def create_strategy(self, config: StrategyConfig) -> Strategy:
        """
        Create a strategy instance from configuration.
        
        Args:
            config: Strategy configuration
            
        Returns:
            Strategy instance
            
        Raises:
            ValueError: If strategy type is not supported
        """
        try:
            return self.registry.create_strategy(config)
        except Exception as e:
            self.logger.error(f"Failed to create strategy {config.strategy_id}: {e}")
            raise
    
    def create_momentum_strategy(
        self,
        strategy_id: str,
        symbols: List[str],
        parameters: Dict = None,
        **kwargs
    ) -> MomentumStrategy:
        """
        Create a momentum strategy with default parameters.
        
        Args:
            strategy_id: Unique strategy identifier
            symbols: List of symbols to trade
            parameters: Strategy-specific parameters
            **kwargs: Additional configuration options
            
        Returns:
            Configured momentum strategy
        """
        default_params = {
            'lookback_period': 20,
            'momentum_threshold': 0.02,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_signal_threshold': 0.0,
            'price_change_threshold': 0.02,
            'volume_threshold': 1.5,
            'min_momentum_strength': 0.6
        }
        
        if parameters:
            default_params.update(parameters)
        
        config = StrategyConfig(
            strategy_id=strategy_id,
            strategy_type=StrategyType.MOMENTUM,
            name=f"Momentum Strategy {strategy_id}",
            description="Momentum-based trading strategy that follows price trends",
            symbols=symbols,
            parameters=default_params,
            **kwargs
        )
        
        return self.create_strategy(config)
    
    def create_mean_reversion_strategy(
        self,
        strategy_id: str,
        symbols: List[str],
        parameters: Dict = None,
        **kwargs
    ) -> MeanReversionStrategy:
        """
        Create a mean reversion strategy with default parameters.
        
        Args:
            strategy_id: Unique strategy identifier
            symbols: List of symbols to trade
            parameters: Strategy-specific parameters
            **kwargs: Additional configuration options
            
        Returns:
            Configured mean reversion strategy
        """
        default_params = {
            'lookback_period': 20,
            'deviation_threshold': 2.0,
            'std_dev_threshold': 2.0,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'bollinger_period': 20,
            'bollinger_std': 2.0,
            'mean_reversion_threshold': 0.05,
            'volume_confirmation': True,
            'trend_filter': True,
            'min_reversion_strength': 0.5
        }
        
        if parameters:
            default_params.update(parameters)
        
        config = StrategyConfig(
            strategy_id=strategy_id,
            strategy_type=StrategyType.MEAN_REVERSION,
            name=f"Mean Reversion Strategy {strategy_id}",
            description="Mean reversion strategy that identifies overbought/oversold conditions",
            symbols=symbols,
            parameters=default_params,
            **kwargs
        )
        
        return self.create_strategy(config)
    
    def get_available_strategy_types(self) -> List[StrategyType]:
        """
        Get list of available strategy types.
        
        Returns:
            List of available strategy types
        """
        return self.registry.list_registered_types()
    
    def get_strategy_class(self, strategy_type: StrategyType) -> Type[Strategy]:
        """
        Get strategy class for a given type.
        
        Args:
            strategy_type: Strategy type
            
        Returns:
            Strategy class
            
        Raises:
            ValueError: If strategy type is not registered
        """
        strategy_class = self.registry.get_strategy_class(strategy_type)
        if not strategy_class:
            available_types = self.get_available_strategy_types()
            raise ValueError(
                f"Strategy type {strategy_type} not available. "
                f"Available types: {available_types}"
            )
        return strategy_class
    
    def create_strategy_from_template(
        self,
        template_name: str,
        strategy_id: str,
        symbols: List[str],
        **kwargs
    ) -> Strategy:
        """
        Create a strategy from a predefined template.
        
        Args:
            template_name: Name of the template
            strategy_id: Unique strategy identifier
            symbols: List of symbols to trade
            **kwargs: Additional configuration options
            
        Returns:
            Strategy instance
            
        Raises:
            ValueError: If template is not found
        """
        templates = {
            'aggressive_momentum': {
                'strategy_type': StrategyType.MOMENTUM,
                'parameters': {
                    'lookback_period': 15,
                    'momentum_threshold': 0.03,
                    'min_momentum_strength': 0.7,
                    'price_change_threshold': 0.03,
                    'volume_threshold': 2.0
                }
            },
            'conservative_momentum': {
                'strategy_type': StrategyType.MOMENTUM,
                'parameters': {
                    'lookback_period': 30,
                    'momentum_threshold': 0.015,
                    'min_momentum_strength': 0.5,
                    'price_change_threshold': 0.015,
                    'volume_threshold': 1.2
                }
            },
            'aggressive_mean_reversion': {
                'strategy_type': StrategyType.MEAN_REVERSION,
                'parameters': {
                    'lookback_period': 20,
                    'deviation_threshold': 1.5,
                    'std_dev_threshold': 1.5,
                    'mean_reversion_threshold': 0.03,
                    'min_reversion_strength': 0.6,
                    'trend_filter': False
                }
            },
            'conservative_mean_reversion': {
                'strategy_type': StrategyType.MEAN_REVERSION,
                'parameters': {
                    'lookback_period': 20,
                    'deviation_threshold': 2.5,
                    'std_dev_threshold': 2.5,
                    'mean_reversion_threshold': 0.08,
                    'min_reversion_strength': 0.4,
                    'trend_filter': True
                }
            }
        }
        
        if template_name not in templates:
            available_templates = list(templates.keys())
            raise ValueError(
                f"Template {template_name} not found. "
                f"Available templates: {available_templates}"
            )
        
        template = templates[template_name]
        
        config = StrategyConfig(
            strategy_id=strategy_id,
            strategy_type=template['strategy_type'],
            name=f"{template_name.replace('_', ' ').title()} Strategy {strategy_id}",
            description=f"Strategy created from {template_name} template",
            symbols=symbols,
            parameters=template['parameters'],
            **kwargs
        )
        
        return self.create_strategy(config)
    
    def get_available_templates(self) -> List[str]:
        """
        Get list of available strategy templates.
        
        Returns:
            List of template names
        """
        return [
            'aggressive_momentum',
            'conservative_momentum',
            'aggressive_mean_reversion',
            'conservative_mean_reversion'
        ]
    
    def register_custom_strategy(
        self,
        strategy_type: StrategyType,
        strategy_class: Type[Strategy]
    ) -> None:
        """
        Register a custom strategy class.
        
        Args:
            strategy_type: Strategy type
            strategy_class: Strategy class to register
        """
        self.registry.register_strategy_class(strategy_type, strategy_class)
        self._strategy_classes[strategy_type] = strategy_class
        self.logger.info(f"Registered custom strategy: {strategy_type}")
    
    def get_factory_info(self) -> Dict:
        """
        Get information about the factory and registered strategies.
        
        Returns:
            Dictionary with factory information
        """
        return {
            'available_types': [str(t) for t in self.get_available_strategy_types()],
            'available_templates': self.get_available_templates(),
            'registered_strategies': len(self._strategy_classes),
            'registry_stats': self.registry.get_registry_stats()
        }


# Global factory instance
_global_factory = StrategyFactory()


def get_global_factory() -> StrategyFactory:
    """
    Get the global strategy factory instance.
    
    Returns:
        Global strategy factory
    """
    return _global_factory


def create_strategy(config: StrategyConfig) -> Strategy:
    """
    Create a strategy using the global factory.
    
    Args:
        config: Strategy configuration
        
    Returns:
        Strategy instance
    """
    return _global_factory.create_strategy(config)


def create_momentum_strategy(
    strategy_id: str,
    symbols: List[str],
    parameters: Dict = None,
    **kwargs
) -> MomentumStrategy:
    """
    Create a momentum strategy using the global factory.
    
    Args:
        strategy_id: Unique strategy identifier
        symbols: List of symbols to trade
        parameters: Strategy-specific parameters
        **kwargs: Additional configuration options
        
    Returns:
        Configured momentum strategy
    """
    return _global_factory.create_momentum_strategy(strategy_id, symbols, parameters, **kwargs)


def create_mean_reversion_strategy(
    strategy_id: str,
    symbols: List[str],
    parameters: Dict = None,
    **kwargs
) -> MeanReversionStrategy:
    """
    Create a mean reversion strategy using the global factory.
    
    Args:
        strategy_id: Unique strategy identifier
        symbols: List of symbols to trade
        parameters: Strategy-specific parameters
        **kwargs: Additional configuration options
        
    Returns:
        Configured mean reversion strategy
    """
    return _global_factory.create_mean_reversion_strategy(strategy_id, symbols, parameters, **kwargs)