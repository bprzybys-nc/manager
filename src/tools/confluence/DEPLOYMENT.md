# Deployment Guide

This guide provides comprehensive instructions for deploying the Confluence Integration Tool in various environments.

## Overview

The Confluence Integration Tool can be deployed in multiple ways:
- Docker containers (recommended for production)
- Kubernetes clusters (for scalable deployments)
- Direct Python installation (for development)
- Cloud platforms (AWS, GCP, Azure)

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 2GB
- Storage: 10GB (for vector embeddings)
- Network: Outbound HTTPS access to Confluence

**Recommended for Production:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 50GB SSD
- Network: Load balancer with SSL termination

### Dependencies

- Python 3.12+
- Docker 20.10+ (for containerized deployment)
- Kubernetes 1.20+ (for K8s deployment)
- Confluence Cloud or Server instance
- Valid Confluence API token

## Environment Configuration

### Environment Variables

Create environment-specific configuration files:

**Production (.env.prod):**
```bash
# Confluence Configuration
CONFLUENCE_URL=https://your-company.atlassian.net
CONFLUENCE_USERNAME=service-account@company.com
CONFLUENCE_API_TOKEN=ATATT3xFfGF0...

# API Configuration
API_HOST=0.0.0.0
API_PORT=8005
LOG_LEVEL=INFO

# Vector Store Configuration
CHROMA_PERSIST_DIRECTORY=/app/data/chroma
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Performance Tuning
MAX_WORKERS=4
REQUEST_TIMEOUT=30
BATCH_SIZE=50

# Security
ALLOWED_HOSTS=confluence-api.company.com
CORS_ORIGINS=https://company.com,https://app.company.com
```

**Staging (.env.staging):**
```bash
# Confluence Configuration
CONFLUENCE_URL=https://company-staging.atlassian.net
CONFLUENCE_USERNAME=staging-test@company.com
CONFLUENCE_API_TOKEN=ATATT3xFfGF0...

# API Configuration
API_HOST=0.0.0.0
API_PORT=8005
LOG_LEVEL=DEBUG

# Vector Store Configuration
CHROMA_PERSIST_DIRECTORY=/app/data/chroma
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Performance Tuning
MAX_WORKERS=2
REQUEST_TIMEOUT=60
BATCH_SIZE=25
```

## Docker Deployment

### Single Container Deployment

**Build and run:**
```bash
# Build the image
docker build -t confluence-tool:latest .

# Run with environment file
docker run -d \
  --name confluence-tool \
  -p 8005:8005 \
  --env-file .env.prod \
  -v confluence-data:/app/data \
  --restart unless-stopped \
  confluence-tool:latest
```

**Health check:**
```bash
# Check container status
docker ps | grep confluence-tool

# Check application health
curl http://localhost:8005/health

# View logs
docker logs confluence-tool -f
```

### Docker Compose Deployment

**Production docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  confluence-tool:
    build: .
    ports:
      - "8005:8005"
    environment:
      - CONFLUENCE_URL=${CONFLUENCE_URL}
      - CONFLUENCE_USERNAME=${CONFLUENCE_USERNAME}
      - CONFLUENCE_API_TOKEN=${CONFLUENCE_API_TOKEN}
      - CHROMA_PERSIST_DIRECTORY=/app/data/chroma
      - LOG_LEVEL=INFO
    volumes:
      - confluence-data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
    networks:
      - confluence-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - confluence-tool
    restart: unless-stopped
    networks:
      - confluence-network

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    networks:
      - confluence-network

volumes:
  confluence-data:
    driver: local
  prometheus-data:
    driver: local

networks:
  confluence-network:
    driver: bridge
```

**Deploy:**
```bash
# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f confluence-tool
```

## Kubernetes Deployment

### Namespace Setup

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: confluence-tools
  labels:
    name: confluence-tools
```

### ConfigMap and Secrets

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: confluence-tool-config
  namespace: confluence-tools
data:
  API_HOST: "0.0.0.0"
  API_PORT: "8005"
  LOG_LEVEL: "INFO"
  CHROMA_PERSIST_DIRECTORY: "/app/data/chroma"
  EMBEDDING_MODEL: "all-MiniLM-L6-v2"
  MAX_WORKERS: "4"
  REQUEST_TIMEOUT: "30"
  BATCH_SIZE: "50"

---
apiVersion: v1
kind: Secret
metadata:
  name: confluence-tool-secrets
  namespace: confluence-tools
type: Opaque
stringData:
  CONFLUENCE_URL: "https://your-company.atlassian.net"
  CONFLUENCE_USERNAME: "service-account@company.com"
  CONFLUENCE_API_TOKEN: "your-api-token-here"
