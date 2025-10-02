# Financial Portfolio Automation System - Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Financial Portfolio Automation System.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Common Issues](#common-issues)
3. [Service-Specific Issues](#service-specific-issues)
4. [Performance Issues](#performance-issues)
5. [Security Issues](#security-issues)
6. [Data Issues](#data-issues)
7. [Integration Issues](#integration-issues)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Recovery Procedures](#recovery-procedures)

## Quick Diagnostics

### System Health Check

Run the comprehensive health check first:

```bash
python scripts/system_health_check.py
```

This will check:
- System resources (CPU, memory, disk)
- Database connectivity
- Cache (Redis) connectivity
- API services
- External connections
- File system permissions
- Configuration
- Security settings

### Service Status Check

```bash
# Check all services
docker-compose ps

# Check specific service
docker-compose ps api

# Check service logs
docker-compose logs api
docker-compose logs postgres
docker-compose logs redis
```

### Quick Fixes

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart api

# Rebuild and restart
docker-compose up -d --build

# Clean restart (removes volumes)
docker-compose down -v
docker-compose up -d
```

## Common Issues

### 1. Services Won't Start

**Symptoms:**
- Containers exit immediately
- Services show as "Exited" status
- Error messages in logs

**Diagnosis:**
```bash
# Check container status
docker-compose ps

# Check logs for errors
docker-compose logs [service-name]

# Check system resources
docker system df
df -h
free -h
```

**Solutions:**

#### Port Conflicts
```bash
# Check what's using the port
sudo lsof -i :8000
sudo netstat -tulpn | grep :8000

# Solution: Change port in docker-compose.yml or stop conflicting service
sudo systemctl stop apache2  # Example: stop Apache
```

#### Insufficient Resources
```bash
# Check available resources
docker system df
df -h
free -h

# Clean up Docker resources
docker system prune -a
docker volume prune
```

#### Permission Issues
```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
# Log out and log back in

# Fix file permissions
sudo chown -R $USER:$USER .
chmod +x deployment/scripts/*.sh
```

### 2. Database Connection Issues

**Symptoms:**
- "Connection refused" errors
- "Database does not exist" errors
- Slow database responses

**Diagnosis:**
```bash
# Check PostgreSQL status
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres pg_isready -U portfolio_user -d portfolio_automation

# Check database exists
docker-compose exec postgres psql -U portfolio_user -l
```

**Solutions:**

#### Database Not Ready
```bash
# Wait for database to start
sleep 30

# Check if database is accepting connections
docker-compose exec postgres pg_isready -U portfolio_user

# Restart database service
docker-compose restart postgres
```

#### Database Doesn't Exist
```bash
# Create database
docker-compose exec postgres createdb -U portfolio_user portfolio_automation

# Run initialization script
python scripts/init_database.py
```

#### Connection Pool Issues
```bash
# Check active connections
docker-compose exec postgres psql -U portfolio_user -d portfolio_automation -c "SELECT count(*) FROM pg_stat_activity;"

# Restart API to reset connection pool
docker-compose restart api
```

### 3. API Service Issues

**Symptoms:**
- API returns 500 errors
- API not responding
- Slow API responses

**Diagnosis:**
```bash
# Check API status
curl -v http://localhost:8000/api/v1/system/health

# Check API logs
docker-compose logs api

# Check API container resources
docker stats portfolio-api
```

**Solutions:**

#### API Not Starting
```bash
# Check API logs for startup errors
docker-compose logs api

# Common issues:
# - Missing environment variables
# - Database connection issues
# - Port conflicts

# Restart API service
docker-compose restart api
```

#### High Memory Usage
```bash
# Check memory usage
docker stats portfolio-api

# Restart API to free memory
docker-compose restart api

# Increase memory limits in docker-compose.yml
```

#### Authentication Issues
```bash
# Check JWT configuration
grep JWT_SECRET_KEY .env

# Generate new JWT secret
openssl rand -base64 64

# Update .env file and restart
docker-compose restart api
```

### 4. Cache (Redis) Issues

**Symptoms:**
- Cache misses
- Slow performance
- Redis connection errors

**Diagnosis:**
```bash
# Check Redis status
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping

# Check Redis memory usage
docker-compose exec redis redis-cli info memory

# Check Redis logs
docker-compose logs redis
```

**Solutions:**

#### Redis Not Responding
```bash
# Restart Redis
docker-compose restart redis

# Check Redis configuration
docker-compose exec redis redis-cli config get "*"

# Clear Redis data if corrupted
docker-compose exec redis redis-cli flushall
```

#### Memory Issues
```bash
# Check Redis memory usage
docker-compose exec redis redis-cli info memory

# Set memory limit
docker-compose exec redis redis-cli config set maxmemory 1gb

# Configure eviction policy
docker-compose exec redis redis-cli config set maxmemory-policy allkeys-lru
```

## Service-Specific Issues

### Alpaca API Integration

**Symptoms:**
- Authentication failures
- Rate limiting errors
- Market data not updating

**Diagnosis:**
```bash
# Check API credentials
grep ALPACA .env

# Test API connection
curl -H "APCA-API-KEY-ID: $ALPACA_API_KEY" \
     -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY" \
     https://paper-api.alpaca.markets/v2/account
```

**Solutions:**

#### Authentication Issues
```bash
# Verify credentials are correct
# Check Alpaca dashboard for API key status
# Ensure using correct base URL (paper vs live)

# Update credentials in .env
ALPACA_API_KEY=your_correct_key
ALPACA_SECRET_KEY=your_correct_secret

# Restart services
docker-compose restart
```

#### Rate Limiting
```bash
# Check rate limit headers in logs
# Implement exponential backoff
# Reduce request frequency

# Monitor rate limits
grep "rate limit" logs/api.log
```

### WebSocket Issues

**Symptoms:**
- Real-time data not updating
- WebSocket connection drops
- High CPU usage

**Diagnosis:**
```bash
# Check WebSocket logs
docker-compose logs api | grep -i websocket

# Check connection status
curl http://localhost:8000/api/v1/system/websocket-status
```

**Solutions:**

#### Connection Drops
```bash
# Implement reconnection logic
# Check network stability
# Increase connection timeout

# Restart WebSocket service
docker-compose restart api
```

## Performance Issues

### Slow API Responses

**Diagnosis:**
```bash
# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/v1/system/health

# Check database query performance
docker-compose exec postgres psql -U portfolio_user -d portfolio_automation -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Check system resources
top
htop
docker stats
```

**Solutions:**

#### Database Optimization
```bash
# Analyze slow queries
docker-compose exec postgres psql -U portfolio_user -d portfolio_automation -c "SELECT query, total_time, calls FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Add missing indexes
# Optimize query patterns
# Consider connection pooling

# Restart database with optimized settings
docker-compose restart postgres
```

#### Cache Optimization
```bash
# Check cache hit rate
docker-compose exec redis redis-cli info stats | grep hit

# Increase cache TTL for stable data
# Implement cache warming
# Use cache clustering for high load

# Monitor cache performance
docker-compose exec redis redis-cli monitor
```

### High Memory Usage

**Diagnosis:**
```bash
# Check memory usage by service
docker stats

# Check system memory
free -h
cat /proc/meminfo

# Check for memory leaks
ps aux --sort=-%mem | head
```

**Solutions:**

#### Memory Leaks
```bash
# Restart services periodically
# Implement memory monitoring
# Profile application for leaks

# Set memory limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G
```

## Security Issues

### SSL/TLS Issues

**Symptoms:**
- Certificate errors
- HTTPS not working
- Browser security warnings

**Diagnosis:**
```bash
# Check certificate validity
openssl x509 -in config/ssl/server.crt -text -noout

# Test SSL connection
openssl s_client -connect localhost:443

# Check certificate expiration
openssl x509 -in config/ssl/server.crt -noout -dates
```

**Solutions:**

#### Certificate Renewal
```bash
# Renew Let's Encrypt certificate
sudo certbot renew

# Generate new self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout config/ssl/server.key \
  -out config/ssl/server.crt

# Restart services
docker-compose restart nginx
```

### Authentication Issues

**Symptoms:**
- Login failures
- Token validation errors
- Unauthorized access

**Diagnosis:**
```bash
# Check JWT configuration
grep JWT .env

# Validate JWT tokens
# Check user permissions
# Review authentication logs
```

**Solutions:**

#### JWT Issues
```bash
# Generate new JWT secret
openssl rand -base64 64

# Update .env file
JWT_SECRET_KEY=new_secret_key

# Restart API service
docker-compose restart api
```

## Data Issues

### Data Corruption

**Symptoms:**
- Invalid data in database
- Calculation errors
- Missing records

**Diagnosis:**
```bash
# Check database integrity
docker-compose exec postgres psql -U portfolio_user -d portfolio_automation -c "SELECT pg_database_size('portfolio_automation');"

# Validate data consistency
python scripts/validate_data.py

# Check for orphaned records
# Verify foreign key constraints
```

**Solutions:**

#### Database Repair
```bash
# Backup current data
docker-compose exec postgres pg_dump -U portfolio_user portfolio_automation > backup_$(date +%Y%m%d).sql

# Run data validation and repair
python scripts/repair_data.py

# Restore from backup if needed
docker-compose exec -T postgres psql -U portfolio_user portfolio_automation < backup_20240101.sql
```

### Missing Data

**Symptoms:**
- Gaps in historical data
- Missing quotes or trades
- Incomplete portfolio snapshots

**Diagnosis:**
```bash
# Check data completeness
python scripts/check_data_completeness.py

# Identify missing periods
# Check data source connectivity
# Review import logs
```

**Solutions:**

#### Data Recovery
```bash
# Re-import missing data
python scripts/import_historical_data.py --start-date 2024-01-01 --end-date 2024-01-31

# Validate imported data
python scripts/validate_imported_data.py

# Update derived calculations
python scripts/recalculate_metrics.py
```

## Integration Issues

### Third-Party API Issues

**Symptoms:**
- API calls failing
- Outdated data
- Service unavailable errors

**Diagnosis:**
```bash
# Test external API connectivity
curl -v https://paper-api.alpaca.markets/v2/account

# Check API status pages
# Review rate limiting
# Verify API credentials
```

**Solutions:**

#### API Connectivity
```bash
# Check network connectivity
ping api.alpaca.markets

# Test DNS resolution
nslookup api.alpaca.markets

# Check firewall rules
sudo ufw status

# Use alternative endpoints if available
```

### MCP Tool Issues

**Symptoms:**
- MCP tools not responding
- AI assistant integration failures
- Tool execution errors

**Diagnosis:**
```bash
# Check MCP server status
python -m financial_portfolio_automation.mcp.mcp_server --health-check

# Test individual tools
# Review MCP logs
# Validate tool permissions
```

**Solutions:**

#### MCP Server Restart
```bash
# Restart MCP server
docker-compose restart mcp-server

# Clear MCP cache
# Validate tool configurations
# Update tool permissions
```

## Monitoring and Logging

### Log Analysis

**Common Log Locations:**
```bash
# Application logs
tail -f logs/application.log

# Docker logs
docker-compose logs -f api

# System logs
sudo tail -f /var/log/syslog

# Database logs
docker-compose logs postgres
```

**Log Analysis Commands:**
```bash
# Find errors
grep -i error logs/application.log

# Find warnings
grep -i warning logs/application.log

# Count error types
grep -i error logs/application.log | cut -d' ' -f4- | sort | uniq -c | sort -nr

# Monitor real-time logs
tail -f logs/application.log | grep -i error
```

### Monitoring Setup

**Grafana Dashboards:**
```bash
# Access Grafana
http://localhost:3000

# Import dashboards
# Configure alerts
# Set up notifications
```

**Prometheus Metrics:**
```bash
# Access Prometheus
http://localhost:9090

# Check targets
# Query metrics
# Set up recording rules
```

## Recovery Procedures

### Database Recovery

**From Backup:**
```bash
# Stop services
docker-compose down

# Start only database
docker-compose up -d postgres

# Restore from backup
docker-compose exec -T postgres psql -U portfolio_user portfolio_automation < backup.sql

# Start all services
docker-compose up -d
```

**Point-in-Time Recovery:**
```bash
# Enable WAL archiving
# Configure continuous archiving
# Use pg_basebackup for base backups
# Restore to specific point in time
```

### System Recovery

**Complete System Restore:**
```bash
# Stop all services
docker-compose down -v

# Restore configuration
cp backup/config/* config/
cp backup/.env .env

# Restore data
docker-compose up -d postgres
docker-compose exec -T postgres psql -U portfolio_user portfolio_automation < backup/database.sql

# Start all services
docker-compose up -d

# Verify system health
python scripts/system_health_check.py
```

### Disaster Recovery

**Backup Strategy:**
```bash
# Daily automated backups
0 2 * * * /path/to/backup_script.sh

# Weekly full system backup
0 3 * * 0 /path/to/full_backup_script.sh

# Monthly offsite backup
0 4 1 * * /path/to/offsite_backup_script.sh
```

**Recovery Testing:**
```bash
# Regular recovery tests
# Document recovery procedures
# Train team on recovery process
# Test backup integrity
```

## Getting Help

### Support Channels

1. **Documentation**: Check all documentation in `docs/`
2. **Health Check**: Run `python scripts/system_health_check.py`
3. **Logs**: Review application and system logs
4. **Community**: Check project issues and discussions
5. **Professional Support**: Contact system administrators

### Information to Provide

When seeking help, provide:

1. **System Information:**
   ```bash
   uname -a
   docker --version
   docker-compose --version
   python --version
   ```

2. **Health Check Results:**
   ```bash
   python scripts/system_health_check.py --format json > health_check.json
   ```

3. **Service Status:**
   ```bash
   docker-compose ps > service_status.txt
   ```

4. **Recent Logs:**
   ```bash
   docker-compose logs --tail=100 > recent_logs.txt
   ```

5. **Configuration (sanitized):**
   ```bash
   # Remove sensitive information before sharing
   cat .env | sed 's/=.*/=***/' > config_sanitized.txt
   ```

### Emergency Contacts

- **System Administrator**: [contact information]
- **Database Administrator**: [contact information]
- **Security Team**: [contact information]
- **On-Call Support**: [contact information]

Remember to follow your organization's incident response procedures for critical issues.