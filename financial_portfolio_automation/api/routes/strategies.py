"""
Strategy management API routes.

Provides endpoints for listing strategies, running backtests, optimizing parameters,
executing strategies, and monitoring strategy performance.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime

from financial_portfolio_automation.api.auth import AuthUser, get_current_user, require_permission

router = APIRouter()


@router.get("/")
async def list_strategies(
    strategy_type: Optional[str] = Query(None, description="Filter by strategy type"),
    active_only: bool = Query(False, description="Show only active strategies"),
    current_user: AuthUser = Depends(require_permission("strategies:read"))
):
    """
    List available trading strategies and their configurations.
    
    Shows strategy details including parameters, performance metrics,
    and current status.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        strategies_data = strategy_tools.list_strategies(
            strategy_type=strategy_type,
            active_only=active_only
        )
        
        if not strategies_data:
            return []
        
        return strategies_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list strategies: {str(e)}")


@router.get("/{strategy_name}")
async def get_strategy(
    strategy_name: str,
    current_user: AuthUser = Depends(require_permission("strategies:read"))
):
    """
    Get detailed information about a specific strategy.
    
    Returns strategy configuration, parameters, performance history,
    and current status.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        strategy_data = strategy_tools.get_strategy(strategy_name=strategy_name)
        
        if not strategy_data:
            raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
        
        return strategy_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve strategy: {str(e)}")


@router.post("/{strategy_name}/backtest")
async def run_backtest(
    strategy_name: str,
    start_date: Optional[str] = Query(None, description="Backtest start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Backtest end date (YYYY-MM-DD)"),
    initial_capital: float = Query(100000, description="Initial capital for backtest"),
    benchmark: Optional[str] = Query(None, description="Benchmark symbol for comparison"),
    current_user: AuthUser = Depends(require_permission("strategies:read"))
):
    """
    Run strategy backtest with historical data.
    
    Simulates strategy performance over historical period and provides
    comprehensive performance analysis and risk metrics.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        # Set default dates if not provided
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=365)
            start_date = start_dt.strftime('%Y-%m-%d')
            end_date = end_dt.strftime('%Y-%m-%d')
        
        backtest_results = strategy_tools.run_backtest(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            benchmark=benchmark.upper() if benchmark else None
        )
        
        if not backtest_results:
            raise HTTPException(status_code=500, detail="Backtest failed or returned no results")
        
        return backtest_results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run backtest: {str(e)}")


@router.post("/{strategy_name}/optimize")
async def optimize_strategy(
    strategy_name: str,
    parameter_ranges: Dict[str, Dict[str, float]],
    objective: str = Query("sharpe", description="Optimization objective"),
    start_date: Optional[str] = Query(None, description="Optimization start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Optimization end date (YYYY-MM-DD)"),
    max_iterations: int = Query(100, description="Maximum optimization iterations"),
    current_user: AuthUser = Depends(require_permission("strategies:write"))
):
    """
    Optimize strategy parameters using historical data.
    
    Uses various optimization algorithms to find optimal parameter combinations
    that maximize the specified objective function.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        # Set default dates if not provided
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=365)
            start_date = start_dt.strftime('%Y-%m-%d')
            end_date = end_dt.strftime('%Y-%m-%d')
        
        optimization_results = strategy_tools.optimize_strategy(
            strategy_name=strategy_name,
            parameter_ranges=parameter_ranges,
            objective=objective,
            start_date=start_date,
            end_date=end_date,
            max_iterations=max_iterations
        )
        
        if not optimization_results:
            raise HTTPException(status_code=500, detail="Optimization failed or returned no results")
        
        return optimization_results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to optimize strategy: {str(e)}")


@router.post("/{strategy_name}/execute")
async def execute_strategy(
    strategy_name: str,
    dry_run: bool = Query(False, description="Simulate execution without placing real orders"),
    max_positions: Optional[int] = Query(None, description="Maximum number of positions to hold"),
    capital_allocation: Optional[float] = Query(None, description="Capital allocation for this strategy"),
    current_user: AuthUser = Depends(require_permission("strategies:write"))
):
    """
    Execute trading strategy with current market conditions.
    
    Runs the strategy against live market data and generates trading signals.
    Use dry_run=true to simulate without placing actual orders.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        execution_results = strategy_tools.execute_strategy(
            strategy_name=strategy_name,
            dry_run=dry_run,
            max_positions=max_positions,
            capital_allocation=capital_allocation
        )
        
        if not execution_results:
            raise HTTPException(status_code=500, detail="Strategy execution failed")
        
        return execution_results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute strategy: {str(e)}")


