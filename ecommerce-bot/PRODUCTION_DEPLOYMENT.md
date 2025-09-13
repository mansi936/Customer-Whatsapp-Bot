# 🚀 Production Deployment Guide

## Table of Contents
1. [Production Features](#production-features)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Deployment Steps](#deployment-steps)
4. [Monitoring & Observability](#monitoring--observability)
5. [Security Hardening](#security-hardening)
6. [Performance Optimization](#performance-optimization)
7. [Disaster Recovery](#disaster-recovery)
8. [Maintenance & Operations](#maintenance--operations)

## Production Features

### ✅ Error Handling & Resilience
- **Retry Logic**: Exponential backoff with jitter for all external service calls
- **Circuit Breakers**: Prevents cascading failures with automatic recovery
- **Fallback Mechanisms**: Graceful degradation when services are unavailable
- **Dead Letter Queues**: Failed messages are stored for manual review

### ✅ Concurrency & Performance
- **Connection Pooling**: Optimized connection management for Redis, MongoDB, PostgreSQL
- **Async Processing**: Non-blocking I/O throughout the application
- **Load Balancing**: Round-robin distribution across service instances
- **Auto-scaling**: Horizontal scaling based on CPU/memory metrics

### ✅ Monitoring & Observability
- **Prometheus Metrics**: Comprehensive application and business metrics
- **Distributed Tracing**: OpenTelemetry integration with Jaeger
- **Structured Logging**: JSON formatted logs with correlation IDs
- **Health Checks**: Liveness, readiness, and startup probes

### ✅ Security
- **TLS/SSL**: End-to-end encryption for all communications
- **Secrets Management**: Environment-based secret injection
- **Rate Limiting**: Request throttling to prevent abuse
- **Input Validation**: Comprehensive sanitization of user inputs

## Pre-Deployment Checklist

### Infrastructure Requirements
- [ ] Kubernetes cluster (v1.25+) with at least 3 nodes
- [ ] Redis cluster with persistence enabled
- [ ] MongoDB replica set with backups
- [ ] PostgreSQL with read replicas
- [ ] Object storage for media files (S3/Azure Blob)
- [ ] CDN for static content delivery
- [ ] Load balancer with SSL termination

### Configuration
- [ ] All environment variables configured in `.env.production`
- [ ] SSL certificates obtained and configured
- [ ] DNS records configured for your domain
- [ ] Firewall rules configured
- [ ] Backup storage configured
- [ ] Monitoring endpoints configured

### Security Audit
- [ ] All secrets rotated and stored securely
- [ ] Network policies configured
- [ ] RBAC policies defined
- [ ] Security scanning completed
- [ ] Penetration testing performed
- [ ] Compliance requirements verified

## Deployment Steps

### 1. Build and Push Docker Images

```bash
# Build production images
docker build -t ecommerce-bot:latest .
docker build -f Dockerfile.mcp -t ecommerce-bot-mcp:latest .

# Tag for registry
docker tag ecommerce-bot:latest your-registry.com/ecommerce-bot:v1.0.0
docker tag ecommerce-bot-mcp:latest your-registry.com/ecommerce-bot-mcp:v1.0.0

# Push to registry
docker push your-registry.com/ecommerce-bot:v1.0.0
docker push your-registry.com/ecommerce-bot-mcp:v1.0.0
```

### 2. Deploy Infrastructure

```bash
# Create namespace
kubectl create namespace ecommerce-bot

# Deploy secrets
kubectl create secret generic ecommerce-bot-secrets \
  --from-env-file=.env.production \
  -n ecommerce-bot

# Deploy databases (if not using managed services)
kubectl apply -f kubernetes/databases/

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=redis -n ecommerce-bot --timeout=300s
kubectl wait --for=condition=ready pod -l app=mongodb -n ecommerce-bot --timeout=300s
```

### 3. Deploy Application

```bash
# Deploy main application
kubectl apply -f kubernetes/deployment.yaml

# Verify deployment
kubectl rollout status deployment/webhook-deployment -n ecommerce-bot

# Check pods
kubectl get pods -n ecommerce-bot

# Check services
kubectl get svc -n ecommerce-bot
```

### 4. Configure Ingress

```bash
# Install cert-manager for SSL
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Deploy ingress
kubectl apply -f kubernetes/ingress.yaml

# Verify SSL certificate
kubectl get certificate -n ecommerce-bot
```

### 5. Deploy Monitoring Stack

```bash
# Deploy Prometheus
kubectl apply -f monitoring/prometheus/

# Deploy Grafana
kubectl apply -f monitoring/grafana/

# Deploy Jaeger
kubectl apply -f monitoring/jaeger/

# Access Grafana
kubectl port-forward svc/grafana 3000:3000 -n ecommerce-bot
# Default login: admin/admin
```

## Monitoring & Observability

### Key Metrics to Monitor

#### Application Metrics
- **Request Rate**: Requests per second by endpoint
- **Error Rate**: 4xx and 5xx errors per minute
- **Response Time**: P50, P95, P99 latencies
- **Active Sessions**: Number of concurrent users
- **Tool Execution Time**: MCP tool performance

#### Business Metrics
- **Orders Per Hour**: Transaction volume
- **Cart Abandonment Rate**: Incomplete checkouts
- **Revenue**: Real-time revenue tracking
- **User Engagement**: Messages per session

#### System Metrics
- **CPU Usage**: Per pod and node
- **Memory Usage**: Heap and RSS memory
- **Network I/O**: Bandwidth utilization
- **Disk I/O**: Storage performance
- **Connection Pool Status**: Active/idle connections

### Alert Configuration

```yaml
# prometheus-alerts.yml
groups:
  - name: ecommerce-bot
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.01
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      - alert: HighLatency
        expr: histogram_quantile(0.99, request_duration_seconds) > 1
        for: 5m
        annotations:
          summary: "P99 latency exceeds 1 second"
          
      - alert: PodMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.8
        for: 5m
        annotations:
          summary: "Pod memory usage above 80%"
```

### Dashboard Setup

Access Grafana and import the following dashboards:
1. **Application Dashboard**: `monitoring/grafana/dashboards/application.json`
2. **Business Metrics**: `monitoring/grafana/dashboards/business.json`
3. **Infrastructure**: `monitoring/grafana/dashboards/infrastructure.json`

## Security Hardening

### Network Security
```bash
# Apply network policies
kubectl apply -f kubernetes/network-policies/

# Verify policies
kubectl get networkpolicy -n ecommerce-bot
```

### Secrets Rotation
```bash
# Rotate database passwords
./scripts/rotate-secrets.sh

# Update Kubernetes secrets
kubectl create secret generic ecommerce-bot-secrets \
  --from-env-file=.env.production \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Security Scanning
```bash
# Scan images for vulnerabilities
trivy image your-registry.com/ecommerce-bot:latest

# Scan Kubernetes manifests
kubesec scan kubernetes/deployment.yaml

# Runtime security with Falco
kubectl apply -f security/falco/
```

## Performance Optimization

### Database Optimization
```sql
-- Create indexes for MongoDB
db.users.createIndex({ "phone_number": 1 }, { unique: true })
db.orders.createIndex({ "user_id": 1, "created_at": -1 })
db.products.createIndex({ "category": 1, "price": 1 })

-- PostgreSQL optimization
CREATE INDEX idx_products_search ON products USING gin(to_tsvector('english', name || ' ' || description));
VACUUM ANALYZE products;
```

### Redis Optimization
```bash
# Configure Redis for production
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

### Application Tuning
```python
# Update configuration for production
MCP_CLIENT_POOL_SIZE=20
REDIS_MAX_CONNECTIONS=200
MONGODB_MAX_POOL_SIZE=100
WORKERS=8
```

## Disaster Recovery

### Backup Strategy

#### Automated Backups
```bash
# Schedule daily backups
kubectl apply -f kubernetes/cronjobs/backup.yaml

# Verify backup job
kubectl get cronjob -n ecommerce-bot
```

#### Manual Backup
```bash
# MongoDB backup
mongodump --uri="mongodb://..." --out=/backups/mongodb-$(date +%Y%m%d)

# Redis backup
redis-cli BGSAVE

# PostgreSQL backup
pg_dump -h localhost -U user -d ecommerce_bot > /backups/postgres-$(date +%Y%m%d).sql
```

### Restore Procedures

#### Database Restore
```bash
# MongoDB restore
mongorestore --uri="mongodb://..." /backups/mongodb-20240101

# Redis restore
redis-cli --rdb /backups/redis.rdb

# PostgreSQL restore
psql -h localhost -U user -d ecommerce_bot < /backups/postgres-20240101.sql
```

#### Application Rollback
```bash
# Rollback deployment
kubectl rollout undo deployment/webhook-deployment -n ecommerce-bot

# Rollback to specific revision
kubectl rollout undo deployment/webhook-deployment --to-revision=3 -n ecommerce-bot
```

## Maintenance & Operations

### Health Checks
```bash
# Check application health
curl https://api.ecommerce-bot.com/health

# Check all pod status
kubectl get pods -n ecommerce-bot -o wide

# Check resource usage
kubectl top pods -n ecommerce-bot
```

### Log Management
```bash
# View application logs
kubectl logs -f deployment/webhook-deployment -n ecommerce-bot

# Export logs for analysis
kubectl logs deployment/webhook-deployment -n ecommerce-bot --since=1h > app-logs.txt

# Search logs with stern
stern webhook -n ecommerce-bot --since 30m
```

### Scaling Operations
```bash
# Manual scaling
kubectl scale deployment webhook-deployment --replicas=5 -n ecommerce-bot

# Update autoscaling
kubectl edit hpa webhook-hpa -n ecommerce-bot
```

### Performance Profiling
```bash
# Enable profiling endpoint
kubectl set env deployment/webhook-deployment ENABLE_PROFILING=true -n ecommerce-bot

# Collect CPU profile
curl http://localhost:6060/debug/pprof/profile?seconds=30 > cpu.prof

# Analyze with pprof
go tool pprof cpu.prof
```

## Troubleshooting Guide

### Common Issues

#### High Memory Usage
```bash
# Check memory usage
kubectl top pods -n ecommerce-bot

# Get heap dump
kubectl exec -it <pod-name> -n ecommerce-bot -- python -m tracemalloc

# Restart pod
kubectl delete pod <pod-name> -n ecommerce-bot
```

#### Connection Issues
```bash
# Test Redis connection
kubectl exec -it <pod-name> -n ecommerce-bot -- redis-cli -h redis-service ping

# Test MongoDB connection
kubectl exec -it <pod-name> -n ecommerce-bot -- mongosh --eval "db.adminCommand('ping')"

# Check network policies
kubectl describe networkpolicy -n ecommerce-bot
```

#### Performance Degradation
```bash
# Check slow queries in MongoDB
db.currentOp({"secs_running": {$gte: 3}})

# Check Redis slow log
redis-cli SLOWLOG GET 10

# Check application metrics
curl http://localhost:9090/metrics | grep -E "(latency|duration)"
```

## Support & Contact

For production support:
- **Critical Issues**: Page on-call engineer via PagerDuty
- **Non-Critical**: Create ticket in JIRA
- **Security Issues**: security@ecommerce-bot.com
- **Documentation**: https://docs.ecommerce-bot.com

## Compliance & Auditing

- **PCI DSS**: Payment data handling compliant
- **GDPR**: User data privacy compliant
- **SOC 2**: Security controls audited
- **ISO 27001**: Information security certified

---

**Last Updated**: January 2024
**Version**: 1.0.0
**Maintained By**: DevOps Team