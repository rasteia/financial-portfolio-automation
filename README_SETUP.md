# Portfolio Dashboard Setup

## Quick Start

1. **Copy the template configuration:**
   ```bash
   copy config.template.json config.json
   ```

2. **Add your Alpaca Paper Trading credentials to `config.json`:**
   - Get your paper trading API keys from [Alpaca Markets](https://alpaca.markets/)
   - Replace `YOUR_ALPACA_API_KEY_HERE` with your actual API key
   - Replace `YOUR_ALPACA_SECRET_KEY_HERE` with your actual secret key

3. **Start the dashboard:**
   ```bash
   python start_dashboard.py
   ```

4. **Access your dashboard:**
   - Web Dashboard: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Real-time Data: http://localhost:8000/api/v1/monitoring/real-time

## Security Notes

- `config.json` is ignored by git to protect your credentials
- Never commit files containing API keys or secrets
- Use paper trading mode for development and testing
- Set `trading_enabled: false` for dashboard-only mode

## Dashboard Endpoints

- **Portfolio Summary**: `/api/v1/portfolio/summary`
- **Real-time Monitoring**: `/api/v1/monitoring/real-time`
- **Risk Metrics**: `/api/v1/monitoring/risk-metrics`
- **Performance Data**: `/api/v1/monitoring/performance`
- **WebSocket Stream**: `ws://localhost:8000/api/v1/monitoring/ws`

## Troubleshooting

If you get "Alpaca API key required" errors:
1. Check that `config.json` exists and has your credentials
2. Verify the API key format is correct
3. Ensure you're using paper trading credentials from Alpaca