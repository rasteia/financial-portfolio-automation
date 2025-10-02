"""
Reporting commands for CLI.

Provides commands for generating various reports, exporting data,
scheduling automated reports, and managing report templates.
"""

import click
from typing import Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from financial_portfolio_automation.cli.utils import (
    format_output, format_currency, format_percentage, 
    handle_error, validate_date_range, confirm_action
)


@click.group()
def reporting():
    """Report generation and data export commands."""
    pass


@reporting.command()
@click.option('--type', 'report_type', 
              type=click.Choice(['performance', 'tax', 'transaction', 'risk', 'allocation']),
              default='performance', help='Type of report to generate')
@click.option('--start-date', type=str, help='Report start date (YYYY-MM-DD)')
@click.option('--end-date', type=str, help='Report end date (YYYY-MM-DD)')
@click.option('--format', 'output_format', 
              type=click.Choice(['pdf', 'html', 'excel', 'json']),
              default='pdf', help='Report output format')
@click.option('--output-file', type=str, help='Output file path')
@click.option('--template', type=str, help='Custom report template to use')
@click.pass_context
def generate(ctx, report_type: str, start_date: Optional[str], end_date: Optional[str],
             output_format: str, output_file: Optional[str], template: Optional[str]):
    """
    Generate comprehensive portfolio reports.
    
    Creates detailed reports including performance analysis, tax summaries,
    transaction history, risk assessment, and allocation breakdowns.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        # Validate date range if provided
        if start_date and end_date:
            start_dt, end_dt = validate_date_range(start_date, end_date)
        else:
            # Default to last quarter
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=90)
            start_date = start_dt.strftime('%Y-%m-%d')
            end_date = end_dt.strftime('%Y-%m-%d')
        
        click.echo(f"📊 Generating {report_type.title()} Report")
        click.echo(f"📅 Period: {start_date} to {end_date}")
        click.echo(f"📄 Format: {output_format.upper()}")
        click.echo("=" * 50)
        
        # Generate report
        with click.progressbar(length=100, label='Generating report') as bar:
            report_result = reporting_tools.generate_report(
                report_type=report_type,
                start_date=start_date,
                end_date=end_date,
                output_format=output_format,
                output_file=output_file,
                template=template,
                progress_callback=lambda p: bar.update(p - bar.pos)
            )
        
        if not report_result or not report_result.get('success'):
            error_msg = report_result.get('error', 'Unknown error') if report_result else 'Report generation failed'
            click.echo(f"❌ {error_msg}")
            return
        
        # Display report summary
        click.echo("\n✅ Report Generated Successfully")
        click.echo("=" * 40)
        
        report_info = {
            'Report Type': report_type.title(),
            'File Path': report_result.get('file_path', 'N/A'),
            'File Size': f"{report_result.get('file_size_mb', 0):.2f} MB",
            'Pages': report_result.get('page_count', 'N/A'),
            'Generation Time': f"{report_result.get('generation_time_ms', 0):.0f}ms"
        }
        
        info_output = format_output(report_info, ctx.obj['output_format'])
        click.echo(info_output)
        
        # Display report contents summary
        contents = report_result.get('contents_summary', {})
        if contents:
            click.echo("\n📋 Report Contents")
            click.echo("=" * 30)
            
            contents_info = {}
            if report_type == 'performance':
                contents_info = {
                    'Portfolio Value': format_currency(contents.get('portfolio_value', 0)),
                    'Total Return': format_percentage(contents.get('total_return', 0)),
                    'Positions Analyzed': contents.get('positions_count', 0),
                    'Transactions': contents.get('transactions_count', 0),
                    'Charts Included': contents.get('charts_count', 0)
                }
            elif report_type == 'tax':
                contents_info = {
                    'Realized Gains': format_currency(contents.get('realized_gains', 0)),
                    'Realized Losses': format_currency(contents.get('realized_losses', 0)),
                    'Net Gains/Losses': format_currency(contents.get('net_gains', 0)),
                    'Taxable Events': contents.get('taxable_events', 0),
                    'Tax Forms': ', '.join(contents.get('tax_forms', []))
                }
            elif report_type == 'transaction':
                contents_info = {
                    'Total Transactions': contents.get('total_transactions', 0),
                    'Buy Orders': contents.get('buy_orders', 0),
                    'Sell Orders': contents.get('sell_orders', 0),
                    'Total Volume': format_currency(contents.get('total_volume', 0)),
                    'Unique Symbols': contents.get('unique_symbols', 0)
                }
            elif report_type == 'risk':
                contents_info = {
                    'Risk Score': f"{contents.get('risk_score', 0):.2f}/10",
                    'VaR (95%)': format_currency(contents.get('var_95', 0)),
                    'Max Drawdown': format_percentage(contents.get('max_drawdown', 0)),
                    'Beta': f"{contents.get('beta', 0):.2f}",
                    'Stress Tests': contents.get('stress_tests_count', 0)
                }
            elif report_type == 'allocation':
                contents_info = {
                    'Asset Classes': contents.get('asset_classes', 0),
                    'Sectors': contents.get('sectors', 0),
                    'Individual Positions': contents.get('positions', 0),
                    'Concentration Risk': contents.get('concentration_risk', 'Low'),
                    'Diversification Score': f"{contents.get('diversification_score', 0):.2f}"
                }
            
            if contents_info:
                contents_output = format_output(contents_info, ctx.obj['output_format'])
                click.echo(contents_output)
        
        # Open report if requested
        if click.confirm("Open the generated report?", default=False):
            import subprocess
            import platform
            
            file_path = report_result.get('file_path')
            if file_path and Path(file_path).exists():
                try:
                    if platform.system() == 'Windows':
                        subprocess.run(['start', file_path], shell=True, check=True)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', file_path], check=True)
                    else:  # Linux
                        subprocess.run(['xdg-open', file_path], check=True)
                    
                    click.echo("📖 Report opened successfully")
                except subprocess.CalledProcessError:
                    click.echo("❌ Failed to open report automatically")
                    click.echo(f"📁 Report saved at: {file_path}")
            else:
                click.echo("❌ Report file not found")
        
    except Exception as e:
        handle_error(f"Failed to generate report: {e}", ctx.obj.get('verbose', False))


@reporting.command()
@click.option('--data-type', 
              type=click.Choice(['positions', 'transactions', 'performance', 'all']),
              default='all', help='Type of data to export')
@click.option('--format', 'export_format',
              type=click.Choice(['csv', 'json', 'excel', 'parquet']),
              default='csv', help='Export format')
@click.option('--start-date', type=str, help='Export start date (YYYY-MM-DD)')
@click.option('--end-date', type=str, help='Export end date (YYYY-MM-DD)')
@click.option('--output-dir', type=str, help='Output directory path')
@click.option('--compress', is_flag=True, help='Compress exported files')
@click.pass_context
def export(ctx, data_type: str, export_format: str, start_date: Optional[str], 
           end_date: Optional[str], output_dir: Optional[str], compress: bool):
    """
    Export portfolio data in various formats.
    
    Exports positions, transactions, performance data, or all data
    in CSV, JSON, Excel, or Parquet format for external analysis.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        # Validate date range if provided
        if start_date and end_date:
            start_dt, end_dt = validate_date_range(start_date, end_date)
        else:
            # Default to all available data
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=365 * 2)  # 2 years
            start_date = start_dt.strftime('%Y-%m-%d')
            end_date = end_dt.strftime('%Y-%m-%d')
        
        # Set output directory
        if not output_dir:
            output_dir = Path.cwd() / 'portfolio_exports'
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        click.echo(f"📤 Exporting {data_type.title()} Data")
        click.echo(f"📅 Period: {start_date} to {end_date}")
        click.echo(f"📄 Format: {export_format.upper()}")
        click.echo(f"📁 Output: {output_dir}")
        click.echo("=" * 50)
        
        # Export data
        with click.progressbar(length=100, label='Exporting data') as bar:
            export_result = reporting_tools.export_data(
                data_type=data_type,
                export_format=export_format,
                start_date=start_date,
                end_date=end_date,
                output_dir=str(output_dir),
                compress=compress,
                progress_callback=lambda p: bar.update(p - bar.pos)
            )
        
        if not export_result or not export_result.get('success'):
            error_msg = export_result.get('error', 'Unknown error') if export_result else 'Export failed'
            click.echo(f"❌ {error_msg}")
            return
        
        # Display export summary
        click.echo("\n✅ Data Exported Successfully")
        click.echo("=" * 40)
        
        exported_files = export_result.get('exported_files', [])
        if exported_files:
            click.echo("📁 Exported Files:")
            
            formatted_files = []
            total_size = 0
            
            for file_info in exported_files:
                file_size_mb = file_info.get('size_mb', 0)
                total_size += file_size_mb
                
                formatted_file = {
                    'File': file_info.get('filename', ''),
                    'Type': file_info.get('data_type', ''),
                    'Records': f"{file_info.get('record_count', 0):,}",
                    'Size': f"{file_size_mb:.2f} MB"
                }
                formatted_files.append(formatted_file)
            
            files_output = format_output(formatted_files, ctx.obj['output_format'])
            click.echo(files_output)
            
            # Summary
            click.echo(f"\n📊 Export Summary:")
            click.echo(f"📁 Files: {len(exported_files)}")
            click.echo(f"💾 Total Size: {total_size:.2f} MB")
            
            if compress:
                compression_ratio = export_result.get('compression_ratio', 1.0)
                click.echo(f"🗜️  Compression: {compression_ratio:.1f}x")
        
        # Data summary
        data_summary = export_result.get('data_summary', {})
        if data_summary:
            click.echo("\n📊 Data Summary:")
            
            summary_info = {}
            if data_type in ['positions', 'all']:
                summary_info.update({
                    'Current Positions': data_summary.get('current_positions', 0),
                    'Historical Positions': data_summary.get('historical_positions', 0)
                })
            
            if data_type in ['transactions', 'all']:
                summary_info.update({
                    'Total Transactions': data_summary.get('total_transactions', 0),
                    'Buy Orders': data_summary.get('buy_orders', 0),
                    'Sell Orders': data_summary.get('sell_orders', 0)
                })
            
            if data_type in ['performance', 'all']:
                summary_info.update({
                    'Performance Records': data_summary.get('performance_records', 0),
                    'Date Range': f"{data_summary.get('earliest_date', 'N/A')} to {data_summary.get('latest_date', 'N/A')}"
                })
            
            if summary_info:
                summary_output = format_output(summary_info, ctx.obj['output_format'])
                click.echo(summary_output)
        
    except Exception as e:
        handle_error(f"Failed to export data: {e}", ctx.obj.get('verbose', False))


