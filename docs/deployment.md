# Deployment Guide

## Overview

This guide covers deployment strategies for the Ticket Analysis CLI tool across different environments, from development to production. The tool is designed to be deployed as a Python package with secure configuration management and monitoring capabilities.

## Prerequisites

### System Requirements

- **Python**: 3.7 or higher
- **Node.js**: 16 or higher (for MCP components)
- **Operating System**: macOS, Linux, or Windows
- **Memory**: Minimum 512MB RAM, recommended 2GB for large datasets
- **Storage**: 100MB for application, additional space for reports and logs
- **Network**: Access to Amazon internal network for MCP integration

### Security Requirements

- Valid Midway credentials for authentication
- Access to Amazon's internal ticketing systems
- Proper network security groups and firewall rules
- Secure credential storage and management

## Development Environment

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/org/ticket-analyzer.git
cd ticket-analyzer

# Create virtual environment
python3.7 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install in development mode
pip install -e .

# Verify installation
ticket-analyzer --version
```

### Development Configuration

Create a development configuration file:

```bash
# Create config directory
mkdir -p ~/.ticket-analyzer

# Create development config
cat > ~/.ticket-analyzer/config.json << EOF
{
  "authentication": {
    "timeout_seconds": 60,
    "max_retry_attempts": 3,
    "check_interval_seconds": 300
  },
  "output": {
    "default_format": "table",
    "max_results": 100,
    "sanitize_output": true
  },
  "logging": {
    "level": "DEBUG",
    "sanitize_logs": true,
    "log_file": "~/.ticket-analyzer/logs/debug.log"
  },
  "mcp": {
    "timeout_seconds": 30,
    "retry_attempts": 3,
    "circuit_breaker_threshold": 5
  }
}
EOF

# Set secure permissions
chmod 600 ~/.ticket-analyzer/config.json
```

## Staging Environment

### Staging Deployment

The staging environment should mirror production as closely as possible while providing a safe testing environment.

```bash
# Staging deployment script
#!/bin/bash
set -e

STAGING_DIR="/opt/ticket-analyzer-staging"
VENV_DIR="$STAGING_DIR/venv"
CONFIG_DIR="/etc/ticket-analyzer-staging"

# Create staging directory
sudo mkdir -p $STAGING_DIR
sudo mkdir -p $CONFIG_DIR
sudo mkdir -p /var/log/ticket-analyzer-staging

# Create virtual environment
sudo python3.7 -m venv $VENV_DIR
sudo $VENV_DIR/bin/pip install --upgrade pip

# Install application
sudo $VENV_DIR/bin/pip install ticket-analyzer==1.0.0

# Create staging configuration
sudo tee $CONFIG_DIR/config.json > /dev/null << EOF
{
  "authentication": {
    "timeout_seconds": 60,
    "max_retry_attempts": 3,
    "check_interval_seconds": 300
  },
  "output": {
    "default_format": "json",
    "max_results": 1000,
    "sanitize_output": true,
    "output_directory": "/var/lib/ticket-analyzer-staging/reports"
  },
  "logging": {
    "level": "INFO",
    "sanitize_logs": true,
    "log_file": "/var/log/ticket-analyzer-staging/app.log",
    "max_log_size": "10MB",
    "backup_count": 5
  },
  "mcp": {
    "timeout_seconds": 30,
    "retry_attempts": 3,
    "circuit_breaker_threshold": 5
  }
}
EOF

# Set secure permissions
sudo chmod 600 $CONFIG_DIR/config.json
sudo chown -R ticket-analyzer:ticket-analyzer $STAGING_DIR
sudo chown -R ticket-analyzer:ticket-analyzer /var/log/ticket-analyzer-staging
```

### Staging Validation

```bash
# Validation script for staging deployment
#!/bin/bash

echo "Validating staging deployment..."

# Check application installation
if ! /opt/ticket-analyzer-staging/venv/bin/ticket-analyzer --version; then
    echo "ERROR: Application not properly installed"
    exit 1
fi

# Check configuration
if [ ! -f /etc/ticket-analyzer-staging/config.json ]; then
    echo "ERROR: Configuration file missing"
    exit 1
fi

# Check permissions
CONFIG_PERMS=$(stat -c "%a" /etc/ticket-analyzer-staging/config.json)
if [ "$CONFIG_PERMS" != "600" ]; then
    echo "ERROR: Configuration file permissions incorrect"
    exit 1
fi

# Test basic functionality
if ! /opt/ticket-analyzer-staging/venv/bin/ticket-analyzer analyze --help > /dev/null; then
    echo "ERROR: Basic functionality test failed"
    exit 1
fi

