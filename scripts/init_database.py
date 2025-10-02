#!/usr/bin/env python3
"""
Database Initialization Script

Initializes the database schema and creates necessary tables, indexes,
and initial data for the Financial Portfolio Automation System.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.config.settings import get_database_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Database initialization and setup"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or get_database_url()
        self.data_store = None
    
    async def initialize(self):
        """Initialize the database"""
        logger.info("Starting database initialization...")
        
        try:
            # Initialize data store
            self.data_store = DataStore(self.database_url)
            await self.data_store.initialize()
            
            # Create tables
            await self.create_tables()
            
            # Create indexes
            await self.create_indexes()
            
            # Create initial data
            await self.create_initial_data()
            
            # Verify setup
            await self.verify_setup()
            
            logger.info("Database initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
        finally:
            if self.data_store:
                await self.data_store.close()
    
    async def create_tables(self):
        """Create all necessary database tables"""
        logger.info("Creating database tables...")
        
        # Quotes table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS quotes (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                bid DECIMAL(10, 4) NOT NULL,
                ask DECIMAL(10, 4) NOT NULL,
                bid_size INTEGER NOT NULL,
                ask_size INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Trades table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                price DECIMAL(10, 4) NOT NULL,
                size INTEGER NOT NULL,
                conditions TEXT[],
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Positions table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS positions (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                quantity INTEGER NOT NULL,
                market_value DECIMAL(15, 2) NOT NULL,
                cost_basis DECIMAL(15, 2) NOT NULL,
                unrealized_pnl DECIMAL(15, 2) NOT NULL,
                day_pnl DECIMAL(15, 2) NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Orders table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(50) UNIQUE NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                quantity INTEGER NOT NULL,
                side VARCHAR(10) NOT NULL,
                order_type VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL,
                filled_quantity INTEGER DEFAULT 0,
                average_fill_price DECIMAL(10, 4),
                limit_price DECIMAL(10, 4),
                stop_price DECIMAL(10, 4),
                time_in_force VARCHAR(10) DEFAULT 'DAY',
                submitted_at TIMESTAMP WITH TIME ZONE,
                filled_at TIMESTAMP WITH TIME ZONE,
                cancelled_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Portfolio snapshots table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                total_value DECIMAL(15, 2) NOT NULL,
                buying_power DECIMAL(15, 2) NOT NULL,
                day_pnl DECIMAL(15, 2) NOT NULL,
                total_pnl DECIMAL(15, 2) NOT NULL,
                positions_data JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Account snapshots table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS account_snapshots (
                id SERIAL PRIMARY KEY,
                account_id VARCHAR(50) NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                buying_power DECIMAL(15, 2) NOT NULL,
                portfolio_value DECIMAL(15, 2) NOT NULL,
                equity DECIMAL(15, 2) NOT NULL,
                day_trade_buying_power DECIMAL(15, 2),
                regt_buying_power DECIMAL(15, 2),
                account_data JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Risk violations table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS risk_violations (
                id SERIAL PRIMARY KEY,
                violation_type VARCHAR(50) NOT NULL,
                symbol VARCHAR(10),
                description TEXT NOT NULL,
                severity VARCHAR(20) NOT NULL,
                violation_data JSONB,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Audit trail table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                id SERIAL PRIMARY KEY,
                entity_type VARCHAR(50) NOT NULL,
                entity_id VARCHAR(100) NOT NULL,
                action VARCHAR(50) NOT NULL,
                user_id VARCHAR(50),
                changes JSONB,
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Error logs table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id SERIAL PRIMARY KEY,
                error_type VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                stack_trace TEXT,
                context JSONB,
                severity VARCHAR(20) NOT NULL,
                resolved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Performance metrics table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id SERIAL PRIMARY KEY,
                metric_type VARCHAR(50) NOT NULL,
                metric_name VARCHAR(100) NOT NULL,
                value DECIMAL(15, 6) NOT NULL,
                metadata JSONB,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Strategy configurations table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS strategy_configs (
                id SERIAL PRIMARY KEY,
                strategy_id VARCHAR(50) UNIQUE NOT NULL,
                strategy_type VARCHAR(50) NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                parameters JSONB NOT NULL,
                risk_limits JSONB NOT NULL,
                symbols TEXT[] NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Strategy executions table
        await self.data_store._execute_query("""
            CREATE TABLE IF NOT EXISTS strategy_executions (
                id SERIAL PRIMARY KEY,
                strategy_id VARCHAR(50) NOT NULL,
                execution_id VARCHAR(50) UNIQUE NOT NULL,
                signals JSONB,
                orders_placed JSONB,
                execution_status VARCHAR(20) NOT NULL,
                execution_time DECIMAL(10, 6),
                error_message TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        logger.info("Database tables created successfully")
    
    async def create_indexes(self):
        """Create database indexes for performance"""
        logger.info("Creating database indexes...")
        
        # Quotes indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_quotes_symbol_timestamp 
            ON quotes (symbol, timestamp DESC)
        """)
        
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_quotes_timestamp 
            ON quotes (timestamp DESC)
        """)
        
        # Trades indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_trades_symbol_timestamp 
            ON trades (symbol, timestamp DESC)
        """)
        
        # Orders indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_orders_order_id 
            ON orders (order_id)
        """)
        
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_orders_symbol_status 
            ON orders (symbol, status)
        """)
        
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_orders_created_at 
            ON orders (created_at DESC)
        """)
        
        # Positions indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_positions_symbol 
            ON positions (symbol)
        """)
        
        # Portfolio snapshots indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_timestamp 
            ON portfolio_snapshots (timestamp DESC)
        """)
        
        # Account snapshots indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_account_snapshots_account_timestamp 
            ON account_snapshots (account_id, timestamp DESC)
        """)
        
        # Risk violations indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_risk_violations_type_created 
            ON risk_violations (violation_type, created_at DESC)
        """)
        
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_risk_violations_resolved 
            ON risk_violations (resolved, created_at DESC)
        """)
        
        # Audit trail indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_audit_trail_entity 
            ON audit_trail (entity_type, entity_id, created_at DESC)
        """)
        
        # Error logs indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_error_logs_type_created 
            ON error_logs (error_type, created_at DESC)
        """)
        
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_error_logs_resolved 
            ON error_logs (resolved, created_at DESC)
        """)
        
        # Performance metrics indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_performance_metrics_type_name_timestamp 
            ON performance_metrics (metric_type, metric_name, timestamp DESC)
        """)
        
        # Strategy configurations indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_strategy_configs_type_active 
            ON strategy_configs (strategy_type, is_active)
        """)
        
        # Strategy executions indexes
        await self.data_store._execute_query("""
            CREATE INDEX IF NOT EXISTS idx_strategy_executions_strategy_created 
            ON strategy_executions (strategy_id, created_at DESC)
        """)
        
        logger.info("Database indexes created successfully")
    
    async def create_initial_data(self):
        """Create initial data and configurations"""
        logger.info("Creating initial data...")
        
        # Create default strategy configurations
        default_strategies = [
            {
                'strategy_id': 'momentum_default',
                'strategy_type': 'momentum',
                'name': 'Default Momentum Strategy',
                'description': 'Basic momentum strategy with 20-day lookback',
                'parameters': {
                    'lookback_period': 20,
                    'threshold': 0.02,
                    'min_volume': 100000
                },
                'risk_limits': {
                    'max_position_size': 10000,
                    'max_portfolio_concentration': 0.2,
                    'stop_loss_percentage': 0.05
                },
                'symbols': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'],
                'is_active': False  # Inactive by default
            },
            {
                'strategy_id': 'mean_reversion_default',
                'strategy_type': 'mean_reversion',
                'name': 'Default Mean Reversion Strategy',
                'description': 'Basic mean reversion strategy with 50-day lookback',
                'parameters': {
                    'lookback_period': 50,
                    'std_dev_threshold': 2.0,
                    'min_volume': 50000
                },
                'risk_limits': {
                    'max_position_size': 5000,
                    'max_portfolio_concentration': 0.15,
                    'stop_loss_percentage': 0.03
                },
                'symbols': ['SPY', 'QQQ', 'IWM', 'GLD', 'TLT'],
                'is_active': False  # Inactive by default
            }
        ]
        
        for strategy in default_strategies:
            await self.data_store._execute_query("""
                INSERT INTO strategy_configs 
                (strategy_id, strategy_type, name, description, parameters, risk_limits, symbols, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (strategy_id) DO NOTHING
            """, 
                strategy['strategy_id'],
                strategy['strategy_type'],
                strategy['name'],
                strategy['description'],
                strategy['parameters'],
                strategy['risk_limits'],
                strategy['symbols'],
                strategy['is_active']
            )
        
        # Create initial performance metrics
        initial_metrics = [
            {
                'metric_type': 'system',
                'metric_name': 'database_initialized',
                'value': 1.0,
                'metadata': {'version': '1.0.0', 'initialized_at': datetime.now().isoformat()},
                'timestamp': datetime.now()
            }
        ]
        
        for metric in initial_metrics:
            await self.data_store._execute_query("""
                INSERT INTO performance_metrics 
                (metric_type, metric_name, value, metadata, timestamp)
                VALUES ($1, $2, $3, $4, $5)
            """,
                metric['metric_type'],
                metric['metric_name'],
                metric['value'],
                metric['metadata'],
                metric['timestamp']
            )
        
        logger.info("Initial data created successfully")
    
    async def verify_setup(self):
        """Verify database setup"""
        logger.info("Verifying database setup...")
        
        # Check that all tables exist
        tables_to_check = [
            'quotes', 'trades', 'positions', 'orders', 'portfolio_snapshots',
            'account_snapshots', 'risk_violations', 'audit_trail', 'error_logs',
            'performance_metrics', 'strategy_configs', 'strategy_executions'
        ]
        
        for table in tables_to_check:
            result = await self.data_store._execute_query("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = $1
                )
            """, table)
            
            if not result[0]['exists']:
                raise Exception(f"Table {table} was not created")
        
        # Check that indexes exist
        index_count = await self.data_store._execute_query("""
            SELECT COUNT(*) as count
            FROM pg_indexes 
            WHERE schemaname = 'public'
            AND indexname LIKE 'idx_%'
        """)
        
        if index_count[0]['count'] < 10:  # We should have at least 10 indexes
            logger.warning(f"Only {index_count[0]['count']} indexes found, expected more")
        
        # Check initial data
        strategy_count = await self.data_store._execute_query("""
            SELECT COUNT(*) as count FROM strategy_configs
        """)
        
        if strategy_count[0]['count'] < 2:
            logger.warning("Initial strategy configurations may not have been created")
        
        logger.info("Database setup verification completed")


async def main():
    """Main function"""
    logger.info("Financial Portfolio Automation - Database Initialization")
    
    # Get database URL from environment or config
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        try:
            database_url = get_database_url()
        except Exception as e:
            logger.error(f"Could not get database URL: {e}")
            sys.exit(1)
    
    # Initialize database
    initializer = DatabaseInitializer(database_url)
    
    try:
        await initializer.initialize()
        logger.info("Database initialization completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)