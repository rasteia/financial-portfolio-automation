# Task 4 Handoff Document: Data Management and Storage Layer

## Overview

This document provides comprehensive guidance for implementing Task 4 of the Financial Portfolio Automation system: **Create data management and storage layer**. This task involves building the foundational data infrastructure that will store, cache, and validate all market data, portfolio information, and trading records.

## Task Breakdown

### 4.1 Implement data store with SQLite backend
- Create database schema for quotes, trades, positions, and orders
- Implement DataStore class with CRUD operations
- Add database migration and schema versioning
- Write unit tests for all database operations
- **Requirements**: 2.2, 7.1, 7.3

### 4.2 Implement data caching system
- Create DataCache class with in-memory caching
- Add TTL-based cache expiration and cleanup
- Implement cache warming and invalidation strategies
- Write unit tests for cache operations and edge cases
- **Requirements**: 2.1, 2.4

### 4.3 Implement data validator for quality assurance
- Create DataValidator class with validation rules
- Add price bounds checking and timestamp validation
- Implement data consistency checks across related records
- Write unit tests for all validation scenarios
- **Requirements**: 2.4, 7.4

## Current System Context

### Existing Components
The system already has these foundational components that Task 4 will integrate with:

1. **Core Data Models** (`financial_portfolio_automation/models/core.py`):
   - `Quote`: Market quote data with bid/ask prices
   - `Position`: Portfolio position information
   - `Order`: Trading order details
   - `PortfolioSnapshot`: Complete portfolio state at a point in time

2. **Exception Hierarchy** (`financial_portfolio_automation/exceptions.py`):
   - `DatabaseError`: For database operation failures
   - `DataError`: For data quality issues
   - `ValidationError`: For data validation failures

3. **API Integration Layer** (`financial_portfolio_automation/api/`):
   - `AlpacaClient`: Authenticated API client
   - `WebSocketHandler`: Real-time data streaming
   - `MarketDataClient`: Market data retrieval

4. **Configuration System** (`financial_portfolio_automation/config/`):
   - Environment-based configuration management
   - Logging configuration

### Project Structure
```
financial_portfolio_automation/
├── api/                    # API integration layer (existing)
├── config/                 # Configuration management (existing)
├── models/                 # Data models (existing)
├── utils/                  # Utility functions (existing)
├── data/                   # NEW: Data management layer
│   ├── __init__.py
│   ├── store.py           # DataStore implementation
│   ├── cache.py           # DataCache implementation
│   ├── validator.py       # DataValidator implementation
│   └── migrations/        # Database migration scripts
└── exceptions.py          # Exception classes (existing)
```

## Detailed Implementation Guide

### 4.1 Data Store Implementation

#### Database Schema Design

Based on the existing data models, create the following SQLite tables:

```sql
-- Market data tables
CREATE TABLE quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    bid DECIMAL(10,4) NOT NULL,
    ask DECIMAL(10,4) NOT NULL,
    bid_size INTEGER NOT NULL,
    ask_size INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp)
);

CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    price DECIMAL(10,4) NOT NULL,
    size INTEGER NOT NULL,
    conditions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp, price, size)
);

-- Portfolio data tables
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    market_value DECIMAL(15,4) NOT NULL,
    cost_basis DECIMAL(15,4) NOT NULL,
    unrealized_pnl DECIMAL(15,4) NOT NULL,
    day_pnl DECIMAL(15,4) NOT NULL,
    snapshot_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (snapshot_id) REFERENCES portfolio_snapshots(id)
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    order_type TEXT NOT NULL CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit')),
    status TEXT NOT NULL CHECK (status IN ('new', 'partially_filled', 'filled', 'cancelled', 'rejected', 'expired')),
    filled_quantity INTEGER DEFAULT 0,
    average_fill_price DECIMAL(10,4),
    limit_price DECIMAL(10,4),
    stop_price DECIMAL(10,4),
    time_in_force TEXT DEFAULT 'day',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    total_value DECIMAL(15,4) NOT NULL,
    buying_power DECIMAL(15,4) NOT NULL,
    day_pnl DECIMAL(15,4) NOT NULL,
    total_pnl DECIMAL(15,4) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp)
);

-- Indexes for performance
CREATE INDEX idx_quotes_symbol_timestamp ON quotes(symbol, timestamp);
CREATE INDEX idx_trades_symbol_timestamp ON trades(symbol, timestamp);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_portfolio_snapshots_timestamp ON portfolio_snapshots(timestamp);

-- Schema versioning
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_version (version) VALUES (1);
```

#### DataStore Class Implementation

Create `financial_portfolio_automation/data/store.py`:

