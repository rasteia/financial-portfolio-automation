"""
Strategy registry for managing and organizing trading strategies.

This module provides a centralized registry for strategy registration,
discovery, and lifecycle management.
"""

from typing import Dict, List, Type, Optional, Any
import logging
from threading import Lock

from .base import Strategy
from ..models.config import StrategyConfig, StrategyType


logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    Registry for managing trading strategy classes and instances.
    
    This class provides a centralized way to register strategy classes,
    create strategy instances, and manage their lifecycle.
    """
    
    def __init__(self):
        """Initialize the strategy registry."""
        self._strategy_classes: Dict[StrategyType, Type[Strategy]] = {}
        self._strategy_instances: Dict[str, Strategy] = {}
        self._lock = Lock()
        self.logger = logging.getLogger(__name__)
    
    def register_strategy_class(
        self,
        strategy_type: StrategyType,
        strategy_class: Type[Strategy]
    ) -> None:
        """
        Register a strategy class for a specific strategy type.
        
        Args:
            strategy_type: Type of strategy
            strategy_class: Strategy class to register
            
        Raises:
            ValueError: If strategy class is invalid or already registered
        """
        with self._lock:
            # Validate strategy class
            if not issubclass(strategy_class, Strategy):
                raise ValueError(f"Strategy class must inherit from Strategy base class")
            
            # Check if already registered
            if strategy_type in self._strategy_classes:
                existing_class = self._strategy_classes[strategy_type]
                if existing_class != strategy_class:
                    self.logger.warning(
                        f"Overriding existing strategy class for {strategy_type}: "
                        f"{existing_class.__name__} -> {strategy_class.__name__}"
                    )
            
            self._strategy_classes[strategy_type] = strategy_class
            self.logger.info(f"Registered strategy class {strategy_class.__name__} for type {strategy_type}")
    
    def unregister_strategy_class(self, strategy_type: StrategyType) -> None:
        """
        Unregister a strategy class.
        
        Args:
            strategy_type: Type of strategy to unregister
        """
        with self._lock:
            if strategy_type in self._strategy_classes:
                class_name = self._strategy_classes[strategy_type].__name__
                del self._strategy_classes[strategy_type]
                self.logger.info(f"Unregistered strategy class {class_name} for type {strategy_type}")
            else:
                self.logger.warning(f"No strategy class registered for type {strategy_type}")
    
    def get_strategy_class(self, strategy_type: StrategyType) -> Optional[Type[Strategy]]:
        """
        Get registered strategy class for a type.
        
        Args:
            strategy_type: Type of strategy
            
        Returns:
            Strategy class if registered, None otherwise
        """
        with self._lock:
            return self._strategy_classes.get(strategy_type)
    
    def list_registered_types(self) -> List[StrategyType]:
        """
        Get list of registered strategy types.
        
        Returns:
            List of registered strategy types
        """
        with self._lock:
            return list(self._strategy_classes.keys())
    
    def create_strategy(self, config: StrategyConfig) -> Strategy:
        """
        Create a strategy instance from configuration.
        
        Args:
            config: Strategy configuration
            
        Returns:
            Strategy instance
            
        Raises:
            ValueError: If strategy type is not registered or creation fails
        """
        with self._lock:
            # Check if strategy type is registered
            if config.strategy_type not in self._strategy_classes:
                available_types = list(self._strategy_classes.keys())
                raise ValueError(
                    f"Strategy type {config.strategy_type} not registered. "
                    f"Available types: {available_types}"
                )
            
            # Check if strategy instance already exists
            if config.strategy_id in self._strategy_instances:
                raise ValueError(f"Strategy with ID {config.strategy_id} already exists")
            
            # Create strategy instance
            strategy_class = self._strategy_classes[config.strategy_type]
            try:
                strategy = strategy_class(config)
                self._strategy_instances[config.strategy_id] = strategy
                self.logger.info(f"Created strategy instance {config.strategy_id}")
                return strategy
            except Exception as e:
                self.logger.error(f"Failed to create strategy {config.strategy_id}: {e}")
                raise ValueError(f"Failed to create strategy: {e}")
    
    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """
        Get strategy instance by ID.
        
        Args:
            strategy_id: Strategy ID
            
        Returns:
            Strategy instance if exists, None otherwise
        """
        with self._lock:
            return self._strategy_instances.get(strategy_id)
    
    def remove_strategy(self, strategy_id: str) -> bool:
        """
        Remove strategy instance from registry.
        
        Args:
            strategy_id: Strategy ID to remove
            
        Returns:
            True if strategy was removed, False if not found
        """
        with self._lock:
            if strategy_id in self._strategy_instances:
                strategy = self._strategy_instances[strategy_id]
                strategy.deactivate()  # Ensure strategy is deactivated
                del self._strategy_instances[strategy_id]
                self.logger.info(f"Removed strategy instance {strategy_id}")
                return True
            else:
                self.logger.warning(f"Strategy {strategy_id} not found for removal")
                return False
    
    def list_strategies(self, active_only: bool = False) -> List[Strategy]:
        """
        Get list of strategy instances.
        
        Args:
            active_only: If True, return only active strategies
            
        Returns:
            List of strategy instances
        """
        with self._lock:
            strategies = list(self._strategy_instances.values())
            if active_only:
                strategies = [s for s in strategies if s.is_active]
            return strategies
    
    def get_strategies_by_type(self, strategy_type: StrategyType) -> List[Strategy]:
        """
        Get strategies of a specific type.
        
        Args:
            strategy_type: Strategy type to filter by
            
        Returns:
            List of strategies of the specified type
        """
        with self._lock:
            return [
                strategy for strategy in self._strategy_instances.values()
                if strategy.config.strategy_type == strategy_type
            ]
    
    def get_strategies_by_symbol(self, symbol: str) -> List[Strategy]:
        """
        Get strategies that trade a specific symbol.
        
        Args:
            symbol: Symbol to filter by
            
        Returns:
            List of strategies that trade the symbol
        """
        with self._lock:
            return [
                strategy for strategy in self._strategy_instances.values()
                if symbol in strategy.symbols
            ]
    
    def activate_strategy(self, strategy_id: str) -> bool:
        """
        Activate a strategy.
        
        Args:
            strategy_id: Strategy ID to activate
            
        Returns:
            True if strategy was activated, False if not found
        """
        with self._lock:
            strategy = self._strategy_instances.get(strategy_id)
            if strategy:
                strategy.activate()
                return True
            return False
    
    def deactivate_strategy(self, strategy_id: str) -> bool:
        """
        Deactivate a strategy.
        
        Args:
            strategy_id: Strategy ID to deactivate
            
        Returns:
            True if strategy was deactivated, False if not found
        """
        with self._lock:
            strategy = self._strategy_instances.get(strategy_id)
            if strategy:
                strategy.deactivate()
                return True
            return False
    
    def deactivate_all_strategies(self) -> None:
        """Deactivate all registered strategies."""
        with self._lock:
            for strategy in self._strategy_instances.values():
                strategy.deactivate()
            self.logger.info("Deactivated all strategies")
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary containing registry statistics
        """
        with self._lock:
            total_strategies = len(self._strategy_instances)
            active_strategies = len([s for s in self._strategy_instances.values() if s.is_active])
            
            type_counts = {}
            for strategy in self._strategy_instances.values():
                strategy_type = strategy.strategy_type
                type_counts[strategy_type] = type_counts.get(strategy_type, 0) + 1
            
            return {
                'registered_classes': len(self._strategy_classes),
                'total_strategies': total_strategies,
                'active_strategies': active_strategies,
                'inactive_strategies': total_strategies - active_strategies,
                'strategy_types': list(self._strategy_classes.keys()),
                'type_distribution': type_counts
            }
    
    def clear_all(self) -> None:
        """Clear all registered strategies and classes."""
        with self._lock:
            # Deactivate all strategies first
            for strategy in self._strategy_instances.values():
                strategy.deactivate()
            
            self._strategy_instances.clear()
            self._strategy_classes.clear()
            self.logger.info("Cleared all strategies and classes from registry")


# Global strategy registry instance
_global_registry = StrategyRegistry()


def get_global_registry() -> StrategyRegistry:
    """
    Get the global strategy registry instance.
    
    Returns:
        Global strategy registry
    """
    return _global_registry


def register_strategy_class(strategy_type: StrategyType, strategy_class: Type[Strategy]) -> None:
    """
    Register a strategy class in the global registry.
    
    Args:
        strategy_type: Type of strategy
        strategy_class: Strategy class to register
    """
    _global_registry.register_strategy_class(strategy_type, strategy_class)


def create_strategy(config: StrategyConfig) -> Strategy:
    """
    Create a strategy instance using the global registry.
    
    Args:
        config: Strategy configuration
        
    Returns:
        Strategy instance
    """
    return _global_registry.create_strategy(config)