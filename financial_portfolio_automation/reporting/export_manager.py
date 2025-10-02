"""
Export Manager for multi-format report output.

This module handles exporting report data to various formats including
PDF, HTML, CSV, JSON, and Excel with template support and customization.
"""

import os
import json
import csv
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import logging

from .types import ReportType, ReportFormat


class ExportManager:
    """
    Multi-format report export manager.
    
    Handles exporting report data to various formats with template
    support and customization options.
    """
    
    def __init__(self, output_directory: str = "reports"):
        """
        Initialize export manager.
        
        Args:
            output_directory: Base directory for report outputs
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Template directories
        self.template_directory = Path(__file__).parent / "templates"
        self.template_directory.mkdir(exist_ok=True)
    
    def export_report(
        self,
        report_data: Dict[str, Any],
        report_type: ReportType,
        format: ReportFormat,
        output_path: Optional[str] = None,
        include_charts: bool = True
    ) -> str:
        """
        Export report data to specified format.
        
        Args:
            report_data: Report data dictionary
            report_type: Type of report being exported
            format: Output format
            output_path: Optional custom output path
            include_charts: Whether to include charts in output
            
        Returns:
            Path to the exported file
            
        Raises:
            ValueError: If format is not supported
            RuntimeError: If export fails
        """
        try:
            self.logger.info(f"Exporting {report_type.value} report as {format.value}")
            
            # Generate output filename if not provided
            if not output_path:
                output_path = self._generate_filename(report_type, format)
            
            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Export based on format
            if format == ReportFormat.JSON:
                return self._export_json(report_data, output_file)
            elif format == ReportFormat.CSV:
                return self._export_csv(report_data, report_type, output_file)
            elif format == ReportFormat.HTML:
                return self._export_html(report_data, report_type, output_file, include_charts)
            elif format == ReportFormat.PDF:
                return self._export_pdf(report_data, report_type, output_file, include_charts)
            elif format == ReportFormat.EXCEL:
                return self._export_excel(report_data, report_type, output_file)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            raise RuntimeError(f"Failed to export report: {e}") from e
    
    def _export_json(self, report_data: Dict[str, Any], output_file: Path) -> str:
        """Export report data as JSON."""
        # Convert Decimal and date objects for JSON serialization
        json_data = self._serialize_for_json(report_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"JSON export completed: {output_file}")
        return str(output_file)
    
    def _export_csv(
        self, 
        report_data: Dict[str, Any], 
        report_type: ReportType, 
        output_file: Path
    ) -> str:
        """Export report data as CSV."""
        if report_type == ReportType.PERFORMANCE:
            return self._export_performance_csv(report_data, output_file)
        elif report_type == ReportType.TAX_SUMMARY:
            return self._export_tax_csv(report_data, output_file)
        elif report_type == ReportType.TRANSACTION_HISTORY:
            return self._export_transaction_csv(report_data, output_file)
        else:
            # Generic CSV export
            return self._export_generic_csv(report_data, output_file)
    
    def _export_html(
        self, 
        report_data: Dict[str, Any], 
        report_type: ReportType, 
        output_file: Path,
        include_charts: bool
    ) -> str:
        """Export report data as HTML."""
        # Generate HTML content
        html_content = self._generate_html_content(
            report_data, report_type, include_charts
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML export completed: {output_file}")
        return str(output_file)
    
    def _export_pdf(
        self, 
        report_data: Dict[str, Any], 
        report_type: ReportType, 
        output_file: Path,
        include_charts: bool
    ) -> str:
        """Export report data as PDF."""
        # For now, generate HTML and note that PDF conversion would be needed
        html_file = output_file.with_suffix('.html')
        self._export_html(report_data, report_type, html_file, include_charts)
        
        # In a real implementation, you would use a library like:
        # - weasyprint: HTML/CSS to PDF
        # - reportlab: Direct PDF generation
        # - pdfkit: wkhtmltopdf wrapper
        
        self.logger.info(f"PDF export (HTML) completed: {html_file}")
        return str(html_file)
    
    def _export_excel(
        self, 
        report_data: Dict[str, Any], 
        report_type: ReportType, 
        output_file: Path
    ) -> str:
        """Export report data as Excel."""
        # For now, export as CSV with .xlsx extension
        # In a real implementation, you would use openpyxl or xlsxwriter
        csv_file = output_file.with_suffix('.csv')
        self._export_csv(report_data, report_type, csv_file)
        
        self.logger.info(f"Excel export (CSV) completed: {csv_file}")
        return str(csv_file)
    
    def _export_performance_csv(
        self, 
        report_data: Dict[str, Any], 
        output_file: Path
    ) -> str:
        """Export performance report as CSV."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Performance Report'])
            writer.writerow([])
            
            # Write summary
            summary = report_data.get('portfolio_summary', {})
            writer.writerow(['Portfolio Summary'])
            writer.writerow(['Start Value', summary.get('start_value', 0)])
            writer.writerow(['End Value', summary.get('end_value', 0)])
            writer.writerow(['Total Return', summary.get('total_return', 0)])
            writer.writerow(['Total Return %', summary.get('total_return_pct', 0)])
            writer.writerow([])
            
            # Write metrics
            metrics = report_data.get('performance_metrics', {})
            if metrics:
                writer.writerow(['Performance Metrics'])
                writer.writerow(['Metric', 'Value'])
                for key, value in metrics.__dict__.items() if hasattr(metrics, '__dict__') else metrics.items():
                    writer.writerow([key.replace('_', ' ').title(), value])
                writer.writerow([])
            
            # Write asset allocation
            allocation = report_data.get('asset_allocation', [])
            if allocation:
                writer.writerow(['Asset Allocation'])
                writer.writerow(['Symbol', 'Weight %', 'Value', 'Return Contribution %'])
                for asset in allocation:
                    writer.writerow([
                        asset.symbol if hasattr(asset, 'symbol') else asset.get('symbol'),
                        asset.weight if hasattr(asset, 'weight') else asset.get('weight'),
                        asset.value if hasattr(asset, 'value') else asset.get('value'),
                        asset.return_contribution if hasattr(asset, 'return_contribution') else asset.get('return_contribution')
                    ])
        
        self.logger.info(f"Performance CSV export completed: {output_file}")
        return str(output_file)
    
    def _export_tax_csv(
        self, 
        report_data: Dict[str, Any], 
        output_file: Path
    ) -> str:
        """Export tax report as CSV."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Tax Report'])
            writer.writerow([])
            
            # Write tax summary
            summary = report_data.get('tax_summary', {})
            if summary:
                writer.writerow(['Tax Summary'])
                writer.writerow(['Tax Year', summary.tax_year if hasattr(summary, 'tax_year') else summary.get('tax_year')])
                writer.writerow(['Short Term Gain/Loss', summary.total_short_term_gain_loss if hasattr(summary, 'total_short_term_gain_loss') else summary.get('total_short_term_gain_loss')])
                writer.writerow(['Long Term Gain/Loss', summary.total_long_term_gain_loss if hasattr(summary, 'total_long_term_gain_loss') else summary.get('total_long_term_gain_loss')])
                writer.writerow(['Total Gain/Loss', summary.total_gain_loss if hasattr(summary, 'total_gain_loss') else summary.get('total_gain_loss')])
                writer.writerow([])
            
            # Write realized gains/losses
            gains_losses = report_data.get('realized_gains_losses', [])
            if gains_losses:
                writer.writerow(['Realized Gains/Losses'])
                writer.writerow([
                    'Symbol', 'Quantity', 'Sale Date', 'Sale Price', 
                    'Cost Basis', 'Gain/Loss', 'Type', 'Wash Sale'
                ])
                
                for gl in gains_losses:
                    writer.writerow([
                        gl.symbol if hasattr(gl, 'symbol') else gl.get('symbol'),
                        gl.quantity if hasattr(gl, 'quantity') else gl.get('quantity'),
                        gl.sale_date if hasattr(gl, 'sale_date') else gl.get('sale_date'),
                        gl.sale_price if hasattr(gl, 'sale_price') else gl.get('sale_price'),
                        gl.cost_basis if hasattr(gl, 'cost_basis') else gl.get('cost_basis'),
                        gl.gain_loss if hasattr(gl, 'gain_loss') else gl.get('gain_loss'),
                        gl.gain_loss_type.value if hasattr(gl, 'gain_loss_type') and hasattr(gl.gain_loss_type, 'value') else gl.get('gain_loss_type'),
                        gl.is_wash_sale if hasattr(gl, 'is_wash_sale') else gl.get('is_wash_sale')
                    ])
        
        self.logger.info(f"Tax CSV export completed: {output_file}")
        return str(output_file)
    
    def _export_transaction_csv(
        self, 
        report_data: Dict[str, Any], 
        output_file: Path
    ) -> str:
        """Export transaction report as CSV."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Transaction Report'])
            writer.writerow([])
            
            # Write transaction details
            transactions = report_data.get('transaction_details', [])
            if transactions:
                writer.writerow(['Transaction Details'])
                writer.writerow([
                    'Order ID', 'Symbol', 'Side', 'Quantity', 'Price', 
                    'Value', 'Order Type', 'Created At', 'Filled At', 
                    'Commission', 'Fees'
                ])
                
                for transaction in transactions:
                    writer.writerow([
                        transaction.get('order_id'),
                        transaction.get('symbol'),
                        transaction.get('side'),
                        transaction.get('quantity'),
                        transaction.get('price'),
                        transaction.get('value'),
                        transaction.get('order_type'),
                        transaction.get('created_at'),
                        transaction.get('filled_at'),
                        transaction.get('commission'),
                        transaction.get('fees')
                    ])
        
        self.logger.info(f"Transaction CSV export completed: {output_file}")
        return str(output_file)
    
    def _export_generic_csv(
        self, 
        report_data: Dict[str, Any], 
        output_file: Path
    ) -> str:
        """Export generic report data as CSV."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write metadata
            metadata = report_data.get('report_metadata', {})
            writer.writerow(['Report Generated:', metadata.get('generated_at')])
            writer.writerow(['Start Date:', metadata.get('start_date')])
            writer.writerow(['End Date:', metadata.get('end_date')])
            writer.writerow([])
            
            # Write flattened data
            for key, value in report_data.items():
                if key != 'report_metadata':
                    writer.writerow([key.replace('_', ' ').title(), str(value)])
        
        self.logger.info(f"Generic CSV export completed: {output_file}")
        return str(output_file)
    
    def _generate_html_content(
        self, 
        report_data: Dict[str, Any], 
        report_type: ReportType,
        include_charts: bool
    ) -> str:
        """Generate HTML content for the report."""
        metadata = report_data.get('report_metadata', {})
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_type.value.replace('_', ' ').title()} Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .table {{ width: 100%; border-collapse: collapse; }}
        .table th, .table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .table th {{ background-color: #f2f2f2; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e9f4ff; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{report_type.value.replace('_', ' ').title()} Report</h1>
        <p>Generated: {metadata.get('generated_at', 'N/A')}</p>
        <p>Period: {metadata.get('start_date', 'N/A')} to {metadata.get('end_date', 'N/A')}</p>
    </div>
"""
        
        # Add report-specific content
        if report_type == ReportType.PERFORMANCE:
            html += self._generate_performance_html(report_data)
        elif report_type == ReportType.TAX_SUMMARY:
            html += self._generate_tax_html(report_data)
        elif report_type == ReportType.TRANSACTION_HISTORY:
            html += self._generate_transaction_html(report_data)
        
        html += """
</body>
</html>
"""
        return html
    
    def _generate_performance_html(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML content for performance report."""
        html = '<div class="section"><h2>Portfolio Summary</h2>'
        
        summary = report_data.get('portfolio_summary', {})
        html += f"""
        <div class="metric">
            <strong>Start Value:</strong> ${summary.get('start_value', 0):,.2f}
        </div>
        <div class="metric">
            <strong>End Value:</strong> ${summary.get('end_value', 0):,.2f}
        </div>
        <div class="metric">
            <strong>Total Return:</strong> ${summary.get('total_return', 0):,.2f}
        </div>
        <div class="metric">
            <strong>Return %:</strong> {summary.get('total_return_pct', 0):.2f}%
        </div>
        </div>
        """
        
        # Add performance metrics
        metrics = report_data.get('performance_metrics', {})
        if metrics:
            html += '<div class="section"><h2>Performance Metrics</h2>'
            html += '<table class="table"><tr><th>Metric</th><th>Value</th></tr>'
            
            metric_dict = metrics.__dict__ if hasattr(metrics, '__dict__') else metrics
            for key, value in metric_dict.items():
                if value is not None:
                    html += f'<tr><td>{key.replace("_", " ").title()}</td><td>{value}</td></tr>'
            
            html += '</table></div>'
        
        return html
    
    def _generate_tax_html(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML content for tax report."""
        html = '<div class="section"><h2>Tax Summary</h2>'
        
        summary = report_data.get('tax_summary', {})
        if summary:
            html += f"""
            <div class="metric">
                <strong>Tax Year:</strong> {summary.tax_year if hasattr(summary, 'tax_year') else summary.get('tax_year')}
            </div>
            <div class="metric">
                <strong>Short Term:</strong> ${summary.total_short_term_gain_loss if hasattr(summary, 'total_short_term_gain_loss') else summary.get('total_short_term_gain_loss', 0):,.2f}
            </div>
            <div class="metric">
                <strong>Long Term:</strong> ${summary.total_long_term_gain_loss if hasattr(summary, 'total_long_term_gain_loss') else summary.get('total_long_term_gain_loss', 0):,.2f}
            </div>
            <div class="metric">
                <strong>Total:</strong> ${summary.total_gain_loss if hasattr(summary, 'total_gain_loss') else summary.get('total_gain_loss', 0):,.2f}
            </div>
            """
        
        html += '</div>'
        return html
    
    def _generate_transaction_html(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML content for transaction report."""
        html = '<div class="section"><h2>Transaction Summary</h2>'
        
        summary = report_data.get('transaction_summary', {})
        if summary:
            html += f"""
            <div class="metric">
                <strong>Total Transactions:</strong> {summary.total_transactions if hasattr(summary, 'total_transactions') else summary.get('total_transactions', 0)}
            </div>
            <div class="metric">
                <strong>Total Volume:</strong> ${summary.total_volume if hasattr(summary, 'total_volume') else summary.get('total_volume', 0):,.2f}
            </div>
            <div class="metric">
                <strong>Total Commissions:</strong> ${summary.total_commissions if hasattr(summary, 'total_commissions') else summary.get('total_commissions', 0):,.2f}
            </div>
            """
        
        html += '</div>'
        return html
    
    def _serialize_for_json(self, obj: Any) -> Any:
        """Serialize objects for JSON export."""
        if isinstance(obj, dict):
            return {key: self._serialize_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return self._serialize_for_json(obj.__dict__)
        else:
            return obj
    
    def _generate_filename(self, report_type: ReportType, format: ReportFormat) -> str:
        """Generate output filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type.value}_{timestamp}.{format.value}"
        return str(self.output_directory / filename)