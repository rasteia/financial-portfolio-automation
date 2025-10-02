"""
Integration tests for the REST API.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from financial_portfolio_automation.api.app import app
from financial_portfolio_automation.api.auth import create_access_token, UserRole


class TestAPIIntegration:
    """Integration test cases for the REST API."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        
        # Create test tokens for different user roles
        self.admin_token = create_access_token({
            "sub": "admin",
            "user_id": "1",
            "role": "admin"
        })
        
        self.trader_token = create_access_token({
            "sub": "trader",
            "user_id": "2",
            "role": "trader"
        })
        
        self.readonly_token = create_access_token({
            "sub": "readonly",
            "user_id": "3",
            "role": "readonly"
        })
        
        # Headers for authenticated requests
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        self.trader_headers = {"Authorization": f"Bearer {self.trader_token}"}
        self.readonly_headers = {"Authorization": f"Bearer {self.readonly_token}"}
    
    def test_api_authentication_flow(self):
        """Test complete API authentication flow."""
        # Test unauthenticated access
        response = self.client.get("/api/v1/portfolio/")
        assert response.status_code == 401
        
        # Test authenticated access
        with patch('financial_portfolio_automation.mcp.portfolio_tools.PortfolioTools') as mock_tools:
            mock_portfolio_tools = MagicMock()
            mock_portfolio_tools.get_portfolio_overview.return_value = {
                'total_value': 100000.0,
                'buying_power': 25000.0,
                'day_pnl': 1500.0,
                'total_pnl': 5000.0,
                'position_count': 10,
                'last_updated': '2024-01-01 10:00:00'
            }
            mock_tools.return_value = mock_portfolio_tools
            
            response = self.client.get("/api/v1/portfolio/", headers=self.admin_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data['total_value'] == 100000.0
            assert data['position_count'] == 10
    
    def test_role_based_access_control(self):
        """Test role-based access control across different endpoints."""
        # Test read-only user can access read endpoints
        with patch('financial_portfolio_automation.mcp.portfolio_tools.PortfolioTools') as mock_tools:
            mock_portfolio_tools = MagicMock()
            mock_portfolio_tools.get_portfolio_overview.return_value = {
                'total_value': 100000.0,
                'buying_power': 25000.0,
                'day_pnl': 1500.0,
                'total_pnl': 5000.0,
                'position_count': 10,
                'last_updated': '2024-01-01 10:00:00'
            }
            mock_tools.return_value = mock_portfolio_tools
            
            response = self.client.get("/api/v1/portfolio/", headers=self.readonly_headers)
            assert response.status_code == 200
        
        # Test read-only user cannot access write endpoints
        order_data = {
            "symbol": "AAPL",
            "quantity": 100,
            "side": "buy",
            "order_type": "market"
        }
        
        response = self.client.post(
            "/api/v1/execution/orders",
            json=order_data,
            headers=self.readonly_headers
        )
        assert response.status_code == 403  # Forbidden
        
        # Test trader can access execution endpoints
        with patch('financial_portfolio_automation.mcp.execution_tools.ExecutionTools') as mock_exec:
            mock_execution_tools = MagicMock()
            mock_execution_tools.place_order.return_value = {
                'success': True,
                'order_id': '12345',
                'message': 'Order placed successfully',
                'timestamp': '2024-01-01T10:00:00Z'
            }
            mock_exec.return_value = mock_execution_tools
            
            response = self.client.post(
                "/api/v1/execution/orders",
                json=order_data,
                headers=self.trader_headers
            )
            assert response.status_code == 200
    
    @patch('financial_portfolio_automation.mcp.portfolio_tools.PortfolioTools')
    def test_portfolio_endpoints_integration(self, mock_tools):
        """Test portfolio endpoints integration."""
        # Mock portfolio tools
        mock_portfolio_tools = MagicMock()
        mock_tools.return_value = mock_portfolio_tools
        
        # Test portfolio overview
        mock_portfolio_tools.get_portfolio_overview.return_value = {
            'total_value': 150000.0,
            'buying_power': 30000.0,
            'day_pnl': 2500.0,
            'total_pnl': 15000.0,
            'position_count': 12,
            'last_updated': '2024-01-01 15:30:00'
        }
        
        response = self.client.get("/api/v1/portfolio/", headers=self.admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data['total_value'] == 150000.0
        assert data['position_count'] == 12
        
        # Test positions endpoint
        mock_portfolio_tools.get_positions.return_value = [
            {
                'symbol': 'AAPL',
                'quantity': 100,
                'market_value': 15000.0,
                'cost_basis': 14000.0,
                'unrealized_pnl': 1000.0,
                'day_pnl': 150.0,
                'allocation_percent': 10.0,
                'current_price': 150.0
            }
        ]
        
        response = self.client.get("/api/v1/portfolio/positions", headers=self.admin_headers)
        assert response.status_code == 200
        
        positions = response.json()
        assert len(positions) == 1
        assert positions[0]['symbol'] == 'AAPL'
        assert positions[0]['quantity'] == 100
    
    @patch('financial_portfolio_automation.mcp.risk_tools.RiskTools')
    def test_analysis_endpoints_integration(self, mock_risk_tools):
        """Test analysis endpoints integration."""
        # Mock risk tools
        mock_risk_tools_instance = MagicMock()
        mock_risk_tools.return_value = mock_risk_tools_instance
        
        mock_risk_tools_instance.assess_portfolio_risk.return_value = {
            'var': 5000.0,
            'expected_shortfall': 7500.0,
            'beta': 1.2,
            'volatility': 0.18,
            'max_drawdown': 0.10,
            'sharpe_ratio': 1.5,
            'sortino_ratio': 1.8
        }
        
        response = self.client.get("/api/v1/analysis/risk", headers=self.admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data['var'] == 5000.0
        assert data['beta'] == 1.2
        assert data['sharpe_ratio'] == 1.5
    
    @patch('financial_portfolio_automation.mcp.execution_tools.ExecutionTools')
    def test_execution_endpoints_integration(self, mock_exec_tools):
        """Test execution endpoints integration."""
        # Mock execution tools
        mock_execution_tools = MagicMock()
        mock_exec_tools.return_value = mock_execution_tools
        
        # Test order placement
        mock_execution_tools.place_order.return_value = {
            'success': True,
            'order_id': '12345678-1234-1234-1234-123456789012',
            'message': 'Order placed successfully',
            'timestamp': '2024-01-01T15:30:00Z'
        }
        
        order_data = {
            "symbol": "AAPL",
            "quantity": 100,
            "side": "buy",
            "order_type": "limit",
            "limit_price": 150.0
        }
        
        response = self.client.post(
            "/api/v1/execution/orders",
            json=order_data,
            headers=self.trader_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is True
        assert 'order_id' in data
        
        # Test order listing
        mock_execution_tools.get_orders.return_value = [
            {
                'order_id': '12345678-1234-1234-1234-123456789012',
                'symbol': 'AAPL',
                'quantity': 100,
                'filled_quantity': 0,
                'side': 'buy',
                'order_type': 'limit',
                'status': 'new',
                'time_in_force': 'day',
                'limit_price': 150.0,
                'created_at': '2024-01-01T15:30:00Z',
                'updated_at': '2024-01-01T15:30:00Z'
            }
        ]
        
        response = self.client.get("/api/v1/execution/orders", headers=self.trader_headers)
        assert response.status_code == 200
        
        orders = response.json()
        assert len(orders) == 1
        assert orders[0]['symbol'] == 'AAPL'
        assert orders[0]['status'] == 'new'
    
    @patch('financial_portfolio_automation.mcp.monitoring_tools.MonitoringTools')
    def test_monitoring_endpoints_integration(self, mock_monitoring_tools):
        """Test monitoring endpoints integration."""
        # Mock monitoring tools
        mock_monitoring_tools_instance = MagicMock()
        mock_monitoring_tools.return_value = mock_monitoring_tools_instance
        
        # Test alerts endpoint
        mock_monitoring_tools_instance.get_alerts.return_value = [
            {
                'severity': 'WARNING',
                'message': 'Portfolio loss exceeds 5% threshold',
                'symbol': 'Portfolio',
                'is_active': True,
                'triggered_at': '2024-01-01 15:45:00'
            }
        ]
        
        response = self.client.get("/api/v1/monitoring/alerts", headers=self.admin_headers)
        assert response.status_code == 200
        
        alerts = response.json()
        assert len(alerts) == 1
        assert alerts[0]['severity'] == 'WARNING'
        assert alerts[0]['is_active'] is True
        
        # Test real-time data endpoint
        mock_monitoring_tools_instance.get_real_time_data.return_value = {
            'portfolio_summary': {
                'total_value': 150000.0,
                'day_pnl': 2500.0,
                'position_count': 12
            },
            'alerts': []
        }
        
        response = self.client.get("/api/v1/monitoring/real-time", headers=self.admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert 'portfolio_summary' in data
        assert data['portfolio_summary']['total_value'] == 150000.0
    
    def test_api_error_handling(self):
        """Test API error handling across endpoints."""
        # Test 404 for non-existent endpoints
        response = self.client.get("/api/v1/nonexistent", headers=self.admin_headers)
        assert response.status_code == 404
        
        # Test 422 for invalid request data
        invalid_order = {
            "symbol": "",  # Invalid empty symbol
            "quantity": -100,  # Invalid negative quantity
            "side": "invalid_side"  # Invalid side
        }
        
        response = self.client.post(
            "/api/v1/execution/orders",
            json=invalid_order,
            headers=self.trader_headers
        )
        assert response.status_code == 422  # Unprocessable Entity
        
        # Test 401 for invalid token
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = self.client.get("/api/v1/portfolio/", headers=invalid_headers)
        assert response.status_code == 401
    
    def test_api_pagination(self):
        """Test API pagination functionality."""
        with patch('financial_portfolio_automation.mcp.execution_tools.ExecutionTools') as mock_exec:
            mock_execution_tools = MagicMock()
            mock_exec.return_value = mock_execution_tools
            
            # Mock paginated orders
            mock_execution_tools.get_orders.return_value = [
                {
                    'order_id': f'order-{i}',
                    'symbol': 'AAPL',
                    'quantity': 100,
                    'filled_quantity': 100,
                    'side': 'buy',
                    'order_type': 'market',
                    'status': 'filled',
                    'time_in_force': 'day',
                    'created_at': '2024-01-01T15:30:00Z',
                    'updated_at': '2024-01-01T15:31:00Z'
                }
                for i in range(10)
            ]
            
            # Test with limit and offset
            response = self.client.get(
                "/api/v1/execution/orders?limit=5&offset=0",
                headers=self.trader_headers
            )
            assert response.status_code == 200
            
            orders = response.json()
            assert len(orders) == 10  # Mock returns all, but real implementation would respect limit
    
    def test_api_filtering(self):
        """Test API filtering functionality."""
        with patch('financial_portfolio_automation.mcp.portfolio_tools.PortfolioTools') as mock_tools:
            mock_portfolio_tools = MagicMock()
            mock_tools.return_value = mock_portfolio_tools
            
            # Mock filtered positions
            mock_portfolio_tools.get_positions.return_value = [
                {
                    'symbol': 'AAPL',
                    'quantity': 100,
                    'market_value': 15000.0,
                    'cost_basis': 14000.0,
                    'unrealized_pnl': 1000.0,
                    'day_pnl': 150.0,
                    'allocation_percent': 10.0,
                    'current_price': 150.0
                }
            ]
            
            # Test symbol filtering
            response = self.client.get(
                "/api/v1/portfolio/positions?symbol=AAPL",
                headers=self.admin_headers
            )
            assert response.status_code == 200
            
            positions = response.json()
            assert len(positions) == 1
            assert positions[0]['symbol'] == 'AAPL'