@router.get("/status")
async def get_strategy_status(
    strategy_name: Optional[str] = Query(None, description="Filter by specific strategy name"),
    active_only: bool = Query(False, description="Show only active strategy executions"),
    last_hours: int = Query(24, description="Show executions from last N hours"),
    current_user: AuthUser = Depends(require_permission("strategies:read"))
):
    """
    Monitor strategy execution status and performance.
    
    Shows current status of running strategies, recent executions,
    and real-time performance metrics.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        status_data = strategy_tools.get_strategy_status(
            strategy_name=strategy_name,
            active_only=active_only,
            hours_back=last_hours
        )
        
        if not status_data:
            return {
                "active_strategies": [],
                "recent_executions": [],
                "performance_summary": {},
                "system_health": {}
            }
        
        return status_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get strategy status: {str(e)}")


@router.put("/{strategy_name}/parameters")
async def update_strategy_parameters(
    strategy_name: str,
    parameters: Dict[str, Any],
    current_user: AuthUser = Depends(require_permission("strategies:write"))
):
    """
    Update strategy parameters.
    
    Updates the configuration parameters for the specified strategy.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        update_result = strategy_tools.update_strategy_parameters(
            strategy_name=strategy_name,
            parameters=parameters
        )
        
        if not update_result or not update_result.get('success'):
            error_msg = update_result.get('error', 'Unknown error') if update_result else 'Parameter update failed'
            raise HTTPException(status_code=400, detail=error_msg)
        
        return {
            "message": f"Strategy '{strategy_name}' parameters updated successfully",
            "strategy_name": strategy_name,
            "updated_parameters": parameters,
            "updated_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update strategy parameters: {str(e)}")


@router.post("/{strategy_name}/start")
async def start_strategy(
    strategy_name: str,
    current_user: AuthUser = Depends(require_permission("strategies:write"))
):
    """
    Start a strategy for continuous execution.
    
    Activates the strategy for ongoing execution based on its schedule
    and configuration.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        start_result = strategy_tools.start_strategy(strategy_name=strategy_name)
        
        if not start_result or not start_result.get('success'):
            error_msg = start_result.get('error', 'Unknown error') if start_result else 'Strategy start failed'
            raise HTTPException(status_code=400, detail=error_msg)
        
        return {
            "message": f"Strategy '{strategy_name}' started successfully",
            "strategy_name": strategy_name,
            "status": "active",
            "started_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start strategy: {str(e)}")


@router.post("/{strategy_name}/stop")
async def stop_strategy(
    strategy_name: str,
    current_user: AuthUser = Depends(require_permission("strategies:write"))
):
    """
    Stop a running strategy.
    
    Deactivates the strategy and stops any ongoing executions.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        stop_result = strategy_tools.stop_strategy(strategy_name=strategy_name)
        
        if not stop_result or not stop_result.get('success'):
            error_msg = stop_result.get('error', 'Unknown error') if stop_result else 'Strategy stop failed'
            raise HTTPException(status_code=400, detail=error_msg)
        
        return {
            "message": f"Strategy '{strategy_name}' stopped successfully",
            "strategy_name": strategy_name,
            "status": "inactive",
            "stopped_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop strategy: {str(e)}")


@router.get("/{strategy_name}/signals")
async def get_strategy_signals(
    strategy_name: str,
    limit: int = Query(50, description="Maximum number of signals to return"),
    current_user: AuthUser = Depends(require_permission("strategies:read"))
):
    """
    Get recent signals generated by a strategy.
    
    Returns the most recent trading signals generated by the specified strategy.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        signals_data = strategy_tools.get_strategy_signals(
            strategy_name=strategy_name,
            limit=limit
        )
        
        if not signals_data:
            return []
        
        return signals_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve strategy signals: {str(e)}")


@router.get("/{strategy_name}/performance")
async def get_strategy_performance(
    strategy_name: str,
    period: str = Query("1m", description="Performance period"),
    current_user: AuthUser = Depends(require_permission("strategies:read"))
):
    """
    Get strategy performance metrics.
    
    Returns detailed performance analysis for the specified strategy
    including returns, risk metrics, and trade statistics.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        performance_data = strategy_tools.get_strategy_performance(
            strategy_name=strategy_name,
            period=period
        )
        
        if not performance_data:
            raise HTTPException(status_code=404, detail=f"Performance data not found for strategy '{strategy_name}'")
        
        return performance_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve strategy performance: {str(e)}")