```

### Deployment with High Availability

```yaml
# deployment-ha.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: confluence-tool
  namespace: confluence-tools
  labels:
    app: confluence-tool
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  selector:
    matchLabels:
      app: confluence-tool
  template:
    metadata:
      labels:
        app: confluence-tool
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - confluence-tool
              topologyKey: kubernetes.io/hostname
      containers:
      - name: confluence-tool
        image: confluence-tool:v1.0.0
        ports:
        - containerPort: 8005
          name: http
        envFrom:
        - configMapRef:
            name: confluence-tool-config
        - secretRef:
            name: confluence-tool-secrets
        volumeMounts:
        - name: data-storage
          mountPath: /app/data
        - name: tmp-storage
          mountPath: /tmp
        livenessProbe:
          httpGet:
            path: /health
            port: 8005
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/detailed
            port: 8005
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "8Gi"
            cpu: "2000m"
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      volumes:
      - name: data-storage
        persistentVolumeClaim:
          claimName: confluence-tool-data-pvc
      - name: tmp-storage
        emptyDir: {}
      securityContext:
        fsGroup: 1000
```

### Service and Ingress

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: confluence-tool-service
  namespace: confluence-tools
  labels:
    app: confluence-tool
spec:
  selector:
    app: confluence-tool
  ports:
  - name: http
    port: 80
    targetPort: 8005
    protocol: TCP
  type: ClusterIP

---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: confluence-tool-ingress
  namespace: confluence-tools
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - confluence-api.company.com
    secretName: confluence-tool-tls
  rules:
  - host: confluence-api.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: confluence-tool-service
            port:
              number: 80
```

### Persistent Storage

```yaml
# storage.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: confluence-tool-data-pvc
  namespace: confluence-tools
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 100Gi

---
# For shared storage across replicas (if needed)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: confluence-tool-shared-pvc
  namespace: confluence-tools
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: nfs-client
  resources:
    requests:
      storage: 100Gi
```

### Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f storage.yaml
kubectl apply -f deployment-ha.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Check deployment status
kubectl get pods -n confluence-tools
kubectl get services -n confluence-tools
kubectl get ingress -n confluence-tools

# Check logs
kubectl logs -f deployment/confluence-tool -n confluence-tools

# Scale deployment
kubectl scale deployment confluence-tool --replicas=5 -n confluence-tools
```

## Cloud Platform Deployment

### AWS ECS Deployment

**Task Definition:**
```json
{
  "family": "confluence-tool",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/confluenceToolTaskRole",
  "containerDefinitions": [
    {
      "name": "confluence-tool",
      "image": "your-account.dkr.ecr.region.amazonaws.com/confluence-tool:latest",
      "portMappings": [
        {
          "containerPort": 8005,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "API_HOST",
          "value": "0.0.0.0"
        },
        {
          "name": "API_PORT",
          "value": "8005"
        }
      ],
      "secrets": [
        {
          "name": "CONFLUENCE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:confluence/url"
        },
        {
          "name": "CONFLUENCE_USERNAME",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:confluence/username"
        },
        {
          "name": "CONFLUENCE_API_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:confluence/token"
        }
      ],
      "mountPoints": [
        {
          "sourceVolume": "confluence-data",
          "containerPath": "/app/data"
        }
      ],
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8005/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/confluence-tool",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "volumes": [
    {
      "name": "confluence-data",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-12345678",
        "rootDirectory": "/confluence-tool-data"
      }
    }
  ]
}
```

### Google Cloud Run Deployment

```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: confluence-tool
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/execution-environment: gen2
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        autoscaling.knative.dev/minScale: "1"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "8Gi"
        run.googleapis.com/cpu: "4"
    spec:
      containerConcurrency: 100
      timeoutSeconds: 300
      containers:
      - image: gcr.io/project-id/confluence-tool:latest
        ports:
        - containerPort: 8005
        env:
        - name: API_HOST
          value: "0.0.0.0"
        - name: API_PORT
          value: "8005"
        - name: CONFLUENCE_URL
          valueFrom:
            secretKeyRef:
              key: url
              name: confluence-secrets
        - name: CONFLUENCE_USERNAME
          valueFrom:
            secretKeyRef:
              key: username
              name: confluence-secrets
        - name: CONFLUENCE_API_TOKEN
          valueFrom:
            secretKeyRef:
              key: token
              name: confluence-secrets
        resources:
          limits:
            memory: "8Gi"
            cpu: "4"
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
      volumes:
      - name: data-volume
        csi:
          driver: gcsfuse.csi.storage.gke.io
          volumeAttributes:
            bucketName: confluence-tool-data
            mountOptions: "implicit-dirs"
```

## Monitoring and Observability

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'confluence-tool'
    static_configs:
      - targets: ['confluence-tool:8005']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'confluence-tool-health'
    static_configs:
      - targets: ['confluence-tool:8005']
    metrics_path: '/health/detailed'
    scrape_interval: 60s
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Confluence Integration Tool",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"4..|5..\"}[5m])",
            "legendFormat": "Error rate"
          }
        ]
      }
    ]
  }
}
```

### Logging Configuration

