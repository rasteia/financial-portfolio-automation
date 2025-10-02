#!/usr/bin/env python3
"""
Demo portfolio builder - shows how to use the portfolio automation system.
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.models.core import Quote, Position, PortfolioSnapshot
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.analysis.portfolio_analyzer import PortfolioAnalyzer


def create_demo_data():
    """Create some demo portfolio data."""
    print("📊 Creating demo portfolio data...")
    
    # Initialize data store
    data_store = DataStore("portfolio_automation.db")
    
    # Create some sample quotes
    demo_quotes = [
        Quote(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=Decimal("150.25"),
            ask=Decimal("150.30"),
            bid_size=100,
            ask_size=200
        ),
        Quote(
            symbol="GOOGL",
            timestamp=datetime.now(),
            bid=Decimal("2750.50"),
            ask=Decimal("2751.00"),
            bid_size=50,
            ask_size=75
        ),
        Quote(
            symbol="MSFT",
            timestamp=datetime.now(),
            bid=Decimal("305.75"),
            ask=Decimal("305.85"),
            bid_size=150,
            ask_size=100
        ),
        Quote(
            symbol="TSLA",
            timestamp=datetime.now(),
            bid=Decimal("245.20"),
            ask=Decimal("245.40"),
            bid_size=200,
            ask_size=180
        )
    ]
    
    # Store quotes
    for quote in demo_quotes:
        data_store.save_quote(quote)
    
    # Create sample positions
    demo_positions = [
        Position(
            symbol="AAPL",
            quantity=Decimal("100"),
            cost_basis=Decimal("14550.00"),  # 100 * 145.50
            market_value=Decimal("15027.00"),
            unrealized_pnl=Decimal("477.00"),
            day_pnl=Decimal("50.00")
        ),
        Position(
            symbol="GOOGL",
            quantity=Decimal("10"),
            cost_basis=Decimal("27000.00"),  # 10 * 2700.00
            market_value=Decimal("27507.50"),
            unrealized_pnl=Decimal("507.50"),
            day_pnl=Decimal("75.50")
        ),
        Position(
            symbol="MSFT",
            quantity=Decimal("50"),
            cost_basis=Decimal("15000.00"),  # 50 * 300.00
            market_value=Decimal("15290.00"),
            unrealized_pnl=Decimal("290.00"),
            day_pnl=Decimal("0.00")
        )
    ]
    
    # Create portfolio snapshot first to get an ID
    total_value = sum(pos.market_value for pos in demo_positions)
    total_pnl = sum(pos.unrealized_pnl for pos in demo_positions)
    
    portfolio_snapshot = PortfolioSnapshot(
        timestamp=datetime.now(),
        total_value=total_value,
        buying_power=Decimal("25000.00"),
        day_pnl=Decimal("125.50"),
        total_pnl=total_pnl,
        positions=demo_positions
    )
    
    # Save portfolio snapshot and get ID
    snapshot_id = data_store.save_portfolio_snapshot(portfolio_snapshot)
    
    # Store positions with snapshot ID
    for position in demo_positions:
        data_store.save_position(position, snapshot_id)
    
    print(f"✅ Created demo portfolio with {len(demo_positions)} positions")
    print(f"💰 Total Portfolio Value: ${total_value:,.2f}")
    print(f"📈 Total P&L: ${total_pnl:,.2f}")
    
    return demo_positions, portfolio_snapshot


def analyze_portfolio(positions, snapshot):
    """Analyze the demo portfolio."""
    print("\n📊 Portfolio Analysis")
    print("=" * 50)
    
    # Display positions
    print("Current Positions:")
    for pos in positions:
        pnl_pct = (pos.unrealized_pnl / pos.cost_basis) * 100
        print(f"  {pos.symbol}: {pos.quantity} shares @ ${pos.current_price} "
              f"(P&L: ${pos.unrealized_pnl:,.2f} / {pnl_pct:.1f}%)")
    
    # Portfolio metrics
    print(f"\nPortfolio Summary:")
    print(f"  Total Value: ${snapshot.total_value:,.2f}")
    print(f"  Buying Power: ${snapshot.buying_power:,.2f}")
    print(f"  Day P&L: ${snapshot.day_pnl:,.2f}")
    print(f"  Total P&L: ${snapshot.total_pnl:,.2f}")
    
    # Allocation breakdown
    print(f"\nAllocation Breakdown:")
    for pos in positions:
        allocation_pct = (pos.market_value / snapshot.total_value) * 100
        print(f"  {pos.symbol}: {allocation_pct:.1f}% (${pos.market_value:,.2f})")


def show_available_commands():
    """Show available CLI commands."""
    print("\n🚀 Available Commands")
    print("=" * 50)
    print("Portfolio Management:")
    print("  python -m financial_portfolio_automation.cli.main --config config/config.json portfolio status")
    print("  python -m financial_portfolio_automation.cli.main --config config/config.json portfolio positions")
    print("  python -m financial_portfolio_automation.cli.main --config config/config.json portfolio allocation")
    
    print("\nAnalysis:")
    print("  python -m financial_portfolio_automation.cli.main --config config/config.json analyze risk --symbol AAPL")
    print("  python -m financial_portfolio_automation.cli.main --config config/config.json analyze performance")
    
    print("\nStrategy & Backtesting:")
    print("  python -m financial_portfolio_automation.cli.main --config config/config.json strategy list")
    print("  python -m financial_portfolio_automation.cli.main --config config/config.json strategy backtest --strategy momentum")
    
    print("\nReporting:")
    print("  python -m financial_portfolio_automation.cli.main --config config/config.json report generate --type performance")
    print("  python -m financial_portfolio_automation.cli.main --config config/config.json report generate --type tax")


def main():
    """Main demo function."""
    print("🎯 Portfolio Automation System Demo")
    print("=" * 50)
    
    try:
        # Create demo data
        positions, snapshot = create_demo_data()
        
        # Analyze portfolio
        analyze_portfolio(positions, snapshot)
        
        # Show available commands
        show_available_commands()
        
        print("\n🎉 Demo completed successfully!")
        print("\nNext Steps:")
        print("1. Try the CLI commands shown above")
        print("2. Set up real Alpaca API credentials for live trading")
        print("3. Explore the MCP tools for AI assistant integration")
        print("4. Build your own investment strategies!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)