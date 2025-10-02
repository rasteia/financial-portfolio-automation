#!/usr/bin/env python3
"""
Clean and recreate demo portfolio data.
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import os

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.models.core import Quote, Position, PortfolioSnapshot
from financial_portfolio_automation.data.store import DataStore


def main():
    """Clean and recreate demo data."""
    print("🧹 Cleaning and recreating demo portfolio data...")
    
    # Remove existing database
    db_path = "portfolio_automation.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✅ Removed existing database")
    
    # Initialize fresh data store
    data_store = DataStore(db_path)
    print("✅ Created fresh database")
    
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
    print(f"✅ Saved {len(demo_quotes)} quotes")
    
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
    
    # Create portfolio snapshot (this will save positions automatically)
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
    
    # Save portfolio snapshot (this saves positions too)
    snapshot_id = data_store.save_portfolio_snapshot(portfolio_snapshot)
    print(f"✅ Saved portfolio snapshot with ID: {snapshot_id}")
    
    # Verify data
    stats = data_store.get_database_stats()
    print(f"📊 Database stats: {stats}")
    
    latest = data_store.get_latest_portfolio_snapshot()
    if latest:
        print(f"💰 Portfolio Value: ${latest.total_value:,.2f}")
        print(f"📈 Total P&L: ${latest.total_pnl:,.2f}")
        print(f"📋 Positions: {len(latest.positions)}")
    
    print("🎉 Demo data recreated successfully!")


if __name__ == "__main__":
    main()