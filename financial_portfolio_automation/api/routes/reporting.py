"""
Reporting API routes.

Provides endpoints for generating various reports, exporting data,
scheduling automated reports, and managing report templates.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from financial_portfolio_automation.api.auth import AuthUser, get_current_user, require_permission

router = APIRouter()


@router.post("/generate")
async def generate_report(
    background_tasks: BackgroundTasks,
    report_type: str = Query(..., description="Type of report to generate"),
    start_date: Optional[str] = Query(None, description="Report start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Report end date (YYYY-MM-DD)"),
    output_format: str = Query("pdf", description="Report output format"),
    template: Optional[str] = Query(None, description="Custom report template to use"),
    email_recipients: Optional[List[str]] = Query(None, description="Email recipients for the report"),
    current_user: AuthUser = Depends(require_permission("reporting:read"))
):
    """
    Generate comprehensive portfolio reports.
    
    Creates detailed reports including performance analysis, tax summaries,
    transaction history, risk assessment, and allocation breakdowns.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        # Set default dates if not provided
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=90)  # Default to last quarter
            start_date = start_dt.strftime('%Y-%m-%d')
            end_date = end_dt.strftime('%Y-%m-%d')
        
        # Generate report
        report_result = reporting_tools.generate_report(
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            output_format=output_format,
            template=template
        )
        
        if not report_result or not report_result.get('success'):
            error_msg = report_result.get('error', 'Unknown error') if report_result else 'Report generation failed'
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Schedule email delivery if recipients provided
        if email_recipients:
            background_tasks.add_task(
                _send_report_email,
                report_result.get('file_path'),
                email_recipients,
                report_type,
                start_date,
                end_date
            )
        
        return {
            "message": "Report generated successfully",
            "report_id": report_result.get('report_id'),
            "report_type": report_type,
            "file_path": report_result.get('file_path'),
            "file_size_mb": report_result.get('file_size_mb'),
            "generation_time_ms": report_result.get('generation_time_ms'),
            "download_url": f"/api/v1/reporting/download/{report_result.get('report_id')}",
            "email_scheduled": len(email_recipients) if email_recipients else 0,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/")
async def list_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    limit: int = Query(50, description="Maximum number of reports to return"),
    offset: int = Query(0, description="Number of reports to skip"),
    current_user: AuthUser = Depends(require_permission("reporting:read"))
):
    """
    List available reports with filtering and pagination.
    
    Returns a list of generated reports with metadata and download links.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        reports_data = reporting_tools.list_reports(
            report_type=report_type,
            limit=limit,
            offset=offset
        )
        
        if not reports_data:
            return []
        
        # Add download URLs
        for report in reports_data:
            report['download_url'] = f"/api/v1/reporting/download/{report.get('report_id')}"
        
        return reports_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")


@router.get("/download/{report_id}")
async def download_report(
    report_id: str,
    current_user: AuthUser = Depends(require_permission("reporting:read"))
):
    """
    Download a specific report file.
    
    Returns the report file for download.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        # Get report file path
        report_info = reporting_tools.get_report_info(report_id=report_id)
        
        if not report_info:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        
        file_path = report_info.get('file_path')
        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="Report file not found")
        
        # Determine media type based on file extension
        file_ext = Path(file_path).suffix.lower()
        media_type_map = {
            '.pdf': 'application/pdf',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.html': 'text/html'
        }
        media_type = media_type_map.get(file_ext, 'application/octet-stream')
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=f"{report_info.get('report_type', 'report')}_{report_id}{file_ext}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download report: {str(e)}")


