#!/bin/bash

# Production deployment script for Telegram Meeting-Scheduler Bot
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_ROOT}/.env.production"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if environment file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file $ENV_FILE not found"
        log_info "Please create the environment file with required variables"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Validate environment variables
validate_env() {
    log_info "Validating environment variables..."
    
    source "$ENV_FILE"
    
    required_vars=(
        "POSTGRES_PASSWORD"
        "TELEGRAM_BOT_TOKEN"
        "GOOGLE_CLIENT_ID"
        "GOOGLE_CLIENT_SECRET"
        "GOOGLE_REDIRECT_URI"
        "ENCRYPTION_KEY"
        "SECRET_KEY"
        "SESSION_SECRET_KEY"
        "OAUTH_TOKEN_ENCRYPTION_KEY"
        "GRAFANA_ADMIN_PASSWORD"
        "GRAFANA_SECRET_KEY"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        printf '  - %s\n' "${missing_vars[@]}"
        exit 1
    fi
    
    log_success "Environment validation passed"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    directories=(
        "$PROJECT_ROOT/docker/ssl"
        "$PROJECT_ROOT/docker/nginx/logs"
        "$PROJECT_ROOT/data/postgres"
        "$PROJECT_ROOT/data/redis"
        "$PROJECT_ROOT/data/logs"
        "$PROJECT_ROOT/backups"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
    
    log_success "Directories created"
}

# Generate SSL certificates (self-signed for development)
generate_ssl_certs() {
    log_info "Generating SSL certificates..."
    
    ssl_dir="$PROJECT_ROOT/docker/ssl"
    
    # Check if certificates already exist
    if [[ -f "$ssl_dir/yourdomain.com.crt" && -f "$ssl_dir/yourdomain.com.key" ]]; then
        log_warning "SSL certificates already exist, skipping generation"
        return
    fi
    
    # Generate self-signed certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$ssl_dir/yourdomain.com.key" \
        -out "$ssl_dir/yourdomain.com.crt" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=yourdomain.com"
    
    # Copy for subdomains
    cp "$ssl_dir/yourdomain.com.crt" "$ssl_dir/api.yourdomain.com.crt"
    cp "$ssl_dir/yourdomain.com.key" "$ssl_dir/api.yourdomain.com.key"
    cp "$ssl_dir/yourdomain.com.crt" "$ssl_dir/bot.yourdomain.com.crt"
    cp "$ssl_dir/yourdomain.com.key" "$ssl_dir/bot.yourdomain.com.key"
    cp "$ssl_dir/yourdomain.com.crt" "$ssl_dir/grafana.yourdomain.com.crt"
    cp "$ssl_dir/yourdomain.com.key" "$ssl_dir/grafana.yourdomain.com.key"
    
    log_success "SSL certificates generated"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Build images
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    log_success "Docker images built"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    cd "$PROJECT_ROOT"
    
    # Start only database services
    docker-compose -f "$COMPOSE_FILE" up -d postgres redis
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    sleep 10
    
    # Run migrations
    docker-compose -f "$COMPOSE_FILE" run --rm api alembic upgrade head
    
    log_success "Database migrations completed"
}

# Deploy services
deploy_services() {
    log_info "Deploying services..."
    
    cd "$PROJECT_ROOT"
    
    # Start all services
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_success "Services deployed"
}

# Wait for services to be healthy
wait_for_services() {
    log_info "Waiting for services to be healthy..."
    
    services=("api" "bot" "worker" "beat" "nginx" "prometheus" "grafana")
    
    for service in "${services[@]}"; do
        log_info "Waiting for $service to be healthy..."
        
        # Wait up to 5 minutes for service to be healthy
        timeout=300
        while [[ $timeout -gt 0 ]]; do
            if docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "healthy\|Up"; then
                log_success "$service is healthy"
                break
            fi
            
            sleep 5
            timeout=$((timeout - 5))
        done
        
        if [[ $timeout -le 0 ]]; then
            log_error "$service failed to become healthy"
            docker-compose -f "$COMPOSE_FILE" logs "$service"
            exit 1
        fi
    done
    
    log_success "All services are healthy"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check if services are running
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" ps
    
    # Test API health endpoint
    log_info "Testing API health endpoint..."
    if curl -f -s http://localhost/health > /dev/null; then
        log_success "API health check passed"
    else
        log_error "API health check failed"
        exit 1
    fi
    
    # Test bot health endpoint
    log_info "Testing bot health endpoint..."
    if curl -f -s http://localhost:8080/health > /dev/null; then
        log_success "Bot health check passed"
    else
        log_warning "Bot health check failed (may be expected if webhook is not set up)"
    fi
    
    log_success "Deployment verification completed"
}

# Display deployment information
show_deployment_info() {
    log_info "Deployment Information:"
    echo ""
    echo "Services:"
    echo "  - API: https://api.yourdomain.com"
    echo "  - Bot: https://bot.yourdomain.com"
    echo "  - Grafana: https://grafana.yourdomain.com (restricted access)"
    echo ""
    echo "Monitoring:"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana: http://localhost:3000"
    echo "  - Alertmanager: http://localhost:9093"
    echo ""
    echo "Logs:"
    echo "  - View logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "  - View specific service: docker-compose -f $COMPOSE_FILE logs -f <service>"
    echo ""
    echo "Management:"
    echo "  - Stop services: docker-compose -f $COMPOSE_FILE down"
    echo "  - Restart services: docker-compose -f $COMPOSE_FILE restart"
    echo "  - Update services: ./scripts/deploy.sh"
    echo ""
}

# Main deployment function
main() {
    log_info "Starting deployment of Telegram Meeting-Scheduler Bot..."
    
    check_root
    check_prerequisites
    validate_env
    create_directories
    generate_ssl_certs
    build_images
    run_migrations
    deploy_services
    wait_for_services
    verify_deployment
    show_deployment_info
    
    log_success "Deployment completed successfully!"
}

# Handle script arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    stop)
        log_info "Stopping services..."
        cd "$PROJECT_ROOT"
        docker-compose -f "$COMPOSE_FILE" down
        log_success "Services stopped"
        ;;
    restart)
        log_info "Restarting services..."
        cd "$PROJECT_ROOT"
        docker-compose -f "$COMPOSE_FILE" restart
        log_success "Services restarted"
        ;;
    logs)
        service="${2:-}"
        if [[ -n "$service" ]]; then
            log_info "Showing logs for $service..."
            cd "$PROJECT_ROOT"
            docker-compose -f "$COMPOSE_FILE" logs -f "$service"
        else
            log_info "Showing logs for all services..."
            cd "$PROJECT_ROOT"
            docker-compose -f "$COMPOSE_FILE" logs -f
        fi
        ;;
    status)
        log_info "Service status:"
        cd "$PROJECT_ROOT"
        docker-compose -f "$COMPOSE_FILE" ps
        ;;
    backup)
        log_info "Creating database backup..."
        cd "$PROJECT_ROOT"
        timestamp=$(date +%Y%m%d_%H%M%S)
        docker-compose -f "$COMPOSE_FILE" exec postgres pg_dump -U tg_bot_user tg_bot_prod > "backups/db_backup_$timestamp.sql"
        log_success "Database backup created: backups/db_backup_$timestamp.sql"
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|logs|status|backup}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Deploy the application (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - Show logs for all services"
        echo "  logs <service> - Show logs for specific service"
        echo "  status  - Show service status"
        echo "  backup  - Create database backup"
        exit 1
        ;;
esac
