"""
Integration tests for the data management layer.
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone
from decimal import Decimal

from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.data.cache import DataCache
from financial_portfolio_automation.data.validator import DataValidator
from financial_portfolio_automation.models.core import Quote, Position, Order, PortfolioSnapshot, OrderSide, OrderType, OrderStatus


class TestDataIntegration:
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        os.unlink(path)
        yield path
        if os.path.exists(path):
            os.unlink(path)
    
    @pytest.fixture
    def data_store(self, temp_db):
        """Create DataStore instance."""
        return DataStore(temp_db)
    
    @pytest.fixture
    def data_cache(self):
        """Create DataCache instance."""
        return DataCache(default_ttl=300)
    
    @pytest.fixture
    def data_validator(self):
        """Create DataValidator instance."""
        return DataValidator()
    
    def test_complete_data_workflow(self, data_store, data_cache, data_validator):
        """Test complete workflow: validate -> cache -> store -> retrieve."""
        
        # 1. Create test data
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            bid=Decimal("150.00"),
            ask=Decimal("150.05"),
            bid_size=100,
            ask_size=200
        )
        
        position = Position(
            symbol="AAPL",
            quantity=100,
            market_value=Decimal("15000.00"),
            cost_basis=Decimal("14500.00"),
            unrealized_pnl=Decimal("500.00"),
            day_pnl=Decimal("50.00")
        )
        
        order = Order(
            order_id="order_123",
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            status=OrderStatus.NEW,
            filled_quantity=0,
            limit_price=Decimal("149.50"),
            time_in_force="day"
        )
        
        portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal("25000.00"),
            buying_power=Decimal("10000.00"),
            day_pnl=Decimal("250.00"),
            total_pnl=Decimal("1500.00"),
            positions=[position]
        )
        
        # 2. Validate all data
        quote_result = data_validator.validate_quote(quote)
        assert quote_result.is_valid
        
        position_result = data_validator.validate_position(position)
        assert position_result.is_valid
        
        order_result = data_validator.validate_order(order)
        assert order_result.is_valid
        
        portfolio_result = data_validator.validate_portfolio_snapshot(portfolio)
        assert portfolio_result.is_valid
        
        # 3. Store data in database
        data_store.save_quote(quote)
        data_store.save_position(position)
        data_store.save_order(order)
        portfolio_id = data_store.save_portfolio_snapshot(portfolio)
        
        # 4. Cache frequently accessed data
        data_cache.set(f"quote:{quote.symbol}", quote)
        data_cache.set(f"position:{position.symbol}", position)
        data_cache.set(f"order:{order.order_id}", order)
        data_cache.set(f"portfolio:latest", portfolio)
        
        # 5. Retrieve from cache (fast path)
        cached_quote = data_cache.get(f"quote:{quote.symbol}")
        assert cached_quote is not None
        assert cached_quote.symbol == quote.symbol
        assert cached_quote.bid == quote.bid
        
        cached_position = data_cache.get(f"position:{position.symbol}")
        assert cached_position is not None
        assert cached_position.symbol == position.symbol
        assert cached_position.quantity == position.quantity
        
        # 6. Retrieve from database (when not in cache)
        data_cache.clear()  # Clear cache to force database retrieval
        
        db_quotes = data_store.get_quotes("AAPL")
        assert len(db_quotes) == 1
        assert db_quotes[0].symbol == quote.symbol
        assert db_quotes[0].bid == quote.bid
        
        db_positions = data_store.get_positions()
        assert len(db_positions) == 1
        assert db_positions[0].symbol == position.symbol
        
        db_orders = data_store.get_orders()
        assert len(db_orders) == 1
        assert db_orders[0].order_id == order.order_id
        
        db_portfolio = data_store.get_portfolio_snapshot(portfolio_id)
        assert db_portfolio is not None
        assert db_portfolio.total_value == portfolio.total_value
        assert len(db_portfolio.positions) == 1
        
        # 7. Test cache warming from database
        def quote_loader(key):
            symbol = key.split(":")[1]
            quotes = data_store.get_quotes(symbol, limit=1)
            return quotes[0] if quotes else None
        
        data_cache.warm_cache(quote_loader, ["quote:AAPL"])
        warmed_quote = data_cache.get("quote:AAPL")
        assert warmed_quote is not None
        assert warmed_quote.symbol == "AAPL"
    
    def test_data_validation_integration(self, data_validator):
        """Test validation of related data consistency."""
        
        # Create quotes with different spreads
        normal_quote = Quote("AAPL", datetime.now(timezone.utc), Decimal("150.00"), Decimal("150.05"), 100, 200)
        wide_spread_quote = Quote("GOOGL", datetime.now(timezone.utc), Decimal("100.00"), Decimal("110.00"), 100, 200)
        
        quotes = [normal_quote, wide_spread_quote]
        
        # Validate data consistency
        result = data_validator.validate_data_consistency(quotes)
        assert result.is_valid  # Should be valid overall
        # Note: warnings depend on the specific validation rules implementation
        
        # Validate timestamp consistency
        timestamps = [quote.timestamp for quote in quotes]
        timestamp_result = data_validator.validate_timestamp_consistency(timestamps)
        assert timestamp_result.is_valid
    
    def test_cache_database_synchronization(self, data_store, data_cache):
        """Test keeping cache synchronized with database updates."""
        
        # Create and store initial quote
        quote = Quote("AAPL", datetime.now(timezone.utc), Decimal("150.00"), Decimal("150.05"), 100, 200)
        data_store.save_quote(quote)
        data_cache.set("quote:AAPL", quote)
        
        # Update quote in database
        updated_quote = Quote("AAPL", datetime.now(timezone.utc), Decimal("151.00"), Decimal("151.05"), 150, 250)
        data_store.save_quote(updated_quote)
        
        # Cache should be invalidated and updated
        data_cache.delete("quote:AAPL")  # Simulate cache invalidation
        
        # Retrieve from database and update cache
        fresh_quotes = data_store.get_quotes("AAPL", limit=1)
        if fresh_quotes:
            data_cache.set("quote:AAPL", fresh_quotes[0])
        
        # Verify cache has updated data
        cached_quote = data_cache.get("quote:AAPL")
        assert cached_quote.bid == Decimal("151.00")
        assert cached_quote.bid_size == 150
    
    def test_error_handling_integration(self, data_store, data_cache, data_validator):
        """Test error handling across all components."""
        
        # Test validation errors
        try:
            invalid_quote = Quote("", datetime.now(timezone.utc), Decimal("150.00"), Decimal("150.05"), 100, 200)
        except ValueError:
            pass  # Expected validation error
        
        # Test database errors with invalid data
        valid_quote = Quote("AAPL", datetime.now(timezone.utc), Decimal("150.00"), Decimal("150.05"), 100, 200)
        
        # This should work fine
        data_store.save_quote(valid_quote)
        
        # Test cache with various data types
        data_cache.set("string", "test")
        data_cache.set("number", 42)
        data_cache.set("object", valid_quote)
        
        assert data_cache.get("string") == "test"
        assert data_cache.get("number") == 42
        assert data_cache.get("object").symbol == "AAPL"
    
    def test_performance_integration(self, data_store, data_cache):
        """Test performance characteristics of integrated system."""
        
        # Create multiple quotes
        quotes = []
        for i in range(50):
            quote = Quote(
                f"STK{chr(65 + i % 26)}",  # STKA, STKB, etc.
                datetime.now(timezone.utc),
                Decimal(f"10{i}.00"),
                Decimal(f"10{i}.05"),
                100 + i,
                200 + i
            )
            quotes.append(quote)
        
        # Store all quotes in database
        for quote in quotes:
            data_store.save_quote(quote)
        
        # Cache some quotes
        for i in range(0, 50, 5):  # Cache every 5th quote
            data_cache.set(f"quote:{quotes[i].symbol}", quotes[i])
        
        # Test retrieval performance
        # Cache hits should be faster than database queries
        cached_quote = data_cache.get("quote:STKA")  # Should be cached
        assert cached_quote is not None
        
        db_quotes = data_store.get_quotes("STKB")  # Should come from database
        assert len(db_quotes) == 1
        
        # Test cache statistics
        stats = data_cache.get_stats()
        assert stats['hit_count'] > 0
        assert stats['total_entries'] > 0
    
    def test_data_lifecycle_management(self, data_store, data_cache, data_validator):
        """Test complete data lifecycle from creation to cleanup."""
        
        # 1. Create and validate data
        quote = Quote("AAPL", datetime.now(timezone.utc), Decimal("150.00"), Decimal("150.05"), 100, 200)
        validation_result = data_validator.validate_quote(quote)
        assert validation_result.is_valid
        
        # 2. Store in database
        data_store.save_quote(quote)
        
        # 3. Cache for fast access
        data_cache.set("quote:AAPL", quote, ttl=60)  # 1 minute TTL
        
        # 4. Verify data exists in both systems
        cached_data = data_cache.get("quote:AAPL")
        assert cached_data is not None
        
        db_data = data_store.get_quotes("AAPL")
        assert len(db_data) == 1
        
        # 5. Update data (use same timestamp to ensure replacement)
        updated_quote = Quote("AAPL", quote.timestamp, Decimal("151.00"), Decimal("151.05"), 120, 220)
        data_store.save_quote(updated_quote)  # Update in database
        data_cache.set("quote:AAPL", updated_quote)  # Update in cache
        
        # 6. Verify updates
        cached_updated = data_cache.get("quote:AAPL")
        assert cached_updated.bid == Decimal("151.00")
        
        db_updated = data_store.get_quotes("AAPL", limit=1)
        assert db_updated[0].bid == Decimal("151.00")
        
        # 7. Cleanup
        data_cache.delete("quote:AAPL")
        assert data_cache.get("quote:AAPL") is None
        
        # Database data should still exist (should be 1 quote due to replacement)
        db_final = data_store.get_quotes("AAPL")
        assert len(db_final) == 1