@reporting.command()
@click.option('--report-type', 
              type=click.Choice(['performance', 'tax', 'transaction', 'risk']),
              required=True, help='Type of report to schedule')
@click.option('--frequency', 
              type=click.Choice(['daily', 'weekly', 'monthly', 'quarterly']),
              required=True, help='Report frequency')
@click.option('--time', type=str, default='09:00', help='Time to generate report (HH:MM)')
@click.option('--email', multiple=True, help='Email addresses to send reports to')
@click.option('--format', 'report_format',
              type=click.Choice(['pdf', 'html', 'excel']),
              default='pdf', help='Report format')
@click.option('--template', type=str, help='Custom report template')
@click.pass_context
def schedule(ctx, report_type: str, frequency: str, time: str, email: tuple,
             report_format: str, template: Optional[str]):
    """
    Schedule automated report generation.
    
    Sets up recurring reports to be generated and optionally emailed
    at specified intervals.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        # Validate time format
        try:
            datetime.strptime(time, '%H:%M')
        except ValueError:
            click.echo("❌ Invalid time format. Use HH:MM (24-hour format)")
            return
        
        click.echo(f"⏰ Scheduling {report_type.title()} Report")
        click.echo(f"📅 Frequency: {frequency.title()}")
        click.echo(f"🕐 Time: {time}")
        if email:
            click.echo(f"📧 Recipients: {', '.join(email)}")
        click.echo("=" * 50)
        
        # Create schedule
        schedule_result = reporting_tools.schedule_report(
            report_type=report_type,
            frequency=frequency,
            time=time,
            email_recipients=list(email),
            report_format=report_format,
            template=template
        )
        
        if not schedule_result or not schedule_result.get('success'):
            error_msg = schedule_result.get('error', 'Unknown error') if schedule_result else 'Scheduling failed'
            click.echo(f"❌ {error_msg}")
            return
        
        # Display schedule confirmation
        click.echo("✅ Report Scheduled Successfully")
        click.echo("=" * 40)
        
        schedule_info = {
            'Schedule ID': schedule_result.get('schedule_id', ''),
            'Report Type': report_type.title(),
            'Frequency': frequency.title(),
            'Next Run': schedule_result.get('next_run_time', ''),
            'Status': 'Active',
            'Recipients': len(email) if email else 0
        }
        
        schedule_output = format_output(schedule_info, ctx.obj['output_format'])
        click.echo(schedule_output)
        
        # Display next few run times
        next_runs = schedule_result.get('next_run_times', [])
        if next_runs:
            click.echo("\n📅 Upcoming Report Times:")
            for i, run_time in enumerate(next_runs[:5], 1):
                click.echo(f"  {i}. {run_time}")
        
    except Exception as e:
        handle_error(f"Failed to schedule report: {e}", ctx.obj.get('verbose', False))


@reporting.command()
@click.pass_context
def templates(ctx):
    """
    List and manage custom report templates.
    
    Shows available report templates and their configurations.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        click.echo("📋 Report Templates")
        click.echo("=" * 50)
        
        # Get templates
        templates_data = reporting_tools.list_templates()
        
        if not templates_data:
            click.echo("📭 No custom templates found")
            click.echo("\n💡 Default templates are available for all report types")
            return
        
        # Display templates
        formatted_templates = []
        for template in templates_data:
            formatted_template = {
                'Name': template.get('name', ''),
                'Type': template.get('report_type', ''),
                'Format': template.get('format', ''),
                'Created': template.get('created_date', ''),
                'Used': template.get('usage_count', 0),
                'Description': template.get('description', '')[:50] + '...' if len(template.get('description', '')) > 50 else template.get('description', '')
            }
            formatted_templates.append(formatted_template)
        
        templates_output = format_output(formatted_templates, ctx.obj['output_format'])
        click.echo(templates_output)
        
        # Template usage statistics
        total_templates = len(templates_data)
        total_usage = sum(t.get('usage_count', 0) for t in templates_data)
        most_used = max(templates_data, key=lambda x: x.get('usage_count', 0))
        
        click.echo(f"\n📊 Template Statistics:")
        click.echo(f"📋 Total Templates: {total_templates}")
        click.echo(f"🔄 Total Usage: {total_usage}")
        click.echo(f"🏆 Most Used: {most_used.get('name', 'N/A')} ({most_used.get('usage_count', 0)} times)")
        
    except Exception as e:
        handle_error(f"Failed to list templates: {e}", ctx.obj.get('verbose', False))


