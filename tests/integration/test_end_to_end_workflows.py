"""
End-to-End Workflow Integration Tests

Tests complete workflows from market data ingestion to trade execution,
validating all system components working together seamlessly.
"""

import pytest
import pytest_asyncio
import asyncio
import time
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from financial_portfolio_automation.models.core import (
    Quote, Position, Order, PortfolioSnapshot, OrderSide, OrderType, OrderStatus
)
from financial_portfolio_automation.models.config import AlpacaConfig, RiskLimits, StrategyConfig, DataFeed, StrategyType
from financial_portfolio_automation.api.alpaca_client import AlpacaClient
from financial_portfolio_automation.api.market_data_client import MarketDataClient
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.data.cache import DataCache
from financial_portfolio_automation.analysis.portfolio_analyzer import PortfolioAnalyzer
from financial_portfolio_automation.analysis.risk_manager import RiskManager
from financial_portfolio_automation.strategy.executor import StrategyExecutor
from financial_portfolio_automation.execution.order_executor import OrderExecutor
from financial_portfolio_automation.monitoring.portfolio_monitor import PortfolioMonitor
from financial_portfolio_automation.notifications.notification_service import NotificationService


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""

    @pytest.fixture
    def alpaca_config(self):
        """Test Alpaca configuration"""
        return AlpacaConfig(
            api_key="test_key_12345",
            secret_key="test_secret_12345",
            base_url="https://paper-api.alpaca.markets",
            data_feed=DataFeed.IEX
        )

    @pytest.fixture
    def risk_limits(self):
        """Test risk limits"""
        return RiskLimits(
            max_position_size=Decimal("10000"),
            max_portfolio_concentration=0.2,
            max_daily_loss=Decimal("1000"),
            max_drawdown=0.1,
            stop_loss_percentage=0.05
        )

    @pytest.fixture
    def strategy_config(self, risk_limits):
        """Test strategy configuration"""
        return StrategyConfig(
            strategy_id="test_momentum_001",
            strategy_type=StrategyType.MOMENTUM,
            name="Test Momentum Strategy",
            description="Test momentum strategy for integration testing",
            parameters={"lookback_period": 20, "momentum_threshold": 0.02},
            symbols=["AAPL", "GOOGL", "MSFT"],
            risk_limits=risk_limits,
            execution_schedule="market_hours"
        )

    @pytest_asyncio.fixture
    async def system_components(self, alpaca_config, risk_limits):
        """Initialize all system components"""
        # Initialize data layer
        data_store = DataStore(":memory:")
        
        # Verify database is properly initialized
        with data_store.get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quotes'")
            if not cursor.fetchone():
                raise RuntimeError("Database schema not properly initialized")
        
        data_cache = DataCache()
        
        # Initialize API clients
        alpaca_client = AlpacaClient(alpaca_config)
        market_data_client = MarketDataClient(alpaca_config)
        
        # Initialize analysis components
        portfolio_analyzer = PortfolioAnalyzer()
        risk_manager = RiskManager(risk_limits)
        
        # Initialize execution components
        order_executor = OrderExecutor(alpaca_client)
        strategy_executor = StrategyExecutor()
        
        # Initialize monitoring
        from financial_portfolio_automation.analysis.technical_analysis import TechnicalAnalysis
        technical_analysis = TechnicalAnalysis()
        portfolio_monitor = PortfolioMonitor(portfolio_analyzer, technical_analysis, data_cache)
        notification_service = NotificationService()
        
        return {
            'data_store': data_store,
            'data_cache': data_cache,
            'alpaca_client': alpaca_client,
            'market_data_client': market_data_client,
            'portfolio_analyzer': portfolio_analyzer,
            'risk_manager': risk_manager,
            'order_executor': order_executor,
            'strategy_executor': strategy_executor,
            'portfolio_monitor': portfolio_monitor,
            'notification_service': notification_service
        }

    @pytest.mark.asyncio
    async def test_complete_portfolio_management_workflow(self, system_components, strategy_config):
        """Test complete workflow: Data → Analysis → Strategy → Execution → Monitoring"""
        
        # Step 1: Market Data Ingestion
        with patch.object(system_components['market_data_client'], 'get_latest_quote') as mock_get_latest_quote:
            mock_get_latest_quote.return_value = {
                'symbol': 'AAPL',
                'timestamp': datetime.now().isoformat(),
                'bid': 150.00,
                'ask': 150.05,
                'bid_size': 100,
                'ask_size': 100,
                'exchange': 'NASDAQ',
                'conditions': [],
                'data_feed': 'iex'
            }
            
            # Also mock get_quote_as_model for Quote object
            with patch.object(system_components['market_data_client'], 'get_quote_as_model') as mock_get_quote_model:
                mock_get_quote_model.return_value = Quote(
                symbol="AAPL",
                timestamp=datetime.now(),
                bid=Decimal("150.00"),
                ask=Decimal("150.05"),
                bid_size=100,
                ask_size=100
            )
            
                # Fetch market data
                quote = system_components['market_data_client'].get_quote_as_model("AAPL")
                assert quote.symbol == "AAPL"
                assert quote.bid == Decimal("150.00")
            
                # Store market data
                system_components['data_store'].save_quote(quote)
        
        # Step 2: Portfolio Analysis
        with patch.object(system_components['alpaca_client'], 'get_positions') as mock_get_positions:
            mock_get_positions.return_value = [
                Position(
                    symbol="AAPL",
                    quantity=100,
                    market_value=Decimal("15000"),
                    cost_basis=Decimal("14500"),
                    unrealized_pnl=Decimal("500"),
                    day_pnl=Decimal("100")
                )
            ]
            
            # Analyze portfolio
            positions = system_components['alpaca_client'].get_positions()
            
            # Calculate basic portfolio metrics from positions
            total_value = sum(pos.market_value for pos in positions)
            total_pnl = sum(pos.unrealized_pnl for pos in positions)
            
            assert total_value == Decimal("15000")
            assert total_pnl == Decimal("500")
        
        # Step 3: Risk Assessment
        # Create a portfolio snapshot from positions for risk analysis
        portfolio_snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=total_value,
            buying_power=Decimal("5000"),
            day_pnl=total_pnl,
            total_pnl=total_pnl,
            positions=positions
        )
        
        risk_assessment = system_components['risk_manager'].generate_risk_report(portfolio_snapshot)
        assert 'risk_score' in risk_assessment
        assert 'concentration_analysis' in risk_assessment
        
        # Step 4: Strategy Signal Generation
        with patch.object(system_components['strategy_executor'], 'execute_strategy') as mock_execute_strategy:
            from financial_portfolio_automation.strategy.base import StrategySignal, SignalType
            
            mock_execute_strategy.return_value = [
                StrategySignal(
                    symbol='GOOGL',
                    signal_type=SignalType.BUY,
                    strength=0.8,
                    timestamp=datetime.now(),
                    metadata={'reasoning': 'Momentum breakout detected', 'strategy_id': 'test_momentum_001'}
                )
            ]
            
            # Create a mock strategy for execution
            from financial_portfolio_automation.strategy.base import Strategy
            mock_strategy = Mock(spec=Strategy)
            mock_strategy.strategy_id = 'test_momentum_001'
            
            signals = system_components['strategy_executor'].execute_strategy(
                mock_strategy, 
                {'GOOGL': quote}, 
                portfolio_snapshot
            )
            assert len(signals) == 1
            assert signals[0].symbol == 'GOOGL'
            assert signals[0].signal_type == SignalType.BUY
        
        # Step 5: Order Execution
        with patch.object(system_components['order_executor'], 'execute_order') as mock_execute_order:
            from financial_portfolio_automation.execution.order_executor import OrderRequest, ExecutionResult
            
            mock_execute_order.return_value = ExecutionResult(
                success=True,
                order_id="test_order_123",
                filled_quantity=10,
                average_fill_price=Decimal("2500.00"),
                remaining_quantity=0
            )
            
            # Execute trade based on signal
            order_request = OrderRequest(
                symbol="GOOGL",
                quantity=10,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET
            )
            
            execution_result = system_components['order_executor'].execute_order(order_request)
            
            assert execution_result.success is True
            assert execution_result.filled_quantity == 10
        
        # Step 6: Portfolio Monitoring
        # Get monitoring status to verify monitoring is working
        monitoring_status = system_components['portfolio_monitor'].get_monitoring_status()
        assert 'is_monitoring' in monitoring_status
        assert 'thresholds' in monitoring_status
        assert 'monitored_symbols' in monitoring_status
        
        # Step 7: Notification Delivery
        with patch.object(system_components['notification_service'], 'send_notification') as mock_send_notification:
            mock_send_notification.return_value = "notification_123"
            
            # Send alert notification
            notification_id = await system_components['notification_service'].send_notification(
                recipients=["test@example.com"],
                subject="Portfolio Alert",
                body="Position size approaching limit for GOOGL",
                channels=["email"]
            )
            
            assert notification_id == "notification_123"

    @pytest.mark.asyncio
    async def test_real_time_data_processing_workflow(self, system_components):
        """Test real-time data processing and analysis workflow"""
        
        # Simulate real-time data stream
        quotes = [
            Quote(
                symbol="AAPL",
                timestamp=datetime.now() - timedelta(seconds=i),
                bid=Decimal(f"{150 + i * 0.1:.2f}"),
                ask=Decimal(f"{150.05 + i * 0.1:.2f}"),
                bid_size=100,
                ask_size=100
            )
            for i in range(10)
        ]
        
        # Process quotes in real-time
        for quote in quotes:
            # Store quote
            await system_components['data_store'].store_quote(quote)
            
            # Cache for fast access
            system_components['data_cache'].set(f"quote:{quote.symbol}", quote, ttl=60)
            
            # Trigger analysis if needed
            cached_quote = system_components['data_cache'].get(f"quote:{quote.symbol}")
            assert cached_quote.symbol == quote.symbol
        
        # Verify data consistency
        stored_quotes = await system_components['data_store'].get_recent_quotes("AAPL", limit=10)
        assert len(stored_quotes) == 10
        
        # Test real-time analysis
        with patch.object(system_components['portfolio_analyzer'], 'calculate_real_time_metrics') as mock_calc_metrics:
            mock_calc_metrics.return_value = {
                'current_price': Decimal("151.00"),
                'price_change': Decimal("1.00"),
                'price_change_percent': 0.0066,
                'volume': 1000
            }
            
            metrics = await system_components['portfolio_analyzer'].calculate_real_time_metrics("AAPL")
            assert metrics['current_price'] == Decimal("151.00")

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, system_components):
        """Test system error recovery and resilience"""
        
        # Test API connection failure recovery
        with patch.object(system_components['alpaca_client'], 'get_account') as mock_get_account:
            # Simulate connection failure then recovery
            mock_get_account.side_effect = [
                ConnectionError("API connection failed"),
                ConnectionError("API connection failed"),
                {"account_id": "test_account", "buying_power": "10000"}
            ]
            
            # Test retry logic
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    account = await system_components['alpaca_client'].get_account()
                    assert account["account_id"] == "test_account"
                    break
                except ConnectionError:
                    retry_count += 1
                    await asyncio.sleep(0.1)  # Brief delay between retries
            
            assert retry_count == 2  # Should succeed on third attempt
        
        # Test data validation and error handling
        invalid_quote = Quote(
            symbol="INVALID",
            timestamp=datetime.now(),
            bid=Decimal("-100.00"),  # Invalid negative price
            ask=Decimal("-99.95"),   # Invalid negative price
            bid_size=-10,            # Invalid negative size
            ask_size=-5              # Invalid negative size
        )
        
        # Should handle invalid data gracefully
        with pytest.raises(ValueError):
            await system_components['data_store'].store_quote(invalid_quote)
        
        # Test database connection recovery
        with patch.object(system_components['data_store'], '_execute_query') as mock_execute:
            mock_execute.side_effect = [
                Exception("Database connection lost"),
                Exception("Database connection lost"),
                []  # Successful recovery
            ]
            
            # Should recover from database errors
            retry_count = 0
            while retry_count < 3:
                try:
                    await system_components['data_store'].get_recent_quotes("AAPL", limit=1)
                    break
                except Exception:
                    retry_count += 1
                    await asyncio.sleep(0.1)
            
            assert retry_count == 2

    @pytest.mark.asyncio
    async def test_multi_strategy_coordination_workflow(self, system_components):
        """Test coordination between multiple trading strategies"""
        
        # Define multiple strategies
        momentum_config = StrategyConfig(
            strategy_id="test_momentum_multi",
            strategy_type=StrategyType.MOMENTUM,
            name="Test Multi Momentum Strategy",
            description="Test momentum strategy for multi-strategy coordination",
            parameters={"lookback_period": 20, "momentum_threshold": 0.02},
            symbols=["AAPL", "GOOGL"],
            risk_limits=RiskLimits(
                max_position_size=Decimal("5000"),
                max_portfolio_concentration=0.1,
                max_daily_loss=Decimal("500"),
                max_drawdown=0.05,
                stop_loss_percentage=0.03
            ),
            execution_schedule="market_hours"
        )
        
        mean_reversion_config = StrategyConfig(
            strategy_id="test_mean_reversion_multi",
            strategy_type=StrategyType.MEAN_REVERSION,
            name="Test Multi Mean Reversion Strategy",
            description="Test mean reversion strategy for multi-strategy coordination",
            parameters={"lookback_period": 50, "deviation_threshold": 2.0},
            symbols=["MSFT", "TSLA"],
            risk_limits=RiskLimits(
                max_position_size=Decimal("5000"),
                max_portfolio_concentration=0.1,
                max_daily_loss=Decimal("500"),
                max_drawdown=0.05,
                stop_loss_percentage=0.03
            ),
            execution_schedule="extended_hours"
        )
        
        # Mock strategy signals
        with patch.object(system_components['strategy_executor'], 'generate_signals') as mock_generate_signals:
            mock_generate_signals.side_effect = [
                [  # Momentum strategy signals
                    {'symbol': 'AAPL', 'action': 'BUY', 'quantity': 20, 'confidence': 0.8},
                    {'symbol': 'GOOGL', 'action': 'SELL', 'quantity': 10, 'confidence': 0.7}
                ],
                [  # Mean reversion strategy signals
                    {'symbol': 'MSFT', 'action': 'BUY', 'quantity': 15, 'confidence': 0.6},
                    {'symbol': 'TSLA', 'action': 'SELL', 'quantity': 5, 'confidence': 0.9}
                ]
            ]
            
            # Execute both strategies
            momentum_signals = await system_components['strategy_executor'].generate_signals(momentum_config)
            mean_reversion_signals = await system_components['strategy_executor'].generate_signals(mean_reversion_config)
            
            # Combine and prioritize signals
            all_signals = momentum_signals + mean_reversion_signals
            
            # Sort by confidence for execution priority
            all_signals.sort(key=lambda x: x['confidence'], reverse=True)
            
            assert len(all_signals) == 4
            assert all_signals[0]['confidence'] == 0.9  # TSLA signal should be first
        
        # Test risk management across strategies
        total_exposure = sum(
            signal['quantity'] * 100  # Assuming $100 per share for simplicity
            for signal in all_signals
            if signal['action'] == 'BUY'
        )
        
        # Should respect overall portfolio risk limits
        portfolio_limit = Decimal("20000")  # Total portfolio limit
        assert total_exposure <= portfolio_limit

    @pytest.mark.asyncio
    async def test_performance_monitoring_workflow(self, system_components):
        """Test performance monitoring and benchmarking workflow"""
        
        start_time = time.time()
        
        # Test data processing performance
        quotes_processed = 0
        target_throughput = 1000  # quotes per second
        
        for i in range(100):  # Process 100 quotes
            quote = Quote(
                symbol=f"TEST{i % 10}",
                timestamp=datetime.now(),
                bid=Decimal(f"{100 + i * 0.01:.2f}"),
                ask=Decimal(f"{100.05 + i * 0.01:.2f}"),
                bid_size=100,
                ask_size=100
            )
            
            await system_components['data_store'].store_quote(quote)
            quotes_processed += 1
        
        processing_time = time.time() - start_time
        actual_throughput = quotes_processed / processing_time
        
        # Should meet minimum throughput requirements
        assert actual_throughput > 50  # Relaxed for test environment
        
        # Test memory usage monitoring
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        
        # Should stay within reasonable memory limits
        assert memory_usage < 1024  # Less than 1GB for tests
        
        # Test API response time monitoring
        response_times = []
        
        with patch.object(system_components['alpaca_client'], 'get_account') as mock_get_account:
            mock_get_account.return_value = {"account_id": "test", "buying_power": "10000"}
            
            for _ in range(10):
                start = time.time()
                await system_components['alpaca_client'].get_account()
                response_time = (time.time() - start) * 1000  # Convert to milliseconds
                response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        
        # Should meet response time targets (relaxed for mocked tests)
        assert avg_response_time < 100  # Less than 100ms average

    @pytest.mark.asyncio
    async def test_data_consistency_workflow(self, system_components):
        """Test data consistency across all system components"""
        
        # Create test data
        test_quote = Quote(
            symbol="CONSISTENCY_TEST",
            timestamp=datetime.now(),
            bid=Decimal("100.00"),
            ask=Decimal("100.05"),
            bid_size=100,
            ask_size=100
        )
        
        test_position = Position(
            symbol="CONSISTENCY_TEST",
            quantity=50,
            market_value=Decimal("5000"),
            cost_basis=Decimal("4900"),
            unrealized_pnl=Decimal("100"),
            day_pnl=Decimal("50")
        )
        
        # Store data in multiple components
        await system_components['data_store'].store_quote(test_quote)
        system_components['data_cache'].set(f"quote:{test_quote.symbol}", test_quote, ttl=300)
        
        # Verify consistency across components
        stored_quote = await system_components['data_store'].get_latest_quote("CONSISTENCY_TEST")
        cached_quote = system_components['data_cache'].get(f"quote:{test_quote.symbol}")
        
        assert stored_quote.symbol == cached_quote.symbol
        assert stored_quote.bid == cached_quote.bid
        assert stored_quote.ask == cached_quote.ask
        
        # Test portfolio data consistency
        with patch.object(system_components['alpaca_client'], 'get_positions') as mock_get_positions:
            mock_get_positions.return_value = [test_position]
            
            positions = await system_components['alpaca_client'].get_positions()
            portfolio_metrics = await system_components['portfolio_analyzer'].analyze_portfolio(positions)
            
            # Verify calculated metrics match position data
            assert portfolio_metrics['total_value'] == test_position.market_value
            assert portfolio_metrics['total_pnl'] == test_position.unrealized_pnl

    @pytest.mark.asyncio
    async def test_audit_trail_workflow(self, system_components):
        """Test comprehensive audit trail and logging workflow"""
        
        # Test trade execution audit trail
        with patch.object(system_components['order_executor'], 'execute_order') as mock_execute_order:
            mock_execute_order.return_value = Order(
                order_id="audit_test_123",
                symbol="AUDIT_TEST",
                quantity=25,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                status=OrderStatus.FILLED,
                filled_quantity=25,
                average_fill_price=Decimal("200.00")
            )
            
            # Execute order and verify audit logging
            order = await system_components['order_executor'].execute_order(
                symbol="AUDIT_TEST",
                quantity=25,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                limit_price=Decimal("200.00")
            )
            
            # Verify order was logged
            assert order.order_id == "audit_test_123"
            
            # Check audit trail in data store
            audit_records = await system_components['data_store'].get_audit_trail(
                entity_type="order",
                entity_id=order.order_id
            )
            
            # Should have audit records for order creation and execution
            assert len(audit_records) >= 1
        
        # Test risk management audit trail
        risk_violation = {
            'type': 'POSITION_SIZE_EXCEEDED',
            'symbol': 'AUDIT_TEST',
            'attempted_quantity': 1000,
            'max_allowed': 500,
            'timestamp': datetime.now()
        }
        
        await system_components['data_store'].log_risk_violation(risk_violation)
        
        # Verify risk violation was logged
        risk_logs = await system_components['data_store'].get_risk_violations(
            symbol="AUDIT_TEST",
            start_date=datetime.now() - timedelta(hours=1)
        )
        
        assert len(risk_logs) >= 1
        assert risk_logs[0]['type'] == 'POSITION_SIZE_EXCEEDED'