@router.post("/export")
async def export_data(
    data_type: str = Query(..., description="Type of data to export"),
    export_format: str = Query("csv", description="Export format"),
    start_date: Optional[str] = Query(None, description="Export start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Export end date (YYYY-MM-DD)"),
    compress: bool = Query(False, description="Compress exported files"),
    current_user: AuthUser = Depends(require_permission("reporting:read"))
):
    """
    Export portfolio data in various formats.
    
    Exports positions, transactions, performance data, or all data
    in CSV, JSON, Excel, or Parquet format for external analysis.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        # Set default dates if not provided
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=365 * 2)  # Default to 2 years
            start_date = start_dt.strftime('%Y-%m-%d')
            end_date = end_dt.strftime('%Y-%m-%d')
        
        # Export data
        export_result = reporting_tools.export_data(
            data_type=data_type,
            export_format=export_format,
            start_date=start_date,
            end_date=end_date,
            compress=compress
        )
        
        if not export_result or not export_result.get('success'):
            error_msg = export_result.get('error', 'Unknown error') if export_result else 'Data export failed'
            raise HTTPException(status_code=500, detail=error_msg)
        
        return {
            "message": "Data exported successfully",
            "export_id": export_result.get('export_id'),
            "data_type": data_type,
            "export_format": export_format,
            "exported_files": export_result.get('exported_files', []),
            "total_size_mb": export_result.get('total_size_mb'),
            "compression_ratio": export_result.get('compression_ratio') if compress else None,
            "download_url": f"/api/v1/reporting/download-export/{export_result.get('export_id')}",
            "exported_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")


@router.get("/download-export/{export_id}")
async def download_export(
    export_id: str,
    current_user: AuthUser = Depends(require_permission("reporting:read"))
):
    """
    Download exported data files.
    
    Returns the exported data files as a download.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        # Get export file path
        export_info = reporting_tools.get_export_info(export_id=export_id)
        
        if not export_info:
            raise HTTPException(status_code=404, detail=f"Export {export_id} not found")
        
        file_path = export_info.get('file_path')
        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="Export file not found")
        
        return FileResponse(
            path=file_path,
            media_type='application/octet-stream',
            filename=f"portfolio_export_{export_id}.zip"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download export: {str(e)}")


@router.post("/schedule")
async def schedule_report(
    report_type: str = Query(..., description="Type of report to schedule"),
    frequency: str = Query(..., description="Report frequency"),
    time: str = Query("09:00", description="Time to generate report (HH:MM)"),
    email_recipients: Optional[List[str]] = Query(None, description="Email recipients"),
    report_format: str = Query("pdf", description="Report format"),
    template: Optional[str] = Query(None, description="Custom report template"),
    current_user: AuthUser = Depends(require_permission("reporting:write"))
):
    """
    Schedule automated report generation.
    
    Sets up recurring reports to be generated and optionally emailed
    at specified intervals.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        # Create schedule
        schedule_result = reporting_tools.schedule_report(
            report_type=report_type,
            frequency=frequency,
            time=time,
            email_recipients=email_recipients or [],
            report_format=report_format,
            template=template
        )
        
        if not schedule_result or not schedule_result.get('success'):
            error_msg = schedule_result.get('error', 'Unknown error') if schedule_result else 'Scheduling failed'
            raise HTTPException(status_code=500, detail=error_msg)
        
        return {
            "message": "Report scheduled successfully",
            "schedule_id": schedule_result.get('schedule_id'),
            "report_type": report_type,
            "frequency": frequency,
            "next_run_time": schedule_result.get('next_run_time'),
            "email_recipients": len(email_recipients) if email_recipients else 0,
            "scheduled_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule report: {str(e)}")


@router.get("/schedules")
async def list_scheduled_reports(
    current_user: AuthUser = Depends(require_permission("reporting:read"))
):
    """
    List all scheduled reports and their status.
    
    Shows all scheduled reports with their configurations and next run times.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        schedules_data = reporting_tools.list_scheduled_reports()
        
        if not schedules_data:
            return []
        
        return schedules_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list scheduled reports: {str(e)}")


@router.delete("/schedules/{schedule_id}")
async def cancel_scheduled_report(
    schedule_id: str,
    current_user: AuthUser = Depends(require_permission("reporting:write"))
):
    """
    Cancel a scheduled report.
    
    Removes the specified report from the scheduling system.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        cancel_result = reporting_tools.cancel_scheduled_report(schedule_id=schedule_id)
        
        if not cancel_result or not cancel_result.get('success'):
            error_msg = cancel_result.get('error', 'Unknown error') if cancel_result else 'Cancellation failed'
            raise HTTPException(status_code=400, detail=error_msg)
        
        return {
            "message": f"Scheduled report {schedule_id} cancelled successfully",
            "schedule_id": schedule_id,
            "cancelled_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel scheduled report: {str(e)}")


@router.get("/templates")
async def list_report_templates(
    current_user: AuthUser = Depends(require_permission("reporting:read"))
):
    """
    List available report templates.
    
    Shows all available report templates and their configurations.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        templates_data = reporting_tools.list_templates()
        
        if not templates_data:
            return []
        
        return templates_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list report templates: {str(e)}")


@router.get("/metrics")
async def get_reporting_metrics(
    current_user: AuthUser = Depends(require_permission("reporting:read"))
):
    """
    Get reporting system metrics and statistics.
    
    Returns statistics about report generation, usage, and system performance.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        metrics_data = reporting_tools.get_reporting_metrics()
        
        if not metrics_data:
            raise HTTPException(status_code=404, detail="Reporting metrics not available")
        
        return metrics_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve reporting metrics: {str(e)}")


async def _send_report_email(file_path: str, recipients: List[str], report_type: str, start_date: str, end_date: str):
    """
    Background task to send report via email.
    
    Sends the generated report to specified email recipients.
    """
    try:
        from financial_portfolio_automation.notifications.email_provider import EmailProvider
        
        email_provider = EmailProvider()
        
        subject = f"Portfolio {report_type.title()} Report ({start_date} to {end_date})"
        body = f"""
        Your portfolio {report_type} report for the period {start_date} to {end_date} is attached.
        
        This report was automatically generated by the Portfolio Management System.
        
        Best regards,
        Portfolio Management Team
        """
        
        # Send email with attachment
        email_provider.send_email(
            to_addresses=recipients,
            subject=subject,
            body=body,
            attachments=[file_path]
        )
        
    except Exception as e:
        # Log error but don't raise - this is a background task
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send report email: {e}")