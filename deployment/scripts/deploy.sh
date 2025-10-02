#!/bin/bash

# Financial Portfolio Automation System Deployment Script
# Supports development, staging, and production deployments

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
COMPOSE_FILE="docker-compose.yml"
BACKUP_BEFORE_DEPLOY=true
SKIP_HEALTH_CHECK=false

# Logging functions
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

# Show usage information
usage() {
    cat << EOF
Usage: $0 [ENVIRONMENT] [OPTIONS]

ENVIRONMENT:
    development     Deploy for development (default)
    staging         Deploy for staging
    production      Deploy for production

OPTIONS:
    --no-backup     Skip backup before deployment
    --skip-health   Skip health checks after deployment
    --help          Show this help message

Examples:
    $0                          # Deploy development environment
    $0 production               # Deploy production environment
    $0 staging --no-backup      # Deploy staging without backup
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            development|staging|production)
                ENVIRONMENT="$1"
                shift
                ;;
            --no-backup)
                BACKUP_BEFORE_DEPLOY=false
                shift
                ;;
            --skip-health)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Set compose file based on environment
    case $ENVIRONMENT in
        production)
            COMPOSE_FILE="docker-compose.prod.yml"
            ;;
        staging)
            COMPOSE_FILE="docker-compose.staging.yml"
            ;;
        *)
            COMPOSE_FILE="docker-compose.yml"
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites for $ENVIRONMENT deployment..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if compose file exists
    if [[ ! -f "deployment/docker/$COMPOSE_FILE" ]]; then
        error "Compose file not found: deployment/docker/$COMPOSE_FILE"
        exit 1
    fi
    
    # Check environment file
    if [[ ! -f .env ]]; then
        error ".env file not found. Run setup.sh first."
        exit 1
    fi
    
    # Check for production-specific requirements
    if [[ "$ENVIRONMENT" == "production" ]]; then
        # Check for SSL certificates
        if [[ ! -f config/ssl/server.crt ]] || [[ ! -f config/ssl/server.key ]]; then
            error "SSL certificates not found. Required for production deployment."
            exit 1
        fi
        
        # Check for required environment variables
        source .env
        if [[ -z "$ALPACA_API_KEY" ]] || [[ "$ALPACA_API_KEY" == "your_alpaca_api_key_here" ]]; then
            error "ALPACA_API_KEY not set in .env file"
            exit 1
        fi
        
        if [[ -z "$ALPACA_SECRET_KEY" ]] || [[ "$ALPACA_SECRET_KEY" == "your_alpaca_secret_key_here" ]]; then
            error "ALPACA_SECRET_KEY not set in .env file"
            exit 1
        fi
    fi
    
    success "Prerequisites check passed"
}

# Create backup
create_backup() {
    if [[ "$BACKUP_BEFORE_DEPLOY" == "false" ]]; then
        log "Skipping backup as requested"
        return
    fi
    
    log "Creating backup before deployment..."
    
    BACKUP_DIR="backups/$(date +'%Y%m%d_%H%M%S')"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database if running
    if docker ps | grep -q portfolio-postgres; then
        log "Backing up database..."
        docker-compose exec -T postgres pg_dump -U portfolio_user portfolio_automation > "$BACKUP_DIR/database.sql"
        success "Database backup created: $BACKUP_DIR/database.sql"
    fi
    
    # Backup configuration
    log "Backing up configuration..."
    cp -r config "$BACKUP_DIR/"
    cp .env "$BACKUP_DIR/"
    
    # Backup logs if they exist
    if [[ -d logs ]]; then
        log "Backing up logs..."
        cp -r logs "$BACKUP_DIR/"
    fi
    
    success "Backup created in $BACKUP_DIR"
}

# Build images
build_images() {
    log "Building Docker images for $ENVIRONMENT..."
    
    cd deployment/docker
    
    # Build API image
    log "Building API image..."
    docker build -f Dockerfile.api -t portfolio-automation-api:latest ../..
    
    # Build CLI image
    log "Building CLI image..."
    docker build -f Dockerfile.cli -t portfolio-automation-cli:latest ../..
    
    cd ../..
    
    success "Docker images built successfully"
}

# Deploy services
deploy_services() {
    log "Deploying services for $ENVIRONMENT environment..."
    
    cd deployment/docker
    
    # Stop existing services
    log "Stopping existing services..."
    docker-compose -f "$COMPOSE_FILE" down
    
    # Pull latest images for external services
    log "Pulling latest images..."
    docker-compose -f "$COMPOSE_FILE" pull postgres redis nginx prometheus grafana
    
    # Start services
    log "Starting services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    cd ../..
    
    success "Services deployed"
}

# Wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."
    
    # Wait for database
    log "Waiting for database..."
    max_attempts=60
    attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "deployment/docker/$COMPOSE_FILE" exec postgres pg_isready -U portfolio_user -d portfolio_automation &> /dev/null; then
            success "Database is ready"
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
    
    # Wait for Redis
    log "Waiting for Redis..."
    attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "deployment/docker/$COMPOSE_FILE" exec redis redis-cli ping &> /dev/null; then
            success "Redis is ready"
            break
        fi
        log "Redis not ready, waiting... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        error "Redis failed to start within expected time"
        exit 1
    fi
    
    # Wait for API
    log "Waiting for API..."
    attempt=1
    api_port=8000
    if [[ "$ENVIRONMENT" == "production" ]]; then
        api_port=80
    fi
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f "http://localhost:$api_port/api/v1/system/health" &> /dev/null; then
            success "API is ready"
            break
        fi
        log "API not ready, waiting... (attempt $attempt/$max_attempts)"
        sleep 3
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        error "API failed to start within expected time"
        exit 1
    fi
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Activate virtual environment if it exists
    if [[ -d venv ]]; then
        source venv/bin/activate
    fi
    
    # Run migrations
    python scripts/migrate_database.py
    
    success "Database migrations completed"
}

# Health checks
health_check() {
    if [[ "$SKIP_HEALTH_CHECK" == "true" ]]; then
        log "Skipping health checks as requested"
        return
    fi
    
    log "Running health checks..."
    
    # Check container status
    log "Checking container status..."
    cd deployment/docker
    containers=$(docker-compose -f "$COMPOSE_FILE" ps --services)
    failed_containers=()
    
    for container in $containers; do
        if ! docker-compose -f "$COMPOSE_FILE" ps "$container" | grep -q "Up"; then
            failed_containers+=("$container")
        fi
    done
    
    if [[ ${#failed_containers[@]} -gt 0 ]]; then
        error "Failed containers: ${failed_containers[*]}"
        exit 1
    fi
    
    cd ../..
    
    # Check API endpoints
    log "Checking API endpoints..."
    api_port=8000
    if [[ "$ENVIRONMENT" == "production" ]]; then
        api_port=80
    fi
    
    endpoints=(
        "/api/v1/system/health"
        "/api/v1/system/info"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if ! curl -f "http://localhost:$api_port$endpoint" &> /dev/null; then
            error "API endpoint check failed: $endpoint"
            exit 1
        fi
    done
    
    # Check database connectivity
    log "Checking database connectivity..."
    if ! docker-compose -f "deployment/docker/$COMPOSE_FILE" exec postgres pg_isready -U portfolio_user -d portfolio_automation &> /dev/null; then
        error "Database connectivity check failed"
        exit 1
    fi
    
    # Check Redis connectivity
    log "Checking Redis connectivity..."
    if ! docker-compose -f "deployment/docker/$COMPOSE_FILE" exec redis redis-cli ping &> /dev/null; then
        error "Redis connectivity check failed"
        exit 1
    fi
    
    success "All health checks passed"
}

# Show deployment summary
show_summary() {
    log "Deployment Summary"
    echo "=================="
    echo "Environment: $ENVIRONMENT"
    echo "Compose File: $COMPOSE_FILE"
    echo "Backup Created: $BACKUP_BEFORE_DEPLOY"
    echo ""
    
    # Show running containers
    log "Running containers:"
    cd deployment/docker
    docker-compose -f "$COMPOSE_FILE" ps
    cd ../..
    
    echo ""
    
    # Show access URLs
    case $ENVIRONMENT in
        production)
            log "Access URLs:"
            echo "API: https://localhost/api/v1/"
            echo "Grafana: http://localhost:3000"
            echo "Prometheus: http://localhost:9090"
            ;;
        *)
            log "Access URLs:"
            echo "API: http://localhost:8000/api/v1/"
            echo "Grafana: http://localhost:3000"
            echo "Prometheus: http://localhost:9090"
            ;;
    esac
    
    echo ""
    log "Useful commands:"
    echo "View logs: docker-compose -f deployment/docker/$COMPOSE_FILE logs -f"
    echo "Stop services: docker-compose -f deployment/docker/$COMPOSE_FILE down"
    echo "Restart services: docker-compose -f deployment/docker/$COMPOSE_FILE restart"
}

# Cleanup on exit
cleanup() {
    if [[ $? -ne 0 ]]; then
        error "Deployment failed!"
        log "Check logs with: docker-compose -f deployment/docker/$COMPOSE_FILE logs"
    fi
}

trap cleanup EXIT

# Main deployment function
main() {
    log "Starting deployment of Financial Portfolio Automation System..."
    
    parse_args "$@"
    check_prerequisites
    create_backup
    build_images
    deploy_services
    wait_for_services
    run_migrations
    health_check
    show_summary
    
    success "Deployment completed successfully!"
}

# Run main function
main "$@"