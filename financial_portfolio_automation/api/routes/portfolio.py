"""
Portfolio management API routes.

Provides endpoints for portfolio overview, positions, performance,
allocation, and rebalancing operations.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime

from financial_portfolio_automation.api.auth import AuthUser, get_current_user, require_permission
from financial_portfolio_automation.api.schemas.portfolio import (
    PortfolioOverview,
    Position,
    PortfolioPerformance,
    AllocationBreakdown,
    RebalanceRequest,
    RebalanceResponse
)

router = APIRouter()


@router.get("/", response_model=PortfolioOverview)
async def get_portfolio_overview(
    current_user: AuthUser = Depends(require_permission("portfolio:read"))
):
    """
    Get portfolio overview and summary.
    
    Returns current portfolio value, buying power, P&L, and position count.
    """
    try:
        from financial_portfolio_automation.mcp.portfolio_tools import PortfolioTools
        
        portfolio_tools = PortfolioTools()
        portfolio_data = portfolio_tools.get_portfolio_overview()
        
        if not portfolio_data:
            raise HTTPException(status_code=404, detail="Portfolio data not found")
        
        return PortfolioOverview(**portfolio_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve portfolio overview: {str(e)}")


@router.get("/positions", response_model=List[Position])
async def get_positions(
    symbol: Optional[str] = Query(None, description="Filter by specific symbol"),
    min_value: Optional[float] = Query(None, description="Minimum position value filter"),
    sort_by: str = Query("value", description="Sort positions by field"),
    current_user: AuthUser = Depends(require_permission("portfolio:read"))
):
    """
    Get current portfolio positions.
    
    Returns detailed information about each position including quantity,
    market value, unrealized P&L, and allocation percentage.
    """
    try:
        from financial_portfolio_automation.mcp.portfolio_tools import PortfolioTools
        
        portfolio_tools = PortfolioTools()
        positions_data = portfolio_tools.get_positions()
        
        if not positions_data:
            return []
        
        # Apply filters
        if symbol:
            symbol = symbol.upper()
            positions_data = [pos for pos in positions_data if pos.get('symbol') == symbol]
        
        if min_value:
            positions_data = [pos for pos in positions_data 
                            if pos.get('market_value', 0) >= min_value]
        
        # Sort positions
        reverse_sort = sort_by in ['value', 'pnl']
        if sort_by == 'symbol':
            positions_data.sort(key=lambda x: x.get('symbol', ''))
        elif sort_by == 'value':
            positions_data.sort(key=lambda x: x.get('market_value', 0), reverse=reverse_sort)
        elif sort_by == 'pnl':
            positions_data.sort(key=lambda x: x.get('unrealized_pnl', 0), reverse=reverse_sort)
        elif sort_by == 'allocation':
            positions_data.sort(key=lambda x: x.get('allocation_percent', 0), reverse=reverse_sort)
        
        return [Position(**pos) for pos in positions_data]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve positions: {str(e)}")


@router.get("/performance", response_model=PortfolioPerformance)
async def get_portfolio_performance(
    period: str = Query("1m", description="Performance period (1d, 1w, 1m, 3m, 6m, 1y, ytd)"),
    benchmark: Optional[str] = Query(None, description="Benchmark symbol for comparison"),
    current_user: AuthUser = Depends(require_permission("portfolio:read"))
):
    """
    Get portfolio performance metrics.
    
    Returns returns, risk metrics, and performance attribution for the specified period.
    Optionally compare against a benchmark.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        performance_data = analysis_tools.get_portfolio_performance(period=period)
        
        if not performance_data:
            raise HTTPException(status_code=404, detail="Performance data not found")
        
        # Add benchmark comparison if requested
        if benchmark:
            benchmark = benchmark.upper()
            benchmark_data = analysis_tools.compare_to_benchmark(
                benchmark_symbol=benchmark, 
                period=period
            )
            if benchmark_data:
                performance_data['benchmark_comparison'] = benchmark_data
        
        return PortfolioPerformance(**performance_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance data: {str(e)}")


@router.get("/allocation", response_model=AllocationBreakdown)
async def get_portfolio_allocation(
    by_sector: bool = Query(False, description="Show allocation by sector"),
    by_asset_class: bool = Query(False, description="Show allocation by asset class"),
    min_allocation: float = Query(0.01, description="Minimum allocation percentage to display"),
    current_user: AuthUser = Depends(require_permission("portfolio:read"))
):
    """
    Get portfolio allocation breakdown.
    
    Shows allocation by individual positions, sectors, or asset classes.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        
        if by_sector:
            allocation_data = analysis_tools.get_sector_allocation()
            allocation_type = "sector"
        elif by_asset_class:
            allocation_data = analysis_tools.get_asset_class_allocation()
            allocation_type = "asset_class"
        else:
            allocation_data = analysis_tools.get_position_allocation()
            allocation_type = "position"
        
        if not allocation_data:
            raise HTTPException(status_code=404, detail="Allocation data not found")
        
        # Filter by minimum allocation
        filtered_data = [
            item for item in allocation_data 
            if item.get('allocation_percent', 0) >= min_allocation * 100
        ]
        
        # Sort by allocation percentage (descending)
        filtered_data.sort(key=lambda x: x.get('allocation_percent', 0), reverse=True)
        
        return AllocationBreakdown(
            allocation_type=allocation_type,
            allocations=filtered_data,
            total_shown_percent=sum(item.get('allocation_percent', 0) for item in filtered_data),
            item_count=len(filtered_data)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve allocation data: {str(e)}")


@router.post("/rebalance", response_model=RebalanceResponse)
async def generate_rebalancing_plan(
    request: RebalanceRequest,
    current_user: AuthUser = Depends(require_permission("portfolio:write"))
):
    """
    Generate portfolio rebalancing recommendations.
    
    Analyzes current allocation against target allocation and suggests trades
    to bring the portfolio back into balance.
    """
    try:
        from financial_portfolio_automation.mcp.optimization_tools import OptimizationTools
        
        optimization_tools = OptimizationTools()
        
        # Get rebalancing recommendations
        rebalance_data = optimization_tools.generate_rebalancing_plan(
            target_weights=request.target_weights,
            threshold=request.rebalance_threshold
        )
        
        if not rebalance_data:
            raise HTTPException(status_code=500, detail="Failed to generate rebalancing plan")
        
        return RebalanceResponse(**rebalance_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate rebalancing plan: {str(e)}")


@router.post("/rebalance/execute")
async def execute_rebalancing_trades(
    request: RebalanceRequest,
    dry_run: bool = Query(False, description="Simulate execution without placing real orders"),
    current_user: AuthUser = Depends(require_permission("execution:write"))
):
    """
    Execute rebalancing trades.
    
    Executes the trades recommended by the rebalancing plan.
    Use dry_run=true to simulate without placing actual orders.
    """
    try:
        from financial_portfolio_automation.mcp.optimization_tools import OptimizationTools
        from financial_portfolio_automation.mcp.execution_tools import ExecutionTools
        
        optimization_tools = OptimizationTools()
        execution_tools = ExecutionTools()
        
        # Generate rebalancing plan
        rebalance_data = optimization_tools.generate_rebalancing_plan(
            target_weights=request.target_weights,
            threshold=request.rebalance_threshold
        )
        
        if not rebalance_data or not rebalance_data.get('trades_needed'):
            return {
                "message": "No rebalancing trades needed",
                "trades_executed": [],
                "trades_failed": [],
                "dry_run": dry_run
            }
        
        trades = rebalance_data['trades_needed']
        executed_trades = []
        failed_trades = []
        
        for trade in trades:
            try:
                if not dry_run:
                    result = execution_tools.place_order(
                        symbol=trade['symbol'],
                        quantity=trade['quantity'],
                        side=trade['side'],
                        order_type='market'
                    )
                    
                    if result.get('success'):
                        executed_trades.append({
                            **trade,
                            'order_id': result.get('order_id'),
                            'status': 'executed'
                        })
                    else:
                        failed_trades.append({
                            **trade,
                            'error': result.get('error'),
                            'status': 'failed'
                        })
                else:
                    # Dry run - just add to executed list
                    executed_trades.append({
                        **trade,
                        'status': 'simulated'
                    })
            
            except Exception as e:
                failed_trades.append({
                    **trade,
                    'error': str(e),
                    'status': 'error'
                })
        
        return {
            "message": f"Rebalancing {'simulated' if dry_run else 'executed'}",
            "trades_executed": executed_trades,
            "trades_failed": failed_trades,
            "dry_run": dry_run,
            "summary": {
                "total_trades": len(trades),
                "successful": len(executed_trades),
                "failed": len(failed_trades)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute rebalancing: {str(e)}")


@router.get("/value-history")
async def get_portfolio_value_history(
    period: str = Query("1m", description="Historical period"),
    interval: str = Query("1d", description="Data interval (1h, 1d, 1w)"),
    current_user: AuthUser = Depends(require_permission("portfolio:read"))
):
    """
    Get historical portfolio value data.
    
    Returns time series data of portfolio value for charting and analysis.
    """
    try:
        from financial_portfolio_automation.mcp.portfolio_tools import PortfolioTools
        
        portfolio_tools = PortfolioTools()
        history_data = portfolio_tools.get_portfolio_value_history(
            period=period,
            interval=interval
        )
        
        if not history_data:
            raise HTTPException(status_code=404, detail="Historical data not found")
        
        return {
            "period": period,
            "interval": interval,
            "data_points": len(history_data),
            "history": history_data
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve value history: {str(e)}")


@router.get("/metrics")
async def get_portfolio_metrics(
    current_user: AuthUser = Depends(require_permission("portfolio:read"))
):
    """
    Get comprehensive portfolio metrics.
    
    Returns detailed metrics including risk, performance, and allocation statistics.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        metrics_data = analysis_tools.get_comprehensive_metrics()
        
        if not metrics_data:
            raise HTTPException(status_code=404, detail="Metrics data not found")
        
        return metrics_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve portfolio metrics: {str(e)}")