echo "Staging deployment validation successful"
```

## Production Environment

### Production Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Environment                    │
├─────────────────────────────────────────────────────────────┤
│  Load Balancer (if multiple instances)                     │
│  ├── Instance 1: ticket-analyzer + monitoring              │
│  ├── Instance 2: ticket-analyzer + monitoring              │
│  └── Instance N: ticket-analyzer + monitoring              │
├─────────────────────────────────────────────────────────────┤
│  Shared Storage                                             │
│  ├── Configuration Management                               │
│  ├── Log Aggregation                                        │
│  └── Report Storage                                         │
├─────────────────────────────────────────────────────────────┤
│  Monitoring & Alerting                                     │
│  ├── Application Metrics                                    │
│  ├── System Metrics                                         │
│  └── Security Monitoring                                    │
└─────────────────────────────────────────────────────────────┘
```

### Production Installation

```bash
# Production deployment script
#!/bin/bash
set -e

PROD_DIR="/opt/ticket-analyzer"
VENV_DIR="$PROD_DIR/venv"
CONFIG_DIR="/etc/ticket-analyzer"
LOG_DIR="/var/log/ticket-analyzer"
DATA_DIR="/var/lib/ticket-analyzer"

# Create production directories
sudo mkdir -p $PROD_DIR
sudo mkdir -p $CONFIG_DIR
sudo mkdir -p $LOG_DIR
sudo mkdir -p $DATA_DIR/reports
sudo mkdir -p $DATA_DIR/cache

# Create service user
sudo useradd -r -s /bin/false -d $PROD_DIR ticket-analyzer || true

# Create virtual environment
sudo python3.7 -m venv $VENV_DIR
sudo $VENV_DIR/bin/pip install --upgrade pip

# Install application with production dependencies
sudo $VENV_DIR/bin/pip install ticket-analyzer==1.0.0
sudo $VENV_DIR/bin/pip install gunicorn supervisor

# Set ownership and permissions
sudo chown -R ticket-analyzer:ticket-analyzer $PROD_DIR
sudo chown -R ticket-analyzer:ticket-analyzer $LOG_DIR
sudo chown -R ticket-analyzer:ticket-analyzer $DATA_DIR
sudo chmod 755 $PROD_DIR
sudo chmod 750 $CONFIG_DIR
sudo chmod 750 $LOG_DIR
sudo chmod 750 $DATA_DIR
```

### Production Configuration

```bash
# Create production configuration
sudo tee $CONFIG_DIR/config.json > /dev/null << 'EOF'
{
  "authentication": {
    "timeout_seconds": 60,
    "max_retry_attempts": 3,
    "check_interval_seconds": 300
  },
  "output": {
    "default_format": "json",
    "max_results": 10000,
    "sanitize_output": true,
    "output_directory": "/var/lib/ticket-analyzer/reports"
  },
  "logging": {
    "level": "INFO",
    "sanitize_logs": true,
    "log_file": "/var/log/ticket-analyzer/app.log",
    "max_log_size": "50MB",
    "backup_count": 10,
    "structured_logging": true
  },
  "mcp": {
    "timeout_seconds": 30,
    "retry_attempts": 5,
    "circuit_breaker_threshold": 10,
    "connection_pool_size": 5
  },
  "performance": {
    "batch_size": 1000,
    "max_concurrent_requests": 10,
    "cache_enabled": true,
    "cache_ttl_seconds": 3600
  },
  "security": {
    "input_validation_strict": true,
    "output_sanitization_level": "high",
    "audit_logging": true
  }
}
EOF

# Set secure permissions
sudo chmod 600 $CONFIG_DIR/config.json
sudo chown ticket-analyzer:ticket-analyzer $CONFIG_DIR/config.json
```

### Systemd Service Configuration

```bash
# Create systemd service file
sudo tee /etc/systemd/system/ticket-analyzer.service > /dev/null << 'EOF'
[Unit]
Description=Ticket Analysis CLI Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=ticket-analyzer
Group=ticket-analyzer
WorkingDirectory=/opt/ticket-analyzer
Environment=PATH=/opt/ticket-analyzer/venv/bin
Environment=TICKET_ANALYZER_CONFIG=/etc/ticket-analyzer/config.json
ExecStart=/opt/ticket-analyzer/venv/bin/ticket-analyzer daemon
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ticket-analyzer

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/ticket-analyzer /var/lib/ticket-analyzer
CapabilityBoundingSet=
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ticket-analyzer
sudo systemctl start ticket-analyzer
```

## Container Deployment

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.7-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TICKET_ANALYZER_CONFIG=/app/config/config.json

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 16 for MCP components
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash - \
    && apt-get install -y nodejs

# Create application directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install application
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/reports \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ticket-analyzer --version || exit 1

# Expose port (if running as service)
EXPOSE 8080

