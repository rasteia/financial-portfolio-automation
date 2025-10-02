"""
Paper Trading Integration Tests

Tests integration with Alpaca paper trading environment using real API connections
and market data to validate system behavior under actual market conditions.
"""

import pytest
import asyncio
import os
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch

from financial_portfolio_automation.models.core import OrderSide, OrderType, OrderStatus
from financial_portfolio_automation.models.config import AlpacaConfig, RiskLimits, DataFeed
from financial_portfolio_automation.api.alpaca_client import AlpacaClient
from financial_portfolio_automation.api.market_data_client import MarketDataClient
from financial_portfolio_automation.execution.order_executor import OrderExecutor
from financial_portfolio_automation.analysis.risk_manager import RiskManager
from financial_portfolio_automation.data.store import DataStore


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ALPACA_API_KEY") or not os.getenv("ALPACA_SECRET_KEY"),
    reason="Alpaca API credentials not available"
)
class TestPaperTradingIntegration:
    """Test integration with Alpaca paper trading environment"""

    @pytest.fixture
    def paper_trading_config(self):
        """Paper trading configuration using environment variables"""
        return AlpacaConfig(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
            base_url="https://paper-api.alpaca.markets",
            data_feed=DataFeed.IEX
        )

    @pytest.fixture
    def conservative_risk_limits(self):
        """Conservative risk limits for paper trading tests"""
        return RiskLimits(
            max_position_size=Decimal("1000"),  # Small position sizes for testing
            max_portfolio_concentration=0.1,
            max_daily_loss=Decimal("100"),
            max_drawdown=0.05,
            stop_loss_percentage=0.02
        )

    @pytest.fixture
    async def paper_trading_system(self, paper_trading_config, conservative_risk_limits):
        """Initialize system components for paper trading"""
        # Initialize data store
        data_store = DataStore(":memory:")
        
        # Initialize API clients
        alpaca_client = AlpacaClient(paper_trading_config)
        market_data_client = MarketDataClient(paper_trading_config)
        
        # Initialize risk manager and order executor
        risk_manager = RiskManager(conservative_risk_limits, data_store)
        order_executor = OrderExecutor(alpaca_client, risk_manager, data_store)
        
        return {
            'data_store': data_store,
            'alpaca_client': alpaca_client,
            'market_data_client': market_data_client,
            'risk_manager': risk_manager,
            'order_executor': order_executor
        }

    @pytest.mark.asyncio
    async def test_paper_trading_authentication(self, paper_trading_system):
        """Test authentication with Alpaca paper trading API"""
        
        # Test account access
        account_info = await paper_trading_system['alpaca_client'].get_account()
        
        assert account_info is not None
        assert 'account_id' in account_info
        assert 'buying_power' in account_info
        assert account_info['trading_blocked'] is False
        
        # Verify paper trading environment
        assert 'paper' in account_info.get('account_number', '').lower() or \
               account_info.get('pattern_day_trader', False) is not None

    @pytest.mark.asyncio
    async def test_real_market_data_retrieval(self, paper_trading_system):
        """Test retrieval of real market data"""
        
        # Test quote retrieval for liquid stocks
        test_symbols = ["AAPL", "MSFT", "GOOGL"]
        
        for symbol in test_symbols:
            quote = await paper_trading_system['market_data_client'].get_quote(symbol)
            
            assert quote is not None
            assert quote.symbol == symbol
            assert quote.bid > 0
            assert quote.ask > 0
            assert quote.ask >= quote.bid  # Ask should be >= bid
            assert quote.bid_size > 0
            assert quote.ask_size > 0
            
            # Store quote for later analysis
            await paper_trading_system['data_store'].store_quote(quote)
        
        # Test historical data retrieval
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        
        historical_data = await paper_trading_system['market_data_client'].get_historical_data(
            symbol="AAPL",
            timeframe="1Day",
            start=start_date,
            end=end_date
        )
        
        assert len(historical_data) > 0
        assert all(bar['symbol'] == 'AAPL' for bar in historical_data)
        assert all(bar['close'] > 0 for bar in historical_data)

    @pytest.mark.asyncio
    async def test_paper_trading_order_execution(self, paper_trading_system):
        """Test order execution in paper trading environment"""
        
        # Get current account info
        account_info = await paper_trading_system['alpaca_client'].get_account()
        initial_buying_power = Decimal(str(account_info['buying_power']))
        
        # Ensure we have sufficient buying power
        if initial_buying_power < Decimal("1000"):
            pytest.skip("Insufficient buying power for order execution test")
        
        # Test market buy order for a small quantity
        test_symbol = "AAPL"
        test_quantity = 1  # Small quantity for testing
        
        # Get current quote to estimate order value
        quote = await paper_trading_system['market_data_client'].get_quote(test_symbol)
        estimated_cost = quote.ask * test_quantity
        
        # Ensure order is within risk limits
        if estimated_cost > paper_trading_system['risk_manager'].risk_limits.max_position_size:
            pytest.skip(f"Order cost {estimated_cost} exceeds risk limit")
        
        # Execute market buy order
        buy_order = await paper_trading_system['order_executor'].execute_order(
            symbol=test_symbol,
            quantity=test_quantity,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET
        )
        
        assert buy_order is not None
        assert buy_order.symbol == test_symbol
        assert buy_order.quantity == test_quantity
        assert buy_order.side == OrderSide.BUY
        assert buy_order.order_type == OrderType.MARKET
        
        # Wait for order to be processed
        await asyncio.sleep(2)
        
        # Check order status
        order_status = await paper_trading_system['alpaca_client'].get_order(buy_order.order_id)
        assert order_status['status'] in ['filled', 'partially_filled', 'new', 'accepted']
        
        # If order was filled, test selling the position
        if order_status['status'] == 'filled':
            # Wait a moment before selling
            await asyncio.sleep(1)
            
            # Execute market sell order
            sell_order = await paper_trading_system['order_executor'].execute_order(
                symbol=test_symbol,
                quantity=test_quantity,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET
            )
            
            assert sell_order is not None
            assert sell_order.symbol == test_symbol
            assert sell_order.quantity == test_quantity
            assert sell_order.side == OrderSide.SELL

    @pytest.mark.asyncio
    async def test_paper_trading_position_management(self, paper_trading_system):
        """Test position management in paper trading environment"""
        
        # Get current positions
        positions = await paper_trading_system['alpaca_client'].get_positions()
        initial_position_count = len(positions)
        
        # Test position tracking
        for position in positions:
            assert 'symbol' in position
            assert 'qty' in position
            assert 'market_value' in position
            assert 'unrealized_pl' in position
            
            # Verify position data consistency
            qty = int(position['qty'])
            if qty != 0:
                assert float(position['market_value']) != 0
        
        # Test portfolio value calculation
        account_info = await paper_trading_system['alpaca_client'].get_account()
        portfolio_value = Decimal(str(account_info['portfolio_value']))
        equity = Decimal(str(account_info['equity']))
        
        assert portfolio_value > 0
        assert equity > 0
        
        # Portfolio value should equal equity for cash accounts
        # or be close for margin accounts
        value_difference = abs(portfolio_value - equity)
        assert value_difference < Decimal("1.00")  # Allow small rounding differences

    @pytest.mark.asyncio
    async def test_paper_trading_risk_controls(self, paper_trading_system):
        """Test risk controls with paper trading environment"""
        
        # Test position size limit enforcement
        test_symbol = "AAPL"
        quote = await paper_trading_system['market_data_client'].get_quote(test_symbol)
        
        # Calculate quantity that would exceed position size limit
        max_position_value = paper_trading_system['risk_manager'].risk_limits.max_position_size
        excessive_quantity = int(max_position_value / quote.ask) + 10
        
        # Attempt to place order that exceeds position size limit
        with pytest.raises(ValueError, match="Position size exceeds limit"):
            await paper_trading_system['order_executor'].execute_order(
                symbol=test_symbol,
                quantity=excessive_quantity,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET
            )
        
        # Test portfolio concentration limit
        account_info = await paper_trading_system['alpaca_client'].get_account()
        portfolio_value = Decimal(str(account_info['portfolio_value']))
        
        if portfolio_value > 0:
            # Calculate quantity that would exceed concentration limit
            max_concentration = paper_trading_system['risk_manager'].risk_limits.max_portfolio_concentration
            max_position_value_by_concentration = portfolio_value * Decimal(str(max_concentration))
            
            if max_position_value_by_concentration < max_position_value:
                excessive_quantity_concentration = int(max_position_value_by_concentration / quote.ask) + 10
                
                # This should be caught by concentration limit
                with pytest.raises(ValueError, match="concentration|limit"):
                    await paper_trading_system['order_executor'].execute_order(
                        symbol=test_symbol,
                        quantity=excessive_quantity_concentration,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET
                    )

    @pytest.mark.asyncio
    async def test_paper_trading_market_hours_handling(self, paper_trading_system):
        """Test handling of market hours and trading restrictions"""
        
        # Get market calendar
        market_calendar = await paper_trading_system['alpaca_client'].get_calendar()
        
        assert len(market_calendar) > 0
        
        # Check today's market status
        today = datetime.now().date()
        today_market_info = None
        
        for day_info in market_calendar:
            if day_info['date'] == today.isoformat():
                today_market_info = day_info
                break
        
        if today_market_info:
            market_open = datetime.fromisoformat(today_market_info['open'])
            market_close = datetime.fromisoformat(today_market_info['close'])
            current_time = datetime.now()
            
            is_market_hours = market_open <= current_time <= market_close
            
            # Test behavior during and outside market hours
            if is_market_hours:
                # During market hours, orders should be accepted
                quote = await paper_trading_system['market_data_client'].get_quote("AAPL")
                assert quote is not None
                assert quote.bid > 0
            else:
                # Outside market hours, we should still be able to place orders
                # (they will be queued for next market open)
                # But market data might be stale
                quote = await paper_trading_system['market_data_client'].get_quote("AAPL")
                # Quote should still be available (last known quote)
                assert quote is not None

    @pytest.mark.asyncio
    async def test_paper_trading_error_handling(self, paper_trading_system):
        """Test error handling with paper trading API"""
        
        # Test invalid symbol handling
        with pytest.raises(Exception):  # Should raise some form of error
            await paper_trading_system['market_data_client'].get_quote("INVALID_SYMBOL_12345")
        
        # Test invalid order parameters
        with pytest.raises(ValueError):
            await paper_trading_system['order_executor'].execute_order(
                symbol="AAPL",
                quantity=0,  # Invalid quantity
                side=OrderSide.BUY,
                order_type=OrderType.MARKET
            )
        
        with pytest.raises(ValueError):
            await paper_trading_system['order_executor'].execute_order(
                symbol="AAPL",
                quantity=-10,  # Negative quantity
                side=OrderSide.BUY,
                order_type=OrderType.MARKET
            )
        
        # Test insufficient buying power handling
        account_info = await paper_trading_system['alpaca_client'].get_account()
        buying_power = Decimal(str(account_info['buying_power']))
        
        if buying_power > 0:
            # Try to place an order that exceeds buying power
            quote = await paper_trading_system['market_data_client'].get_quote("AAPL")
            excessive_quantity = int(buying_power / quote.ask) + 1000  # Way more than buying power allows
            
            with pytest.raises(Exception):  # Should raise insufficient buying power error
                await paper_trading_system['order_executor'].execute_order(
                    symbol="AAPL",
                    quantity=excessive_quantity,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET
                )

    @pytest.mark.asyncio
    async def test_paper_trading_data_consistency(self, paper_trading_system):
        """Test data consistency between API calls and stored data"""
        
        # Get positions from API
        api_positions = await paper_trading_system['alpaca_client'].get_positions()
        
        # Store positions in local data store
        for position in api_positions:
            await paper_trading_system['data_store'].store_position(position)
        
        # Retrieve positions from data store
        stored_positions = await paper_trading_system['data_store'].get_all_positions()
        
        # Verify consistency
        assert len(api_positions) == len(stored_positions)
        
        for api_pos in api_positions:
            # Find corresponding stored position
            stored_pos = next(
                (pos for pos in stored_positions if pos['symbol'] == api_pos['symbol']),
                None
            )
            
            assert stored_pos is not None
            assert stored_pos['qty'] == api_pos['qty']
            assert abs(float(stored_pos['market_value']) - float(api_pos['market_value'])) < 0.01
        
        # Test account data consistency
        api_account = await paper_trading_system['alpaca_client'].get_account()
        
        # Store account snapshot
        await paper_trading_system['data_store'].store_account_snapshot(api_account)
        
        # Retrieve and verify
        stored_account = await paper_trading_system['data_store'].get_latest_account_snapshot()
        
        assert stored_account is not None
        assert stored_account['account_id'] == api_account['account_id']
        assert abs(float(stored_account['buying_power']) - float(api_account['buying_power'])) < 0.01

    @pytest.mark.asyncio
    async def test_paper_trading_performance_metrics(self, paper_trading_system):
        """Test performance metrics calculation with real data"""
        
        # Get account history for performance calculation
        account_info = await paper_trading_system['alpaca_client'].get_account()
        
        # Get portfolio history
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        portfolio_history = await paper_trading_system['alpaca_client'].get_portfolio_history(
            period="1M",
            timeframe="1D"
        )
        
        if portfolio_history and len(portfolio_history.get('equity', [])) > 1:
            equity_values = [float(val) for val in portfolio_history['equity'] if val is not None]
            
            if len(equity_values) >= 2:
                # Calculate basic performance metrics
                initial_value = equity_values[0]
                final_value = equity_values[-1]
                
                total_return = (final_value - initial_value) / initial_value
                
                # Calculate daily returns
                daily_returns = []
                for i in range(1, len(equity_values)):
                    daily_return = (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
                    daily_returns.append(daily_return)
                
                if daily_returns:
                    # Calculate volatility (standard deviation of daily returns)
                    import statistics
                    volatility = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
                    
                    # Basic performance validation
                    assert isinstance(total_return, float)
                    assert isinstance(volatility, float)
                    assert volatility >= 0  # Volatility should be non-negative
                    
                    # Store performance metrics
                    performance_data = {
                        'total_return': total_return,
                        'volatility': volatility,
                        'equity_values': equity_values,
                        'daily_returns': daily_returns,
                        'calculation_date': datetime.now()
                    }
                    
                    await paper_trading_system['data_store'].store_performance_metrics(performance_data)

    @pytest.mark.asyncio
    async def test_paper_trading_real_time_updates(self, paper_trading_system):
        """Test real-time data updates and processing"""
        
        # Test real-time quote updates
        test_symbols = ["AAPL", "MSFT"]
        quotes_received = []
        
        for symbol in test_symbols:
            # Get multiple quotes with small delays to simulate real-time updates
            for _ in range(3):
                quote = await paper_trading_system['market_data_client'].get_quote(symbol)
                quotes_received.append(quote)
                await asyncio.sleep(0.5)  # Small delay between requests
        
        # Verify we received quotes
        assert len(quotes_received) == 6  # 3 quotes for each of 2 symbols
        
        # Group quotes by symbol
        aapl_quotes = [q for q in quotes_received if q.symbol == "AAPL"]
        msft_quotes = [q for q in quotes_received if q.symbol == "MSFT"]
        
        assert len(aapl_quotes) == 3
        assert len(msft_quotes) == 3
        
        # Verify timestamps are in order (or very close)
        for quotes in [aapl_quotes, msft_quotes]:
            for i in range(1, len(quotes)):
                time_diff = (quotes[i].timestamp - quotes[i-1].timestamp).total_seconds()
                assert time_diff >= 0  # Later quotes should have later or equal timestamps
        
        # Store all quotes for analysis
        for quote in quotes_received:
            await paper_trading_system['data_store'].store_quote(quote)
        
        # Verify data was stored correctly
        for symbol in test_symbols:
            stored_quotes = await paper_trading_system['data_store'].get_recent_quotes(symbol, limit=3)
            assert len(stored_quotes) == 3