```yaml
# fluent-bit.conf
[SERVICE]
    Flush         1
    Log_Level     info
    Daemon        off
    Parsers_File  parsers.conf

[INPUT]
    Name              tail
    Path              /app/logs/*.log
    Parser            json
    Tag               confluence-tool.*
    Refresh_Interval  5

[OUTPUT]
    Name  es
    Match *
    Host  elasticsearch.logging.svc.cluster.local
    Port  9200
    Index confluence-tool-logs
    Type  _doc
```

## Security Considerations

### Network Security

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: confluence-tool-network-policy
  namespace: confluence-tools
spec:
  podSelector:
    matchLabels:
      app: confluence-tool
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8005
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS to Confluence
    - protocol: TCP
      port: 53   # DNS
    - protocol: UDP
      port: 53   # DNS
```

### Pod Security Policy

```yaml
# pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: confluence-tool-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

## Backup and Recovery

### Data Backup Strategy

```bash
#!/bin/bash
# backup-script.sh

BACKUP_DIR="/backups/confluence-tool"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR/$DATE"

# Backup vector store data
kubectl exec -n confluence-tools deployment/confluence-tool -- \
  tar czf - /app/data/chroma | \
  cat > "$BACKUP_DIR/$DATE/chroma-data.tar.gz"

# Backup configuration
kubectl get configmap confluence-tool-config -n confluence-tools -o yaml > \
  "$BACKUP_DIR/$DATE/configmap.yaml"

# Backup secrets (encrypted)
kubectl get secret confluence-tool-secrets -n confluence-tools -o yaml > \
  "$BACKUP_DIR/$DATE/secrets.yaml"

# Cleanup old backups (keep last 30 days)
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR/$DATE"
```

### Disaster Recovery

```bash
#!/bin/bash
# restore-script.sh

BACKUP_DATE=$1
BACKUP_DIR="/backups/confluence-tool/$BACKUP_DATE"

if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory not found: $BACKUP_DIR"
  exit 1
fi

# Scale down deployment
kubectl scale deployment confluence-tool --replicas=0 -n confluence-tools

# Restore configuration
kubectl apply -f "$BACKUP_DIR/configmap.yaml"
kubectl apply -f "$BACKUP_DIR/secrets.yaml"

# Restore vector store data
kubectl exec -n confluence-tools deployment/confluence-tool -- \
  tar xzf - -C / < "$BACKUP_DIR/chroma-data.tar.gz"

# Scale up deployment
kubectl scale deployment confluence-tool --replicas=3 -n confluence-tools

echo "Restore completed from: $BACKUP_DIR"
```

## Performance Tuning

### Application Tuning

```bash
# Environment variables for performance
export UVICORN_WORKERS=4
export UVICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker
export UVICORN_MAX_REQUESTS=1000
export UVICORN_MAX_REQUESTS_JITTER=100

# Vector store optimization
export CHROMA_BATCH_SIZE=100
export CHROMA_MAX_BATCH_SIZE=1000
export EMBEDDING_BATCH_SIZE=32

# Memory optimization
export PYTHONMALLOC=malloc
export MALLOC_ARENA_MAX=2
```

### Database Tuning

```python
# config/performance.py
CHROMA_SETTINGS = {
    "anonymized_telemetry": False,
    "allow_reset": False,
    "is_persistent": True,
    "persist_directory": "/app/data/chroma",
    "chroma_db_impl": "duckdb+parquet",
    "chroma_server_host": None,
    "chroma_server_http_port": None,
    "chroma_server_ssl_enabled": False,
    "chroma_server_grpc_port": None,
    "chroma_server_cors_allow_origins": []
}
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check memory usage
   kubectl top pods -n confluence-tools
   
   # Adjust memory limits
   kubectl patch deployment confluence-tool -n confluence-tools -p \
     '{"spec":{"template":{"spec":{"containers":[{"name":"confluence-tool","resources":{"limits":{"memory":"16Gi"}}}]}}}}'
   ```

2. **Slow Vector Search**
   ```bash
   # Check vector store size
   kubectl exec -n confluence-tools deployment/confluence-tool -- \
     du -sh /app/data/chroma
   
   # Rebuild index
   curl -X POST http://confluence-api.company.com/bulk/index \
     -H "Content-Type: application/json" \
     -d '{"force_reindex": true}'
   ```

3. **Connection Issues**
   ```bash
   # Test Confluence connectivity
   kubectl exec -n confluence-tools deployment/confluence-tool -- \
     curl -s https://your-company.atlassian.net/wiki/rest/api/space
   
   # Check DNS resolution
   kubectl exec -n confluence-tools deployment/confluence-tool -- \
     nslookup your-company.atlassian.net
   ```

### Health Checks

```bash
# Application health
curl -f http://confluence-api.company.com/health

# Detailed health with dependencies
curl -f http://confluence-api.company.com/health/detailed

# Confluence connectivity
curl -f http://confluence-api.company.com/health/confluence
```

This completes the comprehensive deployment guide covering all major deployment scenarios and operational considerations.