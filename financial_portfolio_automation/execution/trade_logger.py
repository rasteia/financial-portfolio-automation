"""
Trade logging and audit system for comprehensive transaction tracking.

This module provides comprehensive trade logging capabilities including
transaction logging, audit trails, and log rotation policies.
"""

import logging
import json
import csv
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
import threading
from dataclasses import dataclass, asdict
from enum import Enum
import gzip
import os

from ..models.core import Order, OrderSide, OrderType, OrderStatus, Position, PortfolioSnapshot
from ..execution.order_executor import ExecutionResult
from ..exceptions import SystemError


logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Log format enumeration."""
    JSON = "json"
    CSV = "csv"
    TEXT = "text"


@dataclass
class TradeLogEntry:
    """Trade log entry structure."""
    timestamp: datetime
    log_level: LogLevel
    event_type: str
    order_id: Optional[str]
    symbol: Optional[str]
    side: Optional[str]
    quantity: Optional[int]
    price: Optional[Decimal]
    order_type: Optional[str]
    status: Optional[str]
    filled_quantity: Optional[int]
    average_fill_price: Optional[Decimal]
    fees: Optional[Decimal]
    user_id: Optional[str]
    session_id: Optional[str]
    message: str
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert Decimal to float for JSON serialization
        if data['price'] is not None:
            data['price'] = float(data['price'])
        if data['average_fill_price'] is not None:
            data['average_fill_price'] = float(data['average_fill_price'])
        if data['fees'] is not None:
            data['fees'] = float(data['fees'])
        # Convert datetime to ISO string
        data['timestamp'] = data['timestamp'].isoformat()
        # Convert enums to strings
        data['log_level'] = data['log_level'].value if data['log_level'] else None
        return data


@dataclass
class LogRotationConfig:
    """Log rotation configuration."""
    max_file_size_mb: int = 100
    max_files: int = 10
    rotation_interval_hours: int = 24
    compress_old_files: bool = True
    archive_directory: Optional[str] = None


class TradeLogger:
    """
    Comprehensive trade logging and audit system.
    
    Provides transaction logging, audit trails, log rotation,
    and various output formats for compliance and analysis.
    """
    
    def __init__(self, log_directory: str = "logs", 
                 log_format: LogFormat = LogFormat.JSON,
                 rotation_config: Optional[LogRotationConfig] = None,
                 user_id: Optional[str] = None):
        """
        Initialize the trade logger.
        
        Args:
            log_directory: Directory to store log files
            log_format: Format for log files
            rotation_config: Log rotation configuration
            user_id: User ID for audit trail
        """
        self.log_directory = Path(log_directory)
        self.log_format = log_format
        self.rotation_config = rotation_config or LogRotationConfig()
        self.user_id = user_id
        self.session_id = self._generate_session_id()
        
        # Create log directory if it doesn't exist
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Log file paths
        self.trade_log_file = self.log_directory / f"trades.{log_format.value}"
        self.audit_log_file = self.log_directory / f"audit.{log_format.value}"
        self.error_log_file = self.log_directory / f"errors.{log_format.value}"
        
        # Thread safety
        self._log_lock = threading.Lock()
        
        # Statistics
        self._log_stats = {
            'total_entries': 0,
            'trade_entries': 0,
            'audit_entries': 0,
            'error_entries': 0,
            'files_rotated': 0
        }
        
        # Initialize log files with headers if needed
        self._initialize_log_files()
        
        logger.info(f"TradeLogger initialized with format {log_format.value}")
    
    def log_order_submission(self, order: Order, execution_result: Optional[ExecutionResult] = None) -> None:
        """
        Log order submission event.
        
        Args:
            order: Order that was submitted
            execution_result: Result of order execution (if available)
        """
        try:
            metadata = {
                'event_category': 'order_lifecycle',
                'execution_strategy': getattr(order, 'execution_strategy', None),
                'time_in_force': order.time_in_force
            }
            
            if execution_result:
                metadata.update({
                    'execution_success': execution_result.success,
                    'execution_time': execution_result.execution_time.isoformat() if execution_result.execution_time else None,
                    'error_message': execution_result.error_message
                })
            
            entry = TradeLogEntry(
                timestamp=datetime.now(timezone.utc),
                log_level=LogLevel.INFO,
                event_type="order_submitted",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side.value,
                quantity=order.quantity,
                price=order.limit_price,
                order_type=order.order_type.value,
                status=order.status.value,
                filled_quantity=order.filled_quantity,
                average_fill_price=order.average_fill_price,
                fees=None,
                user_id=self.user_id,
                session_id=self.session_id,
                message=f"Order submitted: {order.side.value} {order.quantity} {order.symbol}",
                metadata=metadata
            )
            
            self._write_log_entry(entry, self.trade_log_file)
            self._log_stats['trade_entries'] += 1
            
        except Exception as e:
            logger.error(f"Error logging order submission: {str(e)}")
    
    def log_order_fill(self, order: Order, fill_price: Decimal, fill_quantity: int, 
                      fees: Optional[Decimal] = None) -> None:
        """
        Log order fill event.
        
        Args:
            order: Order that was filled
            fill_price: Price at which order was filled
            fill_quantity: Quantity that was filled
            fees: Trading fees (if any)
        """
        try:
            metadata = {
                'event_category': 'order_lifecycle',
                'partial_fill': fill_quantity < order.quantity,
                'remaining_quantity': order.quantity - fill_quantity,
                'cumulative_filled': order.filled_quantity + fill_quantity
            }
            
            entry = TradeLogEntry(
                timestamp=datetime.now(timezone.utc),
                log_level=LogLevel.INFO,
                event_type="order_filled",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side.value,
                quantity=fill_quantity,
                price=fill_price,
                order_type=order.order_type.value,
                status=order.status.value,
                filled_quantity=fill_quantity,
                average_fill_price=fill_price,
                fees=fees,
                user_id=self.user_id,
                session_id=self.session_id,
                message=f"Order filled: {fill_quantity} {order.symbol} at ${fill_price}",
                metadata=metadata
            )
            
            self._write_log_entry(entry, self.trade_log_file)
            self._log_stats['trade_entries'] += 1
            
        except Exception as e:
            logger.error(f"Error logging order fill: {str(e)}")
    
    def log_order_cancellation(self, order: Order, reason: str = "User requested") -> None:
        """
        Log order cancellation event.
        
        Args:
            order: Order that was cancelled
            reason: Reason for cancellation
        """
        try:
            metadata = {
                'event_category': 'order_lifecycle',
                'cancellation_reason': reason,
                'filled_before_cancel': order.filled_quantity > 0
            }
            
            entry = TradeLogEntry(
                timestamp=datetime.now(timezone.utc),
                log_level=LogLevel.INFO,
                event_type="order_cancelled",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side.value,
                quantity=order.quantity,
                price=order.limit_price,
                order_type=order.order_type.value,
                status=OrderStatus.CANCELLED.value,
                filled_quantity=order.filled_quantity,
                average_fill_price=order.average_fill_price,
                fees=None,
                user_id=self.user_id,
                session_id=self.session_id,
                message=f"Order cancelled: {order.order_id} - {reason}",
                metadata=metadata
            )
            
            self._write_log_entry(entry, self.trade_log_file)
            self._log_stats['trade_entries'] += 1
            
        except Exception as e:
            logger.error(f"Error logging order cancellation: {str(e)}")
    
    def log_risk_violation(self, violation_type: str, symbol: Optional[str], 
                          message: str, severity: str = "medium") -> None:
        """
        Log risk management violation.
        
        Args:
            violation_type: Type of risk violation
            symbol: Symbol involved (if any)
            message: Violation message
            severity: Severity level
        """
        try:
            log_level = LogLevel.WARNING
            if severity in ["high", "critical"]:
                log_level = LogLevel.ERROR
            
            metadata = {
                'event_category': 'risk_management',
                'violation_type': violation_type,
                'severity': severity
            }
            
            entry = TradeLogEntry(
                timestamp=datetime.now(timezone.utc),
                log_level=log_level,
                event_type="risk_violation",
                order_id=None,
                symbol=symbol,
                side=None,
                quantity=None,
                price=None,
                order_type=None,
                status=None,
                filled_quantity=None,
                average_fill_price=None,
                fees=None,
                user_id=self.user_id,
                session_id=self.session_id,
                message=message,
                metadata=metadata
            )
            
            self._write_log_entry(entry, self.audit_log_file)
            self._log_stats['audit_entries'] += 1
            
        except Exception as e:
            logger.error(f"Error logging risk violation: {str(e)}")
    
    def log_portfolio_snapshot(self, portfolio: PortfolioSnapshot) -> None:
        """
        Log portfolio snapshot for audit trail.
        
        Args:
            portfolio: Portfolio snapshot to log
        """
        try:
            metadata = {
                'event_category': 'portfolio_tracking',
                'position_count': len(portfolio.positions),
                'total_value': float(portfolio.total_value),
                'day_pnl': float(portfolio.day_pnl),
                'total_pnl': float(portfolio.total_pnl),
                'positions': [
                    {
                        'symbol': pos.symbol,
                        'quantity': pos.quantity,
                        'market_value': float(pos.market_value),
                        'unrealized_pnl': float(pos.unrealized_pnl)
                    }
                    for pos in portfolio.positions
                ]
            }
            
            entry = TradeLogEntry(
                timestamp=portfolio.timestamp,
                log_level=LogLevel.INFO,
                event_type="portfolio_snapshot",
                order_id=None,
                symbol=None,
                side=None,
                quantity=None,
                price=None,
                order_type=None,
                status=None,
                filled_quantity=None,
                average_fill_price=None,
                fees=None,
                user_id=self.user_id,
                session_id=self.session_id,
                message=f"Portfolio snapshot: ${portfolio.total_value:,.2f} total value",
                metadata=metadata
            )
            
            self._write_log_entry(entry, self.audit_log_file)
            self._log_stats['audit_entries'] += 1
            
        except Exception as e:
            logger.error(f"Error logging portfolio snapshot: {str(e)}")
    
    def log_system_event(self, event_type: str, message: str, 
                        level: LogLevel = LogLevel.INFO, metadata: Optional[Dict] = None) -> None:
        """
        Log system event for audit trail.
        
        Args:
            event_type: Type of system event
            message: Event message
            level: Log level
            metadata: Additional metadata
        """
        try:
            event_metadata = {
                'event_category': 'system',
                'event_type': event_type
            }
            if metadata:
                event_metadata.update(metadata)
            
            entry = TradeLogEntry(
                timestamp=datetime.now(timezone.utc),
                log_level=level,
                event_type=event_type,
                order_id=None,
                symbol=None,
                side=None,
                quantity=None,
                price=None,
                order_type=None,
                status=None,
                filled_quantity=None,
                average_fill_price=None,
                fees=None,
                user_id=self.user_id,
                session_id=self.session_id,
                message=message,
                metadata=event_metadata
            )
            
            log_file = self.error_log_file if level in [LogLevel.ERROR, LogLevel.CRITICAL] else self.audit_log_file
            self._write_log_entry(entry, log_file)
            
            if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                self._log_stats['error_entries'] += 1
            else:
                self._log_stats['audit_entries'] += 1
            
        except Exception as e:
            logger.error(f"Error logging system event: {str(e)}")
    
    def log_error(self, error: Exception, context: Optional[Dict] = None) -> None:
        """
        Log error with context information.
        
        Args:
            error: Exception that occurred
            context: Additional context information
        """
        try:
            metadata = {
                'event_category': 'error',
                'error_type': type(error).__name__,
                'error_message': str(error)
            }
            if context:
                metadata.update(context)
            
            entry = TradeLogEntry(
                timestamp=datetime.now(timezone.utc),
                log_level=LogLevel.ERROR,
                event_type="error",
                order_id=context.get('order_id') if context else None,
                symbol=context.get('symbol') if context else None,
                side=None,
                quantity=None,
                price=None,
                order_type=None,
                status=None,
                filled_quantity=None,
                average_fill_price=None,
                fees=None,
                user_id=self.user_id,
                session_id=self.session_id,
                message=f"Error occurred: {str(error)}",
                metadata=metadata
            )
            
            self._write_log_entry(entry, self.error_log_file)
            self._log_stats['error_entries'] += 1
            
        except Exception as e:
            logger.error(f"Error logging error: {str(e)}")
    
    def get_trade_history(self, symbol: Optional[str] = None, 
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve trade history with optional filtering.
        
        Args:
            symbol: Filter by symbol
            start_date: Start date for filtering
            end_date: End date for filtering
            limit: Maximum number of entries to return
            
        Returns:
            List of trade log entries
        """
        try:
            entries = []
            
            if not self.trade_log_file.exists():
                return entries
            
            with open(self.trade_log_file, 'r') as f:
                if self.log_format == LogFormat.JSON:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            
                            # Apply filters
                            if symbol and entry.get('symbol') != symbol:
                                continue
                            
                            if start_date or end_date:
                                entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                                if start_date and entry_time < start_date:
                                    continue
                                if end_date and entry_time > end_date:
                                    continue
                            
                            entries.append(entry)
                            
                            if limit and len(entries) >= limit:
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                elif self.log_format == LogFormat.CSV:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Apply filters (simplified for CSV)
                        if symbol and row.get('symbol') != symbol:
                            continue
                        
                        entries.append(row)
                        
                        if limit and len(entries) >= limit:
                            break
            
            return entries
            
        except Exception as e:
            logger.error(f"Error retrieving trade history: {str(e)}")
            return []
    
    def rotate_logs(self) -> None:
        """Rotate log files based on configuration."""
        try:
            with self._log_lock:
                for log_file in [self.trade_log_file, self.audit_log_file, self.error_log_file]:
                    if log_file.exists():
                        self._rotate_single_file(log_file)
                
                self._log_stats['files_rotated'] += 1
                
        except Exception as e:
            logger.error(f"Error rotating logs: {str(e)}")
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """
        Get logging statistics.
        
        Returns:
            Dictionary with logging metrics
        """
        stats = self._log_stats.copy()
        
        # Add file sizes
        for log_type, log_file in [
            ('trade_log_size_mb', self.trade_log_file),
            ('audit_log_size_mb', self.audit_log_file),
            ('error_log_size_mb', self.error_log_file)
        ]:
            if log_file.exists():
                stats[log_type] = log_file.stat().st_size / (1024 * 1024)
            else:
                stats[log_type] = 0
        
        return stats
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    
    def _initialize_log_files(self) -> None:
        """Initialize log files with headers if needed."""
        if self.log_format == LogFormat.CSV:
            headers = [
                'timestamp', 'log_level', 'event_type', 'order_id', 'symbol',
                'side', 'quantity', 'price', 'order_type', 'status',
                'filled_quantity', 'average_fill_price', 'fees', 'user_id',
                'session_id', 'message', 'metadata'
            ]
            
            for log_file in [self.trade_log_file, self.audit_log_file, self.error_log_file]:
                if not log_file.exists():
                    with open(log_file, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(headers)
    
    def _write_log_entry(self, entry: TradeLogEntry, log_file: Path) -> None:
        """Write log entry to file."""
        with self._log_lock:
            try:
                # Check if rotation is needed
                if log_file.exists() and log_file.stat().st_size > self.rotation_config.max_file_size_mb * 1024 * 1024:
                    self._rotate_single_file(log_file)
                
                with open(log_file, 'a', encoding='utf-8') as f:
                    if self.log_format == LogFormat.JSON:
                        json.dump(entry.to_dict(), f, ensure_ascii=False)
                        f.write('\n')
                    
                    elif self.log_format == LogFormat.CSV:
                        writer = csv.writer(f)
                        entry_dict = entry.to_dict()
                        row = [
                            entry_dict.get('timestamp', ''),
                            entry_dict.get('log_level', ''),
                            entry_dict.get('event_type', ''),
                            entry_dict.get('order_id', ''),
                            entry_dict.get('symbol', ''),
                            entry_dict.get('side', ''),
                            entry_dict.get('quantity', ''),
                            entry_dict.get('price', ''),
                            entry_dict.get('order_type', ''),
                            entry_dict.get('status', ''),
                            entry_dict.get('filled_quantity', ''),
                            entry_dict.get('average_fill_price', ''),
                            entry_dict.get('fees', ''),
                            entry_dict.get('user_id', ''),
                            entry_dict.get('session_id', ''),
                            entry_dict.get('message', ''),
                            json.dumps(entry_dict.get('metadata', {}))
                        ]
                        writer.writerow(row)
                    
                    elif self.log_format == LogFormat.TEXT:
                        timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
                        f.write(f"[{timestamp}] {entry.log_level.value} - {entry.message}\n")
                
                self._log_stats['total_entries'] += 1
                
            except Exception as e:
                logger.error(f"Error writing log entry: {str(e)}")
    
    def _rotate_single_file(self, log_file: Path) -> None:
        """Rotate a single log file."""
        try:
            if not log_file.exists():
                return
            
            # Generate rotated filename with timestamp
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            rotated_name = f"{log_file.stem}_{timestamp}{log_file.suffix}"
            
            # Determine destination directory
            if self.rotation_config.archive_directory:
                archive_dir = Path(self.rotation_config.archive_directory)
                archive_dir.mkdir(parents=True, exist_ok=True)
                rotated_path = archive_dir / rotated_name
            else:
                rotated_path = log_file.parent / rotated_name
            
            # Move current file to rotated name
            log_file.rename(rotated_path)
            
            # Compress if configured
            if self.rotation_config.compress_old_files:
                compressed_path = rotated_path.with_suffix(rotated_path.suffix + '.gz')
                with open(rotated_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        f_out.writelines(f_in)
                rotated_path.unlink()  # Remove uncompressed file
            
            # Clean up old files
            self._cleanup_old_files(log_file)
            
            # Reinitialize file if CSV format
            if self.log_format == LogFormat.CSV:
                self._initialize_log_files()
            
        except Exception as e:
            logger.error(f"Error rotating file {log_file}: {str(e)}")
    
    def _cleanup_old_files(self, log_file: Path) -> None:
        """Clean up old rotated files based on retention policy."""
        try:
            # Find all rotated files for this log
            pattern = f"{log_file.stem}_*"
            
            # Search in both current directory and archive directory
            search_dirs = [log_file.parent]
            if self.rotation_config.archive_directory:
                search_dirs.append(Path(self.rotation_config.archive_directory))
            
            all_rotated_files = []
            for search_dir in search_dirs:
                if search_dir.exists():
                    all_rotated_files.extend(search_dir.glob(pattern))
            
            # Sort by modification time (newest first)
            all_rotated_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove files beyond max_files limit
            if len(all_rotated_files) > self.rotation_config.max_files:
                for old_file in all_rotated_files[self.rotation_config.max_files:]:
                    try:
                        old_file.unlink()
                    except Exception as e:
                        logger.warning(f"Could not delete old log file {old_file}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error cleaning up old files: {str(e)}")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            # Log session end
            self.log_system_event(
                "session_end",
                f"Trade logging session ended: {self.session_id}",
                LogLevel.INFO
            )
        except:
            pass  # Ignore errors during cleanup