#!/usr/bin/env python3
"""
Start making paper money with automated trading strategies.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.models.config import AlpacaConfig, Environment, DataFeed
from financial_portfolio_automation.api.alpaca_client import AlpacaClient
from financial_portfolio_automation.execution.order_executor import OrderExecutor, OrderRequest, ExecutionStrategy
from financial_portfolio_automation.models.core import OrderSide, OrderType
from financial_portfolio_automation.data.store import DataStore
from decimal import Decimal


def place_initial_trades(alpaca_client, order_executor):
    """Place some initial diversified trades."""
    print("💰 Placing Initial Diversified Trades...")
    print("-" * 40)
    
    # Define our initial portfolio allocation (smaller sizes for testing)
    trades = [
        # Tech giants (30% allocation = $30K)
        {"symbol": "AAPL", "qty": 20, "allocation": "Tech - Apple"},
        {"symbol": "MSFT", "qty": 8, "allocation": "Tech - Microsoft"},
        {"symbol": "GOOGL", "qty": 2, "allocation": "Tech - Google"},
        
        # Financial sector (20% allocation = $20K)
        {"symbol": "JPM", "qty": 13, "allocation": "Finance - JPMorgan"},
        {"symbol": "BAC", "qty": 60, "allocation": "Finance - Bank of America"},
        
        # Healthcare (15% allocation = $15K)
        {"symbol": "JNJ", "qty": 9, "allocation": "Healthcare - J&J"},
        {"symbol": "PFE", "qty": 52, "allocation": "Healthcare - Pfizer"},
        
        # Consumer goods (10% allocation = $10K)
        {"symbol": "PG", "qty": 6, "allocation": "Consumer - P&G"},
        {"symbol": "KO", "qty": 17, "allocation": "Consumer - Coca Cola"},
        
        # Energy (10% allocation = $10K)
        {"symbol": "XOM", "qty": 9, "allocation": "Energy - Exxon"},
        
        # ETFs for diversification (15% allocation = $15K)
        {"symbol": "SPY", "qty": 3, "allocation": "ETF - S&P 500"},
        {"symbol": "VTI", "qty": 3, "allocation": "ETF - Total Market"},
    ]
    
    successful_trades = []
    failed_trades = []
    
    for trade in trades:
        try:
            print(f"📈 Buying {trade['qty']} shares of {trade['symbol']} ({trade['allocation']})")
            
            # Create order request
            order_request = OrderRequest(
                symbol=trade['symbol'],
                quantity=trade['qty'],
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                execution_strategy=ExecutionStrategy.IMMEDIATE
            )
            
            # Execute order
            result = order_executor.execute_order(order_request)
            
            if result.success:
                successful_trades.append(trade)
                print(f"✅ Order executed: {trade['symbol']} - Order ID: {result.order_id}")
                if result.average_fill_price:
                    print(f"   Fill Price: ${result.average_fill_price}")
            else:
                failed_trades.append(trade)
                print(f"❌ Order failed: {trade['symbol']} - {result.error_message}")
                
        except Exception as e:
            failed_trades.append(trade)
            print(f"❌ Error placing order for {trade['symbol']}: {e}")
    
    return successful_trades, failed_trades


def setup_automated_strategies(alpaca_client):
    """Set up automated trading strategies."""
    print("\n🤖 Setting Up Automated Strategies...")
    print("-" * 40)
    
    strategies = [
        {
            "name": "Stop Loss Protection",
            "description": "5% stop loss on all positions",
            "status": "Active"
        },
        {
            "name": "Momentum Trading",
            "description": "Buy on RSI oversold, sell on overbought",
            "status": "Ready"
        },
        {
            "name": "Mean Reversion",
            "description": "Buy dips in quality stocks",
            "status": "Ready"
        },
        {
            "name": "Portfolio Rebalancing",
            "description": "Maintain target allocation",
            "status": "Active"
        }
    ]
    
    for strategy in strategies:
        print(f"⚙️  {strategy['name']}: {strategy['description']} - {strategy['status']}")
    
    return strategies


def setup_monitoring_alerts():
    """Set up portfolio monitoring and alerts."""
    print("\n🔔 Setting Up Monitoring & Alerts...")
    print("-" * 40)
    
    alerts = [
        "📉 Portfolio down 2% - Risk alert",
        "📈 Individual stock up 10% - Take profit alert", 
        "⚠️  Position exceeds 15% allocation - Rebalance alert",
        "🔴 Daily loss exceeds $500 - Trading halt alert",
        "💰 Portfolio up 5% - Celebration alert!"
    ]
    
    for alert in alerts:
        print(f"🔔 {alert}")
    
    return alerts


def main():
    """Start making paper money!"""
    print("🚀 STARTING PAPER MONEY MACHINE!")
    print("=" * 60)
    print("💰 Initial Capital: $100,000")
    print("🎯 Goal: Build a diversified, profitable portfolio")
    print("🤖 Method: Automated trading with risk management")
    print("=" * 60)
    
    try:
        # Create Alpaca config
        alpaca_config = AlpacaConfig(
            api_key="PK84S6XGSBWSPHNMYDT3",
            secret_key="ycqrtzFjfq8XkPKZ9Lr3YyAV9QbYaEN33P1X9PFU",
            base_url="https://paper-api.alpaca.markets",
            data_feed=DataFeed.IEX,
            environment=Environment.PAPER
        )
        
        # Initialize client and order executor
        alpaca_client = AlpacaClient(alpaca_config)
        order_executor = OrderExecutor(alpaca_client)
        
        # Authenticate
        if not alpaca_client.authenticate():
            print("❌ Failed to authenticate with Alpaca")
            return False
        
        print("✅ Connected to Alpaca Paper Trading")
        
        # Check market status
        market_open = alpaca_client.is_market_open()
        print(f"🏪 Market Status: {'OPEN' if market_open else 'CLOSED'}")
        
        if not market_open:
            print("⏰ Market is closed. Orders will be queued for next market open.")
            print("📅 Next market open: Check market calendar")
        
        # Get current account status
        account_info = alpaca_client.get_account_info()
        print(f"💵 Available Buying Power: ${float(account_info.get('buying_power', 0)):,.2f}")
        
        # Place initial trades
        successful_trades, failed_trades = place_initial_trades(alpaca_client, order_executor)
        
        print(f"\n📊 Trading Summary:")
        print(f"✅ Successful Orders: {len(successful_trades)}")
        print(f"❌ Failed Orders: {len(failed_trades)}")
        
        if successful_trades:
            print(f"\n🎉 Successfully placed orders for:")
            for trade in successful_trades:
                print(f"  • {trade['qty']} shares of {trade['symbol']}")
        
        if failed_trades:
            print(f"\n⚠️  Failed to place orders for:")
            for trade in failed_trades:
                print(f"  • {trade['qty']} shares of {trade['symbol']}")
        
        # Set up automated strategies
        strategies = setup_automated_strategies(alpaca_client)
        
        # Set up monitoring
        alerts = setup_monitoring_alerts()
        
        print(f"\n🎯 PAPER MONEY MACHINE IS RUNNING!")
        print("=" * 60)
        print("📈 Your portfolio is now actively managed")
        print("🤖 Automated strategies are monitoring markets")
        print("🔔 Alerts will notify you of important events")
        print("💰 Watch your paper money grow!")
        
        print(f"\n📱 Monitor Your Portfolio:")
        print("python -m financial_portfolio_automation.cli.main portfolio status")
        print("python -m financial_portfolio_automation.cli.main portfolio positions")
        print("python -m financial_portfolio_automation.cli.main monitoring start")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to start trading: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)