```python
"""
Data store implementation with SQLite backend.
"""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any, Generator
from dataclasses import asdict

from ..models.core import Quote, Position, Order, PortfolioSnapshot
from ..exceptions import DatabaseError, ValidationError


class DataStore:
    """SQLite-based data store for portfolio automation system."""
    
    def __init__(self, db_path: str = "portfolio.db"):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self._ensure_database_exists()
    
    def _ensure_database_exists(self) -> None:
        """Ensure database exists and is properly initialized."""
        try:
            with self.get_connection() as conn:
                # Check if schema_version table exists
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
                )
                if not cursor.fetchone():
                    self._initialize_schema(conn)
                else:
                    self._check_schema_version(conn)
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database: {e}")
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            if conn:
                conn.close()
    
    # Quote operations
    def save_quote(self, quote: Quote) -> None:
        """Save a quote to the database."""
        # Implementation details...
    
    def get_quotes(self, symbol: str, start_time: datetime = None, 
                   end_time: datetime = None, limit: int = None) -> List[Quote]:
        """Retrieve quotes for a symbol within a time range."""
        # Implementation details...
    
    # Position operations
    def save_position(self, position: Position, snapshot_id: int = None) -> None:
        """Save a position to the database."""
        # Implementation details...
    
    # Order operations
    def save_order(self, order: Order) -> None:
        """Save an order to the database."""
        # Implementation details...
    
    def update_order(self, order: Order) -> None:
        """Update an existing order."""
        # Implementation details...
    
    # Portfolio snapshot operations
    def save_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> int:
        """Save a portfolio snapshot and return its ID."""
        # Implementation details...
    
    # Migration support
    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema."""
        # Execute schema creation SQL
        
    def _check_schema_version(self, conn: sqlite3.Connection) -> None:
        """Check and upgrade schema if needed."""
        # Check current version and apply migrations
```

### 4.2 Data Cache Implementation

Create `financial_portfolio_automation/data/cache.py`:

```python
"""
In-memory data caching system with TTL support.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Set, Callable
from dataclasses import dataclass
from collections import defaultdict

from ..exceptions import DataError


@dataclass
class CacheEntry:
    """Represents a cached data entry with TTL."""
    value: Any
    expires_at: float
    access_count: int = 0
    last_accessed: float = 0
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() > self.expires_at
    
    def touch(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()


class DataCache:
    """Thread-safe in-memory cache with TTL and cleanup strategies."""
    
    def __init__(self, default_ttl: int = 300, cleanup_interval: int = 60):
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._cleanup_timer: Optional[threading.Timer] = None
        self._start_cleanup_timer()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            if entry.is_expired():
                del self._cache[key]
                return None
            
            entry.touch()
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        
        with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=expires_at,
                last_accessed=time.time()
            )
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            return self._cache.pop(key, None) is not None
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())
            return {
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'active_entries': total_entries - expired_entries,
                'hit_rate': self._calculate_hit_rate()
            }
    
    # Cache warming and invalidation strategies
    def warm_cache(self, data_loader: Callable[[str], Any], keys: List[str]) -> None:
        """Pre-load cache with data."""
        # Implementation details...
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        # Implementation details...
```

### 4.3 Data Validator Implementation

Create `financial_portfolio_automation/data/validator.py`:

```python
"""
Data validation system for quality assurance.
"""

import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..models.core import Quote, Position, Order, PortfolioSnapshot
from ..exceptions import ValidationError


@dataclass
class ValidationRule:
    """Represents a data validation rule."""
    name: str
    description: str
    severity: str  # 'error', 'warning', 'info'
    validator: callable


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]


class DataValidator:
    """Comprehensive data validation system."""
    
    def __init__(self):
        self.rules: Dict[str, List[ValidationRule]] = {
            'quote': self._get_quote_rules(),
            'position': self._get_position_rules(),
            'order': self._get_order_rules(),
            'portfolio': self._get_portfolio_rules()
        }
    
    def validate_quote(self, quote: Quote) -> ValidationResult:
        """Validate a quote object."""
        return self._validate_object(quote, 'quote')
    
    def validate_position(self, position: Position) -> ValidationResult:
        """Validate a position object."""
        return self._validate_object(position, 'position')
    
    def validate_order(self, order: Order) -> ValidationResult:
        """Validate an order object."""
        return self._validate_object(order, 'order')
    
    def validate_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> ValidationResult:
        """Validate a portfolio snapshot."""
        return self._validate_object(snapshot, 'portfolio')
    
    def validate_price_bounds(self, symbol: str, price: Decimal) -> bool:
        """Validate price is within reasonable bounds."""
        # Implementation: Check against historical ranges, circuit breakers, etc.
        
    def validate_timestamp_consistency(self, timestamps: List[datetime]) -> ValidationResult:
        """Validate timestamp ordering and consistency."""
        # Implementation: Check for proper ordering, no future dates, etc.
    
    def validate_data_consistency(self, quotes: List[Quote], trades: List[Any]) -> ValidationResult:
        """Validate consistency between related data records."""
        # Implementation: Cross-validate quotes vs trades, position calculations, etc.
    
    def _get_quote_rules(self) -> List[ValidationRule]:
        """Get validation rules for quotes."""
        return [
            ValidationRule(
                name="price_bounds",
                description="Prices must be within reasonable bounds",
                severity="error",
                validator=lambda q: 0 < q.bid < 100000 and 0 < q.ask < 100000
            ),
            ValidationRule(
                name="spread_check",
                description="Bid-ask spread should be reasonable",
                severity="warning",
                validator=lambda q: (q.ask - q.bid) / q.bid < 0.1  # 10% max spread
            ),
            # Add more rules...
        ]
    
    # Similar methods for other data types...
```