# Default command
CMD ["ticket-analyzer", "daemon"]
```

### Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  ticket-analyzer:
    build: .
    container_name: ticket-analyzer
    restart: unless-stopped
    
    environment:
      - TICKET_ANALYZER_CONFIG=/app/config/config.json
      - PYTHONUNBUFFERED=1
    
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - ./reports:/app/reports
      - /tmp:/tmp
    
    networks:
      - ticket-analyzer-network
    
    security_opt:
      - no-new-privileges:true
    
    read_only: true
    tmpfs:
      - /tmp
    
    healthcheck:
      test: ["CMD", "ticket-analyzer", "--version"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Optional: Log aggregation service
  fluentd:
    image: fluent/fluentd:v1.14
    container_name: ticket-analyzer-logs
    volumes:
      - ./fluentd/conf:/fluentd/etc
      - ./logs:/var/log/ticket-analyzer:ro
    networks:
      - ticket-analyzer-network
    depends_on:
      - ticket-analyzer

networks:
  ticket-analyzer-network:
    driver: bridge
```

### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ticket-analyzer
  labels:
    app: ticket-analyzer
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ticket-analyzer
  template:
    metadata:
      labels:
        app: ticket-analyzer
    spec:
      serviceAccountName: ticket-analyzer
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      
      containers:
      - name: ticket-analyzer
        image: ticket-analyzer:1.0.0
        imagePullPolicy: Always
        
        ports:
        - containerPort: 8080
          name: http
        
        env:
        - name: TICKET_ANALYZER_CONFIG
          value: "/app/config/config.json"
        
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: logs
          mountPath: /app/logs
        - name: reports
          mountPath: /app/reports
        
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        
        livenessProbe:
          exec:
            command:
            - ticket-analyzer
            - --version
          initialDelaySeconds: 30
          periodSeconds: 30
        
        readinessProbe:
          exec:
            command:
            - ticket-analyzer
            - --version
          initialDelaySeconds: 5
          periodSeconds: 10
        
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      
      volumes:
      - name: config
        configMap:
          name: ticket-analyzer-config
      - name: logs
        emptyDir: {}
      - name: reports
        persistentVolumeClaim:
          claimName: ticket-analyzer-reports

---
apiVersion: v1
kind: Service
metadata:
  name: ticket-analyzer-service
spec:
  selector:
    app: ticket-analyzer
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ticket-analyzer-config
data:
  config.json: |
    {
      "authentication": {
        "timeout_seconds": 60,
        "max_retry_attempts": 3,
        "check_interval_seconds": 300
      },
      "output": {
        "default_format": "json",
        "max_results": 10000,
        "sanitize_output": true,
        "output_directory": "/app/reports"
      },
      "logging": {
        "level": "INFO",
        "sanitize_logs": true,
        "structured_logging": true
      }
    }
```

## Environment-Specific Configurations

### Development Environment Variables

```bash
# Development .env file
TICKET_ANALYZER_ENV=development
TICKET_ANALYZER_LOG_LEVEL=DEBUG
TICKET_ANALYZER_CONFIG_DIR=~/.ticket-analyzer
TICKET_ANALYZER_MAX_RESULTS=100
TICKET_ANALYZER_CACHE_ENABLED=false
```

### Staging Environment Variables

```bash
# Staging environment variables
TICKET_ANALYZER_ENV=staging
TICKET_ANALYZER_LOG_LEVEL=INFO
TICKET_ANALYZER_CONFIG_DIR=/etc/ticket-analyzer-staging
TICKET_ANALYZER_MAX_RESULTS=1000
TICKET_ANALYZER_CACHE_ENABLED=true
TICKET_ANALYZER_CACHE_TTL=1800
```

### Production Environment Variables

```bash
# Production environment variables
TICKET_ANALYZER_ENV=production
TICKET_ANALYZER_LOG_LEVEL=INFO
TICKET_ANALYZER_CONFIG_DIR=/etc/ticket-analyzer
TICKET_ANALYZER_MAX_RESULTS=10000
TICKET_ANALYZER_CACHE_ENABLED=true
TICKET_ANALYZER_CACHE_TTL=3600
TICKET_ANALYZER_MONITORING_ENABLED=true
TICKET_ANALYZER_AUDIT_LOGGING=true
```

## Security Considerations

### Network Security

- **Firewall Rules**: Restrict access to necessary ports only
- **VPN Access**: Require VPN for remote access to production systems
- **Network Segmentation**: Isolate application in secure network segments
- **TLS/SSL**: Use encrypted connections for all external communications

### Access Control

- **Service Accounts**: Use dedicated service accounts with minimal privileges
- **File Permissions**: Ensure configuration files have restrictive permissions (600)
- **Directory Permissions**: Set appropriate directory permissions (750 for config, logs)
- **Sudo Access**: Limit sudo access to deployment and maintenance operations only

### Credential Management

- **Environment Variables**: Use environment variables for sensitive configuration
- **Secret Management**: Integrate with enterprise secret management systems
- **Credential Rotation**: Implement regular credential rotation procedures
- **Audit Logging**: Log all authentication and authorization events

## Rollback Procedures

### Application Rollback

```bash
#!/bin/bash
# Rollback script for production deployment