@reporting.command()
@click.pass_context
def schedules(ctx):
    """
    List and manage scheduled reports.
    
    Shows all scheduled reports and their status.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        click.echo("⏰ Scheduled Reports")
        click.echo("=" * 50)
        
        # Get scheduled reports
        schedules_data = reporting_tools.list_scheduled_reports()
        
        if not schedules_data:
            click.echo("📭 No scheduled reports found")
            return
        
        # Display schedules
        formatted_schedules = []
        for schedule in schedules_data:
            status_icon = '🟢' if schedule.get('is_active') else '🔴'
            
            formatted_schedule = {
                'ID': schedule.get('schedule_id', '')[:8] + '...',
                'Type': schedule.get('report_type', '').title(),
                'Frequency': schedule.get('frequency', '').title(),
                'Time': schedule.get('time', ''),
                'Status': f"{status_icon} {'Active' if schedule.get('is_active') else 'Inactive'}",
                'Next Run': schedule.get('next_run', ''),
                'Last Run': schedule.get('last_run', 'Never'),
                'Recipients': schedule.get('recipient_count', 0)
            }
            formatted_schedules.append(formatted_schedule)
        
        schedules_output = format_output(formatted_schedules, ctx.obj['output_format'])
        click.echo(schedules_output)
        
        # Schedule statistics
        active_count = sum(1 for s in schedules_data if s.get('is_active'))
        total_count = len(schedules_data)
        
        click.echo(f"\n📊 Schedule Summary:")
        click.echo(f"📋 Total Schedules: {total_count}")
        click.echo(f"🟢 Active: {active_count}")
        click.echo(f"🔴 Inactive: {total_count - active_count}")
        
        # Show options to manage schedules
        if schedules_data:
            click.echo(f"\n💡 Use 'reporting cancel-schedule <schedule_id>' to cancel a schedule")
        
    except Exception as e:
        handle_error(f"Failed to list scheduled reports: {e}", ctx.obj.get('verbose', False))


@reporting.command()
@click.argument('schedule_id', required=True)
@click.pass_context
def cancel_schedule(ctx, schedule_id: str):
    """
    Cancel a scheduled report.
    
    Removes the specified report from the scheduling system.
    """
    try:
        from financial_portfolio_automation.mcp.reporting_tools import ReportingTools
        
        reporting_tools = ReportingTools()
        
        click.echo(f"🗑️  Cancelling Schedule: {schedule_id}")
        click.echo("=" * 50)
        
        # Confirm cancellation
        if not confirm_action(f"Cancel scheduled report {schedule_id}?", default=False):
            click.echo("❌ Cancellation aborted")
            return
        
        # Cancel schedule
        cancel_result = reporting_tools.cancel_scheduled_report(schedule_id)
        
        if not cancel_result or not cancel_result.get('success'):
            error_msg = cancel_result.get('error', 'Unknown error') if cancel_result else 'Cancellation failed'
            click.echo(f"❌ {error_msg}")
            return
        
        click.echo("✅ Schedule cancelled successfully")
        
        # Show cancelled schedule details
        cancelled_schedule = cancel_result.get('cancelled_schedule', {})
        if cancelled_schedule:
            schedule_info = {
                'Schedule ID': cancelled_schedule.get('schedule_id', ''),
                'Report Type': cancelled_schedule.get('report_type', '').title(),
                'Frequency': cancelled_schedule.get('frequency', '').title(),
                'Was Active': 'Yes' if cancelled_schedule.get('was_active') else 'No',
                'Reports Generated': cancelled_schedule.get('reports_generated', 0)
            }
            
            info_output = format_output(schedule_info, ctx.obj['output_format'])
            click.echo(info_output)
        
    except Exception as e:
        handle_error(f"Failed to cancel schedule: {e}", ctx.obj.get('verbose', False))