## Testing Strategy

### Unit Test Structure

Create comprehensive unit tests for each component:

```
tests/
├── test_data_store.py          # DataStore tests
├── test_data_cache.py          # DataCache tests
├── test_data_validator.py      # DataValidator tests
└── integration/
    └── test_data_integration.py # Integration tests
```

### Key Test Scenarios

1. **DataStore Tests**:
   - Database initialization and schema creation
   - CRUD operations for all data types
   - Transaction handling and rollback
   - Migration system
   - Concurrent access handling
   - Error conditions and recovery

2. **DataCache Tests**:
   - Basic get/set operations
   - TTL expiration
   - Cache cleanup and memory management
   - Thread safety
   - Cache warming and invalidation
   - Performance under load

3. **DataValidator Tests**:
   - Individual validation rules
   - Composite validation scenarios
   - Edge cases and boundary conditions
   - Performance with large datasets
   - Custom validation rule registration

### Sample Test Implementation

```python
# tests/test_data_store.py
import pytest
import tempfile
from datetime import datetime, timezone
from decimal import Decimal

from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.models.core import Quote
from financial_portfolio_automation.exceptions import DatabaseError


class TestDataStore:
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            yield f.name
    
    @pytest.fixture
    def data_store(self, temp_db):
        """Create DataStore instance with temporary database."""
        return DataStore(temp_db)
    
    def test_save_and_retrieve_quote(self, data_store):
        """Test saving and retrieving a quote."""
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            bid=Decimal("150.00"),
            ask=Decimal("150.05"),
            bid_size=100,
            ask_size=200
        )
        
        # Save quote
        data_store.save_quote(quote)
        
        # Retrieve quote
        quotes = data_store.get_quotes("AAPL", limit=1)
        assert len(quotes) == 1
        assert quotes[0].symbol == "AAPL"
        assert quotes[0].bid == Decimal("150.00")
    
    def test_database_error_handling(self, data_store):
        """Test database error handling."""
        # Test with invalid data that should raise DatabaseError
        with pytest.raises(DatabaseError):
            # Attempt operation that should fail
            pass
```

## Integration Points

### With Existing Components

1. **API Integration Layer**:
   - `AlpacaClient.get_account_info()` → `DataStore.save_portfolio_snapshot()`
   - `WebSocketHandler` quote callbacks → `DataStore.save_quote()`
   - `MarketDataClient` → `DataCache` for frequently accessed data

2. **Configuration System**:
   - Database connection settings
   - Cache configuration (TTL values, cleanup intervals)
   - Validation rule parameters

3. **Exception Handling**:
   - Use existing `DatabaseError`, `DataError`, `ValidationError`
   - Proper error propagation and logging

### Future Components

The data layer will be used by:
- Analysis Engine (Task 5): Historical data for technical analysis
- Strategy Engine (Task 6): Backtesting data and performance metrics
- Execution Layer (Task 7): Order history and position tracking

## Performance Considerations

1. **Database Optimization**:
   - Proper indexing strategy
   - Connection pooling for high-frequency operations
   - Batch operations for bulk data insertion
   - Regular VACUUM operations for SQLite maintenance

2. **Cache Optimization**:
   - Memory usage monitoring
   - LRU eviction for memory pressure
   - Cache hit rate optimization
   - Async cache warming

3. **Validation Optimization**:
   - Rule prioritization (fail fast on critical errors)
   - Batch validation for bulk operations
   - Configurable validation levels

## Security Considerations

1. **Data Protection**:
   - Database file permissions
   - Sensitive data encryption at rest
   - SQL injection prevention (parameterized queries)

2. **Access Control**:
   - Read-only vs read-write access patterns
   - Audit logging for data modifications
   - Data retention policies

## Deployment Notes

1. **Database Setup**:
   - Automatic schema initialization
   - Migration path for schema updates
   - Backup and recovery procedures

2. **Configuration**:
   - Environment-specific database paths
   - Cache size limits based on available memory
   - Validation rule customization per environment

## Success Criteria

Task 4 will be considered complete when:

1. ✅ All database operations work correctly with proper error handling
2. ✅ Cache system provides significant performance improvement for repeated data access
3. ✅ Data validation catches common data quality issues
4. ✅ All unit tests pass with >90% code coverage
5. ✅ Integration tests demonstrate proper interaction with existing components
6. ✅ Performance benchmarks meet requirements (sub-second response times)
7. ✅ Documentation is complete and accurate

## Next Steps After Task 4

Once Task 4 is complete, the system will be ready for:
- **Task 5**: Analysis Engine implementation (will use stored historical data)
- **Task 6**: Strategy Engine development (will use cached market data)
- **Task 7**: Execution Layer (will store order and trade history)

The data management layer is foundational to all subsequent development, so thorough testing and robust implementation are critical for the overall system success.