BACKUP_VERSION="$1"
PROD_DIR="/opt/ticket-analyzer"
BACKUP_DIR="/opt/ticket-analyzer-backups"

if [ -z "$BACKUP_VERSION" ]; then
    echo "Usage: $0 <backup_version>"
    echo "Available backups:"
    ls -la $BACKUP_DIR/
    exit 1
fi

echo "Rolling back to version: $BACKUP_VERSION"

# Stop service
sudo systemctl stop ticket-analyzer

# Backup current version
sudo cp -r $PROD_DIR $BACKUP_DIR/rollback-$(date +%Y%m%d-%H%M%S)

# Restore backup version
sudo rm -rf $PROD_DIR
sudo cp -r $BACKUP_DIR/$BACKUP_VERSION $PROD_DIR

# Restore ownership and permissions
sudo chown -R ticket-analyzer:ticket-analyzer $PROD_DIR
sudo chmod 755 $PROD_DIR

# Start service
sudo systemctl start ticket-analyzer

# Verify rollback
if sudo systemctl is-active --quiet ticket-analyzer; then
    echo "Rollback successful"
else
    echo "Rollback failed - check logs"
    exit 1
fi
```

### Configuration Rollback

```bash
#!/bin/bash
# Configuration rollback script

CONFIG_DIR="/etc/ticket-analyzer"
BACKUP_DIR="/etc/ticket-analyzer-backups"
BACKUP_VERSION="$1"

if [ -z "$BACKUP_VERSION" ]; then
    echo "Usage: $0 <config_backup_version>"
    ls -la $BACKUP_DIR/
    exit 1
fi

# Backup current config
sudo cp $CONFIG_DIR/config.json $BACKUP_DIR/config-$(date +%Y%m%d-%H%M%S).json

# Restore backup config
sudo cp $BACKUP_DIR/$BACKUP_VERSION $CONFIG_DIR/config.json

# Set permissions
sudo chmod 600 $CONFIG_DIR/config.json
sudo chown ticket-analyzer:ticket-analyzer $CONFIG_DIR/config.json

# Restart service to apply new config
sudo systemctl restart ticket-analyzer

echo "Configuration rollback completed"
```

## Deployment Checklist

### Pre-Deployment Checklist

- [ ] All tests pass in CI/CD pipeline
- [ ] Security scan completed with no critical issues
- [ ] Performance testing completed
- [ ] Configuration files reviewed and validated
- [ ] Backup procedures tested
- [ ] Rollback procedures tested
- [ ] Monitoring and alerting configured
- [ ] Documentation updated
- [ ] Stakeholders notified of deployment

### Post-Deployment Checklist

- [ ] Application starts successfully
- [ ] Health checks pass
- [ ] Authentication works correctly
- [ ] Basic functionality verified
- [ ] Logs are being generated correctly
- [ ] Monitoring metrics are being collected
- [ ] Performance metrics within acceptable ranges
- [ ] Security monitoring active
- [ ] Backup procedures working
- [ ] Documentation reflects current deployment

## Troubleshooting Common Deployment Issues

### Application Won't Start

```bash
# Check service status
sudo systemctl status ticket-analyzer

# Check logs
sudo journalctl -u ticket-analyzer -f

# Check configuration
sudo -u ticket-analyzer ticket-analyzer --validate-config

# Check permissions
ls -la /opt/ticket-analyzer
ls -la /etc/ticket-analyzer
```

### Authentication Issues

```bash
# Test authentication manually
sudo -u ticket-analyzer mwinit -s

# Check Kerberos tickets
sudo -u ticket-analyzer klist

# Verify network connectivity
sudo -u ticket-analyzer curl -I https://internal-api.amazon.com
```

### Performance Issues

```bash
# Check system resources
top
free -h
df -h

# Check application metrics
sudo -u ticket-analyzer ticket-analyzer metrics

# Check log file sizes
du -sh /var/log/ticket-analyzer/*
```

### Configuration Issues

```bash
# Validate configuration syntax
sudo -u ticket-analyzer python3 -m json.tool /etc/ticket-analyzer/config.json

# Test configuration loading
sudo -u ticket-analyzer ticket-analyzer --test-config

# Check environment variables
sudo -u ticket-analyzer env | grep TICKET_ANALYZER
```