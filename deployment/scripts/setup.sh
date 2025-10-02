#!/bin/bash

# Financial Portfolio Automation System Setup Script
# This script sets up the complete system environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is not installed. Please install Python 3.8+ first."
        exit 1
    fi
    
    # Check Python version
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ $(echo "$python_version < 3.8" | bc -l) -eq 1 ]]; then
        error "Python 3.8+ is required. Current version: $python_version"
        exit 1
    fi
    
    success "All system requirements met"
}

# Create directory structure
create_directories() {
    log "Creating directory structure..."
    
    # Create main directories
    mkdir -p data/{database,cache,logs,reports,backups}
    mkdir -p config/{environments,validation,ssl}
    mkdir -p scripts/{maintenance,monitoring}
    mkdir -p docs/{deployment,api,user}
    
    # Create log directories
    mkdir -p logs/{api,cli,system,audit}
    
    # Create backup directories
    mkdir -p backups/{database,config,reports}
    
    # Set permissions
    chmod 755 data config scripts docs logs backups
    chmod 700 config/ssl backups
    
    success "Directory structure created"
}

# Generate configuration files
generate_config() {
    log "Generating configuration files..."
    
    # Generate environment file if it doesn't exist
    if [[ ! -f .env ]]; then
        log "Creating .env file..."
        cat > .env << EOF
# Financial Portfolio Automation Environment Configuration

# Database Configuration
POSTGRES_DB=portfolio_automation
POSTGRES_USER=portfolio_user
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Redis Configuration
REDIS_PASSWORD=$(openssl rand -base64 32)

# Alpaca API Configuration (REQUIRED - Set your actual values)
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# JWT Configuration
JWT_SECRET_KEY=$(openssl rand -base64 64)

# Monitoring Configuration
GRAFANA_PASSWORD=$(openssl rand -base64 16)
SENTRY_DSN=your_sentry_dsn_here

# System Configuration
LOG_LEVEL=INFO
ENVIRONMENT=development
EOF
        warning "Please edit .env file and set your Alpaca API credentials"
    fi
    
    # Generate application config
    if [[ ! -f config/config.json ]]; then
        log "Creating application configuration..."
        cat > config/config.json << EOF
{
    "database": {
        "url": "postgresql://portfolio_user:password@localhost:5432/portfolio_automation",
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30
    },
    "cache": {
        "url": "redis://localhost:6379/0",
        "default_ttl": 300,
        "max_connections": 10
    },
    "alpaca": {
        "api_key": "",
        "secret_key": "",
        "base_url": "https://paper-api.alpaca.markets",
        "data_feed": "iex"
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
            "enabled": false,
            "smtp_server": "",
            "smtp_port": 587,
            "username": "",
            "password": ""
        },
        "sms": {
            "enabled": false,
            "provider": "twilio",
            "account_sid": "",
            "auth_token": "",
            "from_number": ""
        },
        "webhook": {
            "enabled": false,
            "url": "",
            "secret": ""
        }
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file_rotation": {
            "max_bytes": 10485760,
            "backup_count": 5
        }
    }
}
EOF
    fi
    
    success "Configuration files generated"
}

# Install Python dependencies
install_dependencies() {
    log "Installing Python dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d venv ]]; then
        log "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    if [[ -f requirements.txt ]]; then
        pip install -r requirements.txt
    else
        error "requirements.txt not found"
        exit 1
    fi
    
    success "Python dependencies installed"
}

# Initialize database
init_database() {
    log "Initializing database..."
    
    # Start database container if not running
    if ! docker ps | grep -q portfolio-postgres; then
        log "Starting PostgreSQL container..."
        docker-compose up -d postgres
        
        # Wait for database to be ready
        log "Waiting for database to be ready..."
        sleep 10
        
        # Check database health
        max_attempts=30
        attempt=1
        while [[ $attempt -le $max_attempts ]]; do
            if docker-compose exec postgres pg_isready -U portfolio_user -d portfolio_automation; then
                break
            fi
            log "Database not ready, waiting... (attempt $attempt/$max_attempts)"
            sleep 2
            ((attempt++))
        done
        
        if [[ $attempt -gt $max_attempts ]]; then
            error "Database failed to start within expected time"
            exit 1
        fi
    fi
    
    # Run database migrations
    log "Running database migrations..."
    source venv/bin/activate
    python scripts/init_database.py
    
    success "Database initialized"
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create Prometheus configuration
    if [[ ! -f deployment/docker/prometheus.yml ]]; then
        cat > deployment/docker/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'portfolio-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/api/v1/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
EOF
    fi
    
    # Create Grafana datasource configuration
    mkdir -p deployment/docker/grafana/datasources
    if [[ ! -f deployment/docker/grafana/datasources/prometheus.yml ]]; then
        cat > deployment/docker/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF
    fi
    
    success "Monitoring configuration created"
}

# Setup SSL certificates (self-signed for development)
setup_ssl() {
    log "Setting up SSL certificates..."
    
    if [[ ! -f config/ssl/server.crt ]]; then
        log "Generating self-signed SSL certificate..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout config/ssl/server.key \
            -out config/ssl/server.crt \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        
        chmod 600 config/ssl/server.key
        chmod 644 config/ssl/server.crt
        
        warning "Self-signed certificate generated. For production, use proper SSL certificates."
    fi
    
    success "SSL certificates configured"
}

# Create systemd service files
create_services() {
    log "Creating systemd service files..."
    
    # Create service file for the application
    cat > portfolio-automation.service << EOF
[Unit]
Description=Financial Portfolio Automation System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    log "To install the service, run:"
    log "sudo cp portfolio-automation.service /etc/systemd/system/"
    log "sudo systemctl daemon-reload"
    log "sudo systemctl enable portfolio-automation"
    
    success "Service files created"
}

# Run health checks
health_check() {
    log "Running health checks..."
    
    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        success "Containers are running"
    else
        warning "Some containers may not be running"
    fi
    
    # Check API health
    if curl -f http://localhost:8000/api/v1/system/health &> /dev/null; then
        success "API is healthy"
    else
        warning "API health check failed"
    fi
    
    # Check database connection
    if docker-compose exec postgres pg_isready -U portfolio_user -d portfolio_automation &> /dev/null; then
        success "Database is accessible"
    else
        warning "Database connection failed"
    fi
    
    # Check Redis connection
    if docker-compose exec redis redis-cli ping &> /dev/null; then
        success "Redis is accessible"
    else
        warning "Redis connection failed"
    fi
}

# Main setup function
main() {
    log "Starting Financial Portfolio Automation System setup..."
    
    check_root
    check_requirements
    create_directories
    generate_config
    install_dependencies
    init_database
    setup_monitoring
    setup_ssl
    create_services
    
    log "Starting services..."
    docker-compose up -d
    
    # Wait for services to start
    sleep 30
    
    health_check
    
    success "Setup completed successfully!"
    
    echo ""
    log "Next steps:"
    log "1. Edit .env file and set your Alpaca API credentials"
    log "2. Edit config/config.json to customize your settings"
    log "3. Access the API at: http://localhost:8000"
    log "4. Access Grafana at: http://localhost:3000 (admin/password from .env)"
    log "5. View logs with: docker-compose logs -f"
    echo ""
    log "For production deployment, use: ./deploy.sh production"
}

# Run main function
main "$@"