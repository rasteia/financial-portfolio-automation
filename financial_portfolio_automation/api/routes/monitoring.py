"""
Monitoring API routes.

Provides endpoints for real-time monitoring, alerts, risk monitoring,
and performance tracking.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import asyncio

from financial_portfolio_automation.api.auth import AuthUser, get_current_user, require_permission

router = APIRouter()


@router.get("/alerts")
async def get_alerts(
    active_only: bool = Query(False, description="Show only active alerts"),
    severity: Optional[str] = Query(None, description="Filter by alert severity"),
    last_hours: int = Query(24, description="Show alerts from last N hours"),
    current_user: AuthUser = Depends(require_permission("monitoring:read"))
):
    """
    Get portfolio alerts with filtering options.
    
    Returns current and historical alerts with filtering by severity,
    status, and time period.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        alerts_data = monitoring_tools.get_alerts(
            active_only=active_only,
            severity=severity,
            hours_back=last_hours
        )
        
        if not alerts_data:
            return []
        
        return alerts_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")


@router.post("/alerts")
async def create_alert(
    symbol: Optional[str] = None,
    metric: str = Query(..., description="Metric to monitor"),
    condition: str = Query(..., description="Alert condition"),
    threshold: float = Query(..., description="Alert threshold value"),
    email: Optional[str] = Query(None, description="Email for notifications"),
    sms: Optional[str] = Query(None, description="SMS number for notifications"),
    current_user: AuthUser = Depends(require_permission("monitoring:write"))
):
    """
    Create a new portfolio or position alert.
    
    Sets up monitoring alerts for price movements, P&L changes,
    volume spikes, or volatility changes.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        
        alert_result = monitoring_tools.create_alert(
            symbol=symbol.upper() if symbol else None,
            metric=metric,
            condition=condition,
            threshold=threshold,
            email=email,
            sms=sms
        )
        
        if not alert_result or not alert_result.get('success'):
            error_msg = alert_result.get('error', 'Unknown error') if alert_result else 'Alert creation failed'
            raise HTTPException(status_code=400, detail=error_msg)
        
        return {
            "message": "Alert created successfully",
            "alert_id": alert_result.get('alert_id'),
            "status": "active",
            "created_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user: AuthUser = Depends(require_permission("monitoring:write"))
):
    """
    Delete an existing alert.
    
    Removes the specified alert from the monitoring system.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        
        delete_result = monitoring_tools.delete_alert(alert_id=alert_id)
        
        if not delete_result or not delete_result.get('success'):
            error_msg = delete_result.get('error', 'Unknown error') if delete_result else 'Alert deletion failed'
            raise HTTPException(status_code=400, detail=error_msg)
        
        return {
            "message": f"Alert {alert_id} deleted successfully",
            "alert_id": alert_id,
            "deleted_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete alert: {str(e)}")


@router.get("/real-time")
async def get_real_time_data(
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols"),
    current_user: AuthUser = Depends(require_permission("monitoring:read"))
):
    """
    Get real-time portfolio and market data.
    
    Returns current portfolio status, position updates, and market indicators
    for monitoring dashboards.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        
        # Parse symbols if provided
        symbol_list = None
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(',')]
        
        real_time_data = monitoring_tools.get_real_time_data(
            symbols=symbol_list,
            include_alerts=True
        )
        
        if not real_time_data:
            raise HTTPException(status_code=404, detail="Real-time data not available")
        
        return real_time_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve real-time data: {str(e)}")


@router.get("/risk-metrics")
async def get_risk_metrics(
    symbol: Optional[str] = Query(None, description="Symbol for risk analysis"),
    time_window: str = Query("1d", description="Risk monitoring time window"),
    current_user: AuthUser = Depends(require_permission("monitoring:read"))
):
    """
    Get real-time portfolio risk metrics.
    
    Returns current risk exposure, VaR, volatility, and concentration
    metrics with real-time updates.
    """
    try:
        from financial_portfolio_automation.mcp.risk_tools import RiskTools
        
        risk_tools = RiskTools()
        
        risk_data = risk_tools.get_real_time_risk_metrics(
            symbol=symbol.upper() if symbol else None,
            time_window=time_window
        )
        
        if not risk_data:
            raise HTTPException(status_code=404, detail="Risk metrics not available")
        
        return risk_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve risk metrics: {str(e)}")


@router.get("/performance")
async def get_performance_monitoring(
    period: str = Query("1d", description="Performance monitoring period"),
    benchmark: Optional[str] = Query(None, description="Benchmark symbol for comparison"),
    current_user: AuthUser = Depends(require_permission("monitoring:read"))
):
    """
    Get real-time portfolio performance monitoring.
    
    Tracks portfolio returns, attribution, and performance metrics
    with continuous updates.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        
        performance_data = monitoring_tools.get_real_time_performance(
            period=period,
            benchmark=benchmark.upper() if benchmark else None
        )
        
        if not performance_data:
            raise HTTPException(status_code=404, detail="Performance monitoring data not available")
        
        return performance_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance monitoring: {str(e)}")


@router.get("/system-health")
async def get_system_health(
    current_user: AuthUser = Depends(require_permission("monitoring:read"))
):
    """
    Get system health and status information.
    
    Returns status of various system components including API connectivity,
    data feeds, and service availability.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        health_data = monitoring_tools.get_system_health()
        
        if not health_data:
            raise HTTPException(status_code=503, detail="System health check failed")
        
        return health_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve system health: {str(e)}")


# WebSocket endpoint for real-time monitoring
@router.websocket("/ws")
async def websocket_monitoring(
    websocket: WebSocket,
    symbols: Optional[str] = Query(None),
    update_interval: int = Query(5, description="Update interval in seconds")
):
    """
    WebSocket endpoint for real-time monitoring data.
    
    Provides continuous updates of portfolio data, alerts, and market information
    through a WebSocket connection.
    """
    await websocket.accept()
    
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        
        # Parse symbols if provided
        symbol_list = None
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(',')]
        
        while True:
            try:
                # Get real-time data
                real_time_data = monitoring_tools.get_real_time_data(
                    symbols=symbol_list,
                    include_alerts=True
                )
                
                if real_time_data:
                    # Add timestamp
                    real_time_data['timestamp'] = datetime.utcnow().isoformat()
                    
                    # Send data to client
                    await websocket.send_text(json.dumps(real_time_data, default=str))
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                error_message = {
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_message))
                await asyncio.sleep(update_interval)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.close(code=1000, reason=str(e))


@router.get("/watchlist")
async def get_watchlist(
    current_user: AuthUser = Depends(require_permission("monitoring:read"))
):
    """
    Get user's watchlist with real-time data.
    
    Returns the user's watchlist symbols with current prices,
    changes, and basic metrics.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        watchlist_data = monitoring_tools.get_watchlist()
        
        if not watchlist_data:
            return []
        
        return watchlist_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve watchlist: {str(e)}")


@router.post("/watchlist/{symbol}")
async def add_to_watchlist(
    symbol: str,
    current_user: AuthUser = Depends(require_permission("monitoring:write"))
):
    """
    Add a symbol to the watchlist.
    
    Adds the specified symbol to the user's watchlist for monitoring.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        symbol = symbol.upper()
        monitoring_tools = MonitoringTools()
        
        add_result = monitoring_tools.add_to_watchlist(symbol=symbol)
        
        if not add_result or not add_result.get('success'):
            error_msg = add_result.get('error', 'Unknown error') if add_result else 'Failed to add to watchlist'
            raise HTTPException(status_code=400, detail=error_msg)
        
        return {
            "message": f"Symbol {symbol} added to watchlist",
            "symbol": symbol,
            "added_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add to watchlist: {str(e)}")


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(
    symbol: str,
    current_user: AuthUser = Depends(require_permission("monitoring:write"))
):
    """
    Remove a symbol from the watchlist.
    
    Removes the specified symbol from the user's watchlist.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        symbol = symbol.upper()
        monitoring_tools = MonitoringTools()
        
        remove_result = monitoring_tools.remove_from_watchlist(symbol=symbol)
        
        if not remove_result or not remove_result.get('success'):
            error_msg = remove_result.get('error', 'Unknown error') if remove_result else 'Failed to remove from watchlist'
            raise HTTPException(status_code=400, detail=error_msg)
        
        return {
            "message": f"Symbol {symbol} removed from watchlist",
            "symbol": symbol,
            "removed_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove from watchlist: {str(e)}")