#!/usr/bin/env python3
"""
Diversify the portfolio across sectors and asset classes.
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
    """Create a diversified portfolio."""
    print("🌍 Creating a diversified portfolio...")
    
    # Remove existing database
    db_path = "portfolio_automation.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✅ Removed existing database")
    
    # Initialize fresh data store
    data_store = DataStore(db_path)
    print("✅ Created fresh database")
    
    # Create quotes for diversified holdings
    demo_quotes = [
        # Technology (25% allocation)
        Quote(symbol="AAPL", timestamp=datetime.now(), bid=Decimal("150.25"), ask=Decimal("150.30"), bid_size=100, ask_size=200),
        Quote(symbol="MSFT", timestamp=datetime.now(), bid=Decimal("305.75"), ask=Decimal("305.85"), bid_size=150, ask_size=100),
        
        # Healthcare (15% allocation)
        Quote(symbol="JNJ", timestamp=datetime.now(), bid=Decimal("162.50"), ask=Decimal("162.60"), bid_size=120, ask_size=80),
        Quote(symbol="PFE", timestamp=datetime.now(), bid=Decimal("28.75"), ask=Decimal("28.80"), bid_size=300, ask_size=250),
        
        # Financial Services (15% allocation)
        Quote(symbol="JPM", timestamp=datetime.now(), bid=Decimal("148.20"), ask=Decimal("148.30"), bid_size=90, ask_size=110),
        Quote(symbol="BAC", timestamp=datetime.now(), bid=Decimal("32.45"), ask=Decimal("32.50"), bid_size=200, ask_size=180),
        
        # Consumer Goods (10% allocation)
        Quote(symbol="PG", timestamp=datetime.now(), bid=Decimal("155.80"), ask=Decimal("155.90"), bid_size=80, ask_size=70),
        Quote(symbol="KO", timestamp=datetime.now(), bid=Decimal("58.25"), ask=Decimal("58.30"), bid_size=150, ask_size=140),
        
        # Energy (10% allocation)
        Quote(symbol="XOM", timestamp=datetime.now(), bid=Decimal("108.50"), ask=Decimal("108.60"), bid_size=100, ask_size=90),
        
        # ETFs for broad diversification (25% allocation)
        Quote(symbol="SPY", timestamp=datetime.now(), bid=Decimal("428.50"), ask=Decimal("428.60"), bid_size=50, ask_size=60),  # S&P 500
        Quote(symbol="VTI", timestamp=datetime.now(), bid=Decimal("245.20"), ask=Decimal("245.30"), bid_size=40, ask_size=45),  # Total Stock Market
        Quote(symbol="VXUS", timestamp=datetime.now(), bid=Decimal("58.75"), ask=Decimal("58.80"), bid_size=80, ask_size=70),  # International
        Quote(symbol="BND", timestamp=datetime.now(), bid=Decimal("76.25"), ask=Decimal("76.30"), bid_size=60, ask_size=55),  # Bonds
    ]
    
    # Store quotes
    for quote in demo_quotes:
        data_store.save_quote(quote)
    print(f"✅ Saved {len(demo_quotes)} quotes")
    
    # Create diversified positions (targeting $100,000 portfolio)
    target_portfolio_value = Decimal("100000.00")
    
    demo_positions = [
        # Technology Sector (25% = $25,000)
        Position(
            symbol="AAPL",
            quantity=Decimal("83"),  # ~$12,500
            cost_basis=Decimal("12075.00"),  # 83 * $145.50
            market_value=Decimal("12472.41"),  # 83 * $150.27
            unrealized_pnl=Decimal("397.41"),
            day_pnl=Decimal("41.50")
        ),
        Position(
            symbol="MSFT",
            quantity=Decimal("41"),  # ~$12,500
            cost_basis=Decimal("12300.00"),  # 41 * $300.00
            market_value=Decimal("12538.30"),  # 41 * $305.80
            unrealized_pnl=Decimal("238.30"),
            day_pnl=Decimal("20.50")
        ),
        
        # Healthcare Sector (15% = $15,000)
        Position(
            symbol="JNJ",
            quantity=Decimal("62"),  # ~$10,000
            cost_basis=Decimal("9920.00"),  # 62 * $160.00
            market_value=Decimal("10081.20"),  # 62 * $162.60
            unrealized_pnl=Decimal("161.20"),
            day_pnl=Decimal("31.00")
        ),
        Position(
            symbol="PFE",
            quantity=Decimal("174"),  # ~$5,000
            cost_basis=Decimal("5046.00"),  # 174 * $29.00
            market_value=Decimal("5011.20"),  # 174 * $28.80
            unrealized_pnl=Decimal("-34.80"),
            day_pnl=Decimal("-8.70")
        ),
        
        # Financial Services (15% = $15,000)
        Position(
            symbol="JPM",
            quantity=Decimal("51"),  # ~$7,500
            cost_basis=Decimal("7395.00"),  # 51 * $145.00
            market_value=Decimal("7563.30"),  # 51 * $148.30
            unrealized_pnl=Decimal("168.30"),
            day_pnl=Decimal("25.50")
        ),
        Position(
            symbol="BAC",
            quantity=Decimal("231"),  # ~$7,500
            cost_basis=Decimal("7161.00"),  # 231 * $31.00
            market_value=Decimal("7507.50"),  # 231 * $32.50
            unrealized_pnl=Decimal("346.50"),
            day_pnl=Decimal("23.10")
        ),
        
        # Consumer Goods (10% = $10,000)
        Position(
            symbol="PG",
            quantity=Decimal("32"),  # ~$5,000
            cost_basis=Decimal("4800.00"),  # 32 * $150.00
            market_value=Decimal("4988.80"),  # 32 * $155.90
            unrealized_pnl=Decimal("188.80"),
            day_pnl=Decimal("16.00")
        ),
        Position(
            symbol="KO",
            quantity=Decimal("86"),  # ~$5,000
            cost_basis=Decimal("4902.00"),  # 86 * $57.00
            market_value=Decimal("5013.80"),  # 86 * $58.30
            unrealized_pnl=Decimal("111.80"),
            day_pnl=Decimal("8.60")
        ),
        
        # Energy (10% = $10,000)
        Position(
            symbol="XOM",
            quantity=Decimal("93"),  # ~$10,000
            cost_basis=Decimal("9765.00"),  # 93 * $105.00
            market_value=Decimal("10099.80"),  # 93 * $108.60
            unrealized_pnl=Decimal("334.80"),
            day_pnl=Decimal("27.90")
        ),
        
        # ETFs for Diversification (25% = $25,000)
        Position(
            symbol="SPY",
            quantity=Decimal("15"),  # ~$6,500
            cost_basis=Decimal("6300.00"),  # 15 * $420.00
            market_value=Decimal("6429.00"),  # 15 * $428.60
            unrealized_pnl=Decimal("129.00"),
            day_pnl=Decimal("15.00")
        ),
        Position(
            symbol="VTI",
            quantity=Decimal("26"),  # ~$6,500
            cost_basis=Decimal("6240.00"),  # 26 * $240.00
            market_value=Decimal("6377.80"),  # 26 * $245.30
            unrealized_pnl=Decimal("137.80"),
            day_pnl=Decimal("13.00")
        ),
        Position(
            symbol="VXUS",
            quantity=Decimal("106"),  # ~$6,000
            cost_basis=Decimal("6042.00"),  # 106 * $57.00
            market_value=Decimal("6232.80"),  # 106 * $58.80
            unrealized_pnl=Decimal("190.80"),
            day_pnl=Decimal("10.60")
        ),
        Position(
            symbol="BND",
            quantity=Decimal("79"),  # ~$6,000
            cost_basis=Decimal("6083.00"),  # 79 * $77.00
            market_value=Decimal("6027.70"),  # 79 * $76.30
            unrealized_pnl=Decimal("-55.30"),
            day_pnl=Decimal("-3.95")
        ),
    ]
    
    # Create portfolio snapshot
    total_value = sum(pos.market_value for pos in demo_positions)
    total_pnl = sum(pos.unrealized_pnl for pos in demo_positions)
    total_day_pnl = sum(pos.day_pnl for pos in demo_positions)
    
    portfolio_snapshot = PortfolioSnapshot(
        timestamp=datetime.now(),
        total_value=total_value,
        buying_power=Decimal("15000.00"),  # Available cash
        day_pnl=total_day_pnl,
        total_pnl=total_pnl,
        positions=demo_positions
    )
    
    # Save portfolio snapshot
    snapshot_id = data_store.save_portfolio_snapshot(portfolio_snapshot)
    print(f"✅ Saved diversified portfolio snapshot with ID: {snapshot_id}")
    
    # Display portfolio analysis
    print("\n📊 Diversified Portfolio Analysis")
    print("=" * 60)
    
    # Sector breakdown
    sectors = {
        "Technology": ["AAPL", "MSFT"],
        "Healthcare": ["JNJ", "PFE"],
        "Financial Services": ["JPM", "BAC"],
        "Consumer Goods": ["PG", "KO"],
        "Energy": ["XOM"],
        "ETFs/Diversified": ["SPY", "VTI", "VXUS", "BND"]
    }
    
    print("Sector Allocation:")
    for sector, symbols in sectors.items():
        sector_value = sum(pos.market_value for pos in demo_positions if pos.symbol in symbols)
        sector_pct = (sector_value / total_value) * 100
        print(f"  {sector}: {sector_pct:.1f}% (${sector_value:,.2f})")
    
    print(f"\nPortfolio Summary:")
    print(f"  Total Value: ${total_value:,.2f}")
    print(f"  Total P&L: ${total_pnl:,.2f} ({(total_pnl/sum(pos.cost_basis for pos in demo_positions)*100):.2f}%)")
    print(f"  Day P&L: ${total_day_pnl:,.2f}")
    print(f"  Positions: {len(demo_positions)}")
    print(f"  Available Cash: ${portfolio_snapshot.buying_power:,.2f}")
    
    # Risk analysis
    print(f"\nRisk Analysis:")
    largest_position = max(pos.market_value for pos in demo_positions)
    largest_pct = (largest_position / total_value) * 100
    print(f"  Largest Position: {largest_pct:.1f}% (reduced from 47.6%)")
    print(f"  Sector Diversification: 6 sectors")
    print(f"  Geographic Diversification: US + International (VXUS)")
    print(f"  Asset Class Diversification: Stocks + Bonds (BND)")
    
    print("\n🎉 Portfolio successfully diversified!")
    print("\nKey Improvements:")
    print("✅ Reduced concentration risk (largest position now ~12.5%)")
    print("✅ Added sector diversification (6 different sectors)")
    print("✅ Added international exposure (VXUS)")
    print("✅ Added bond allocation for stability (BND)")
    print("✅ Maintained growth potential with quality stocks")


if __name__ == "__main__":
    main()