# Financial Portfolio Automation System - Installation Guide

This guide provides step-by-step instructions for installing and setting up the Financial Portfolio Automation System in different environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Development Installation](#development-installation)
4. [Production Installation](#production-installation)
5. [Configuration](#configuration)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS (10.15+), or Windows 10+
- **Memory**: Minimum 4GB RAM, Recommended 8GB+
- **Storage**: Minimum 10GB free space
- **Network**: Internet connection for API access and package downloads

### Required Software

1. **Docker** (20.10+)
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   
   # macOS
   # Download Docker Desktop from https://www.docker.com/products/docker-desktop
   
   # Windows
   # Download Docker Desktop from https://www.docker.com/products/docker-desktop
   ```

2. **Docker Compose** (2.0+)
   ```bash
   # Usually included with Docker Desktop
   # For Linux, install separately:
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

3. **Python** (3.8+)
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3 python3-pip python3-venv
   
   # macOS
   brew install python3
   
   # Windows
   # Download from https://www.python.org/downloads/
   ```

4. **Git**
   ```bash
   # Ubuntu/Debian
   sudo apt install git
   
   # macOS
   brew install git
   
   # Windows
   # Download from https://git-scm.com/download/win
   ```

### Optional Tools

- **Make** (for using Makefile commands)
- **curl** (for API testing)
- **jq** (for JSON processing)

## Quick Start

For a rapid development setup:

```bash
# Clone the repository
git clone https://github.com/your-org/financial-portfolio-automation.git
cd financial-portfolio-automation

# Run the setup script
chmod +x deployment/scripts/setup.sh
./deployment/scripts/setup.sh

# Edit configuration
nano .env  # Set your Alpaca API credentials

# Start the system
docker-compose up -d
```

## Development Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/financial-portfolio-automation.git
cd financial-portfolio-automation
```

### Step 2: Run Setup Script

```bash
chmod +x deployment/scripts/setup.sh
./deployment/scripts/setup.sh
```

The setup script will:
- Check system requirements
- Create directory structure
- Generate configuration files
- Install Python dependencies
- Initialize the database
- Set up monitoring
- Create SSL certificates (self-signed for development)

### Step 3: Configure Environment

Edit the `.env` file with your settings:

```bash
nano .env
```

**Required Settings:**
```env
# Alpaca API Configuration (REQUIRED)
ALPACA_API_KEY=your_actual_api_key_here
ALPACA_SECRET_KEY=your_actual_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Database passwords (auto-generated)
POSTGRES_PASSWORD=generated_password
REDIS_PASSWORD=generated_password

# JWT Secret (auto-generated)
JWT_SECRET_KEY=generated_secret
```

### Step 4: Start Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 5: Verify Installation

```bash
# Run health check
python scripts/system_health_check.py

# Test API
curl http://localhost:8000/api/v1/system/health

# Test CLI
python -m financial_portfolio_automation.cli.main --help
```

## Production Installation

### Step 1: Prepare Production Environment

```bash
# Clone repository
git clone https://github.com/your-org/financial-portfolio-automation.git
cd financial-portfolio-automation

# Create production environment file
cp .env.example .env.production
```

### Step 2: Configure Production Settings

Edit `.env.production`:

```env
# Environment
ENVIRONMENT=production

# Database (use external database for production)
DATABASE_URL=postgresql://user:password@db-host:5432/portfolio_automation

# Redis (use external Redis for production)
REDIS_URL=redis://:password@redis-host:6379/0

# Alpaca API (use live API for production)
ALPACA_API_KEY=your_live_api_key
ALPACA_SECRET_KEY=your_live_secret_key
ALPACA_BASE_URL=https://api.alpaca.markets

# Security
JWT_SECRET_KEY=your_strong_jwt_secret_key

# Monitoring
SENTRY_DSN=your_sentry_dsn
GRAFANA_PASSWORD=your_grafana_password

# SSL (use real certificates)
SSL_CERT_PATH=/path/to/ssl/cert.pem
SSL_KEY_PATH=/path/to/ssl/private.key
```

### Step 3: Set Up SSL Certificates

For production, use proper SSL certificates:

```bash
# Using Let's Encrypt (recommended)
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem config/ssl/server.crt
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem config/ssl/server.key
sudo chown $USER:$USER config/ssl/server.*
chmod 600 config/ssl/server.key
```

### Step 4: Deploy Production

```bash
# Deploy using production configuration
./deployment/scripts/deploy.sh production

# Or manually:
cd deployment/docker
docker-compose -f docker-compose.prod.yml up -d
```

### Step 5: Set Up Monitoring

Access monitoring dashboards:
- **Grafana**: http://your-domain:3000
- **Prometheus**: http://your-domain:9090

Import pre-configured dashboards from `deployment/docker/grafana/dashboards/`.

### Step 6: Set Up Backup

```bash
# Create backup script
sudo crontab -e

# Add backup job (daily at 2 AM)
0 2 * * * /path/to/financial-portfolio-automation/scripts/backup.sh
```

## Configuration

### Application Configuration

Edit `config/config.json`:

```json
{
    "database": {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30
    },
    "cache": {
        "default_ttl": 300,
        "max_connections": 10
    },
    "risk_management": {
        "max_position_size": 10000,
        "max_portfolio_concentration": 0.2,
        "max_daily_loss": 1000,
        "max_drawdown": 0.1,
        "stop_loss_percentage": 0.05
    },
    "notifications": {
        "email": {
            "enabled": true,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "your-email@gmail.com",
            "password": "your-app-password"
        }
    }
}
```

### Environment-Specific Configuration

Create environment-specific configs:

```bash
# Development
config/environments/development.yaml

# Staging
config/environments/staging.yaml

# Production
config/environments/production.yaml
```

### Logging Configuration

Configure logging in `config/logging.yaml`:

```yaml
version: 1
formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    formatter: default
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/application.log
    maxBytes: 10485760
    backupCount: 5
    formatter: default
loggers:
  financial_portfolio_automation:
    level: INFO
    handlers: [console, file]
root:
  level: WARNING
  handlers: [console]
```

## Verification

### Health Checks

```bash
# System health check
python scripts/system_health_check.py

# API health check
curl http://localhost:8000/api/v1/system/health

# Database check
docker-compose exec postgres pg_isready -U portfolio_user

# Redis check
docker-compose exec redis redis-cli ping
```

### Functional Tests

```bash
# Run integration tests
python -m pytest tests/integration/ -v

# Test CLI functionality
python -m financial_portfolio_automation.cli.main portfolio status

# Test API endpoints
curl -X GET http://localhost:8000/api/v1/portfolio/account \
  -H "Authorization: Bearer your-jwt-token"
```

### Performance Tests

```bash
# Run performance tests
python -m pytest tests/performance/ -v

# Load testing (if available)
ab -n 1000 -c 10 http://localhost:8000/api/v1/system/health
```

## Troubleshooting

### Common Issues

#### 1. Docker Permission Issues

```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and log back in
```

#### 2. Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :8000

# Stop conflicting service or change port in docker-compose.yml
```

#### 3. Database Connection Issues

```bash
# Check database logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
python scripts/init_database.py
```

#### 4. API Not Responding

```bash
# Check API logs
docker-compose logs api

# Restart API service
docker-compose restart api

# Check health endpoint
curl -v http://localhost:8000/api/v1/system/health
```

#### 5. SSL Certificate Issues

```bash
# Regenerate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout config/ssl/server.key \
  -out config/ssl/server.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### Log Locations

- **Application Logs**: `logs/`
- **Docker Logs**: `docker-compose logs [service]`
- **System Logs**: `/var/log/` (Linux)
- **Database Logs**: `docker-compose logs postgres`

### Getting Help

1. **Check Documentation**: Review all documentation in `docs/`
2. **Check Issues**: Look for similar issues in the project repository
3. **Run Diagnostics**: Use `python scripts/system_health_check.py`
4. **Enable Debug Logging**: Set `LOG_LEVEL=DEBUG` in `.env`
5. **Contact Support**: Create an issue in the project repository

### Useful Commands

```bash
# View all containers
docker-compose ps

# View logs for specific service
docker-compose logs -f api

# Execute command in container
docker-compose exec api bash

# Restart specific service
docker-compose restart api

# Update and restart all services
docker-compose pull && docker-compose up -d

# Clean up unused resources
docker system prune -a

# Backup database
docker-compose exec postgres pg_dump -U portfolio_user portfolio_automation > backup.sql

# Restore database
docker-compose exec -T postgres psql -U portfolio_user portfolio_automation < backup.sql
```

## Next Steps

After successful installation:

1. **Configure Strategies**: Set up your trading strategies in the web interface
2. **Set Up Notifications**: Configure email/SMS notifications
3. **Import Data**: Import historical data for backtesting
4. **Monitor System**: Set up monitoring and alerting
5. **Schedule Backups**: Set up automated backups
6. **Review Security**: Review and harden security settings

For detailed usage instructions, see the [User Guide](../user/user_guide.md).
For API documentation, see the [API Reference](../api/api_reference.md).