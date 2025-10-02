"""
Logging configuration and utilities for the portfolio automation system.

This module provides centralized logging setup and utilities for consistent
logging across all components of the system.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime

from ..config.settings import get_config, LoggingConfig
from ..exceptions import SystemError


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class PortfolioLogger:
    """Enhanced logger with portfolio-specific functionality."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_done = False
    
    def _ensure_setup(self):
        """Ensure logging is properly configured."""
        if not self._setup_done:
            setup_logging()
            self._setup_done = True
    
    def debug(self, message: str, **kwargs):
        """Log debug message with optional extra fields."""
        self._ensure_setup()
        extra = {'extra_fields': kwargs} if kwargs else {}
        self.logger.debug(message, extra=extra)
    
    def info(self, message: str, **kwargs):
        """Log info message with optional extra fields."""
        self._ensure_setup()
        extra = {'extra_fields': kwargs} if kwargs else {}
        self.logger.info(message, extra=extra)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional extra fields."""
        self._ensure_setup()
        extra = {'extra_fields': kwargs} if kwargs else {}
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, **kwargs):
        """Log error message with optional extra fields."""
        self._ensure_setup()
        extra = {'extra_fields': kwargs} if kwargs else {}
        self.logger.error(message, extra=extra)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with optional extra fields."""
        self._ensure_setup()
        extra = {'extra_fields': kwargs} if kwargs else {}
        self.logger.critical(message, extra=extra)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback and optional extra fields."""
        self._ensure_setup()
        extra = {'extra_fields': kwargs} if kwargs else {}
        self.logger.exception(message, extra=extra)
    
    def trade_event(self, event_type: str, symbol: str, **kwargs):
        """Log trading-specific events."""
        self.info(f"Trade Event: {event_type}", 
                 event_type=event_type, 
                 symbol=symbol, 
                 **kwargs)
    
    def api_call(self, method: str, endpoint: str, status_code: Optional[int] = None, **kwargs):
        """Log API call events."""
        self.info(f"API Call: {method} {endpoint}", 
                 method=method, 
                 endpoint=endpoint, 
                 status_code=status_code, 
                 **kwargs)
    
    def risk_event(self, event_type: str, severity: str, **kwargs):
        """Log risk management events."""
        log_method = getattr(self, severity.lower(), self.info)
        log_method(f"Risk Event: {event_type}", 
                  event_type=event_type, 
                  severity=severity, 
                  **kwargs)
    
    def performance_metric(self, metric_name: str, value: float, **kwargs):
        """Log performance metrics."""
        self.info(f"Performance Metric: {metric_name}", 
                 metric_name=metric_name, 
                 value=value, 
                 **kwargs)


def setup_logging(config: Optional[LoggingConfig] = None) -> None:
    """
    Set up logging configuration for the entire application.
    
    Args:
        config: Optional logging configuration. If not provided, loads from system config.
    """
    if config is None:
        try:
            system_config = get_config()
            config = system_config.logging
        except Exception:
            # Fallback to default config if system config fails
            config = LoggingConfig()
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set logging level
    level = getattr(logging, config.level.upper(), logging.INFO)
    root_logger.setLevel(level)
    
    # Create formatters
    console_formatter = logging.Formatter(config.format)
    file_formatter = StructuredFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if configured)
    if config.file_path:
        try:
            # Ensure log directory exists
            log_path = Path(config.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                config.file_path,
                maxBytes=config.max_file_size,
                backupCount=config.backup_count
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            # Log to console if file logging setup fails
            console_handler.handle(logging.LogRecord(
                name="logging_setup",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg=f"Failed to setup file logging: {e}",
                args=(),
                exc_info=None
            ))
    
    # Set specific logger levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("alpaca_trade_api").setLevel(logging.INFO)


def get_logger(name: str) -> PortfolioLogger:
    """
    Get a portfolio-specific logger instance.
    
    Args:
        name: Logger name, typically __name__ of the calling module.
        
    Returns:
        PortfolioLogger instance.
    """
    return PortfolioLogger(name)


class LogContext:
    """Context manager for adding structured context to log messages."""
    
    def __init__(self, logger: PortfolioLogger, **context):
        self.logger = logger
        self.context = context
        self.old_context = {}
    
    def __enter__(self):
        # Store old context and add new context
        if hasattr(self.logger.logger, '_context'):
            self.old_context = self.logger.logger._context.copy()
        else:
            self.logger.logger._context = {}
        
        self.logger.logger._context.update(self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old context
        if self.old_context:
            self.logger.logger._context = self.old_context
        else:
            delattr(self.logger.logger, '_context')


def log_function_call(logger: PortfolioLogger):
    """Decorator to log function entry and exit."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Entering {func.__name__}", 
                        function=func.__name__, 
                        args=str(args)[:100], 
                        kwargs=str(kwargs)[:100])
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Exiting {func.__name__}", 
                           function=func.__name__, 
                           success=True)
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}", 
                           function=func.__name__, 
                           error=str(e))
                raise
        return wrapper
    return decorator


def log_execution_time(logger: PortfolioLogger):
    """Decorator to log function execution time."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"Function {func.__name__} executed", 
                          function=func.__name__, 
                          execution_time=execution_time)
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Function {func.__name__} failed", 
                           function=func.__name__, 
                           execution_time=execution_time, 
                           error=str(e))
                raise
        return wrapper
    return decorator