# Guía de Deployment - ETERNA DX Rules Engine

## Resumen Ejecutivo

Esta guía cubre el despliegue del sistema ETERNA DX Rules Engine desde desarrollo hasta producción, incluyendo configuraciones de Docker, Kubernetes, monitoreo y procedimientos operacionales.

## Arquitectura de Deployment

### Entornos

```mermaid
flowchart LR
    subgraph "Development"
        DEV[Local Dev<br/>SQLite + Hot Reload]
    end
    
    subgraph "Staging"
        STAGE[Staging<br/>PostgreSQL + Docker]
    end
    
    subgraph "Production"
        PROD[Production<br/>K8s + PostgreSQL<br/>+ Redis + Monitoring]
    end
    
    DEV --> STAGE
    STAGE --> PROD
```

### Componentes por Entorno

| Componente | Development | Staging | Production |
|------------|-------------|---------|------------|
| **Backend** | uvicorn --reload | Docker container | Kubernetes pods (3+) |
| **Frontend** | next dev | Docker container | CDN + Static hosting |
| **Database** | SQLite local | PostgreSQL container | PostgreSQL cluster |
| **Cache** | Sin cache | Redis container | Redis cluster |
| **Load Balancer** | N/A | nginx | ALB/nginx ingress |
| **Monitoring** | Logs locales | Basic metrics | Full observability stack |

---

## Configuración por Entornos

### Development (Local)

**Prerrequisitos:**
- Python 3.9+
- Node.js 18+
- Git

**Configuración rápida:**
```bash
# 1. Clonar y configurar
git clone <repository>
cd def_recomendations

# 2. Backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# 3. Frontend  
cd admin-ui
npm install
cd ..

# 4. Iniciar servicios
.\run-dev.ps1  # Windows
# ./run-dev.sh  # Linux/macOS (TODO: crear)
```

**Variables de entorno (.env.local):**
```env
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000
DATABASE_URL=sqlite:///./rules.db
AUTH_ENABLED=false
```

### Staging

**Docker Compose para staging:**

```yaml
# docker-compose.staging.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: eterna_rules_staging
      POSTGRES_USER: eterna_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U eterna_user -d eterna_rules_staging"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      APP_ENV: staging
      DATABASE_URL: postgresql://eterna_user:${DB_PASSWORD}@postgres:5432/eterna_rules_staging
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      AUTH_ENABLED: true
      CORS_ORIGINS: https://staging-admin.eterna.com
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.staging.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

**Comandos de staging:**
```bash
# Desplegar staging
docker-compose -f docker-compose.staging.yml up -d

# Ver logs
docker-compose -f docker-compose.staging.yml logs -f backend

# Ejecutar migraciones
docker-compose -f docker-compose.staging.yml exec backend python -c "from backend.rules_engine.persistence import create_all_tables; create_all_tables()"

# Backup de BD
docker-compose -f docker-compose.staging.yml exec postgres pg_dump -U eterna_user eterna_rules_staging > backup_$(date +%Y%m%d).sql
```

### Production (Kubernetes)

**Namespace y configuración base:**

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: eterna-rules
  labels:
    name: eterna-rules
    environment: production
```

**ConfigMap para configuración:**

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: eterna-rules-config
  namespace: eterna-rules
data:
  APP_ENV: "production"
  APP_HOST: "0.0.0.0"
  APP_PORT: "8000"
  MAX_RECS_PER_DAY: "5"
  ANTI_REPEAT_DAYS: "14"
  DEFAULT_LOCALE: "es-ES"
  LOG_LEVEL: "INFO"
```

**Secrets para credenciales:**

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: eterna-rules-secrets
  namespace: eterna-rules
type: Opaque
data:
  # Base64 encoded values
  DATABASE_URL: <base64_encoded_postgresql_url>
  REDIS_URL: <base64_encoded_redis_url>
  JWT_SECRET_KEY: <base64_encoded_jwt_secret>
  SENTRY_DSN: <base64_encoded_sentry_dsn>
```

**Deployment del backend:**

```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eterna-rules-backend
  namespace: eterna-rules
  labels:
    app: eterna-rules-backend
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: eterna-rules-backend
  template:
    metadata:
      labels:
        app: eterna-rules-backend
    spec:
      containers:
      - name: backend
        image: eterna/rules-engine:v0.1.0
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: eterna-rules-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: eterna-rules-secrets
              key: REDIS_URL
        envFrom:
        - configMapRef:
            name: eterna-rules-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
          readOnly: true
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: eterna-rules-data-pvc
      imagePullSecrets:
      - name: registry-secret
```

**Service y Ingress:**

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: eterna-rules-backend-service
  namespace: eterna-rules
spec:
  selector:
    app: eterna-rules-backend
  ports:
  - port: 80
    targetPort: 8000
    name: http
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: eterna-rules-ingress
  namespace: eterna-rules
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://admin.eterna.com"
spec:
  tls:
  - hosts:
    - api.eterna.com
    secretName: eterna-rules-tls
  rules:
  - host: api.eterna.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: eterna-rules-backend-service
            port:
              number: 80
```

**HorizontalPodAutoscaler:**

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: eterna-rules-backend-hpa
  namespace: eterna-rules
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: eterna-rules-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Base de Datos

### PostgreSQL para Producción

**Configuración recomendada:**

```sql
-- postgresql.conf optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

-- Índices para performance
CREATE INDEX CONCURRENTLY idx_audits_user_date ON audits(user_id, date);
CREATE INDEX CONCURRENTLY idx_audits_rule_fired ON audits(rule_id, fired);
CREATE INDEX CONCURRENTLY idx_audits_created_at ON audits(created_at);
CREATE INDEX CONCURRENTLY idx_rules_enabled_tenant ON rules(enabled, tenant_id);
CREATE INDEX CONCURRENTLY idx_change_logs_created_at ON change_logs(created_at);
```

**Backup y Restore:**

```bash
# Backup diario automático
#!/bin/bash
# /opt/scripts/backup_eterna_rules.sh
export PGPASSWORD="$DB_PASSWORD"
BACKUP_DIR="/backups/eterna-rules"
DATE=$(date +%Y%m%d_%H%M%S)

pg_dump -h $DB_HOST -U $DB_USER -d eterna_rules_prod \
  --format=custom \
  --file="$BACKUP_DIR/eterna_rules_$DATE.dump"

# Comprimir y subir a S3
gzip "$BACKUP_DIR/eterna_rules_$DATE.dump"
aws s3 cp "$BACKUP_DIR/eterna_rules_$DATE.dump.gz" \
  s3://eterna-backups/database/

# Limpiar backups locales > 7 días
find $BACKUP_DIR -name "*.dump.gz" -mtime +7 -delete
```

**Cron job para backup:**
```cron
# Backup diario a las 2:00 AM
0 2 * * * /opt/scripts/backup_eterna_rules.sh >> /var/log/backup.log 2>&1
```

### Migraciones con Alembic

**Configuración inicial:**

```bash
# Instalar Alembic
pip install alembic

# Inicializar Alembic
alembic init alembic

# Generar migración inicial
alembic revision --autogenerate -m "Initial schema"

# Aplicar migraciones
alembic upgrade head
```

**Script de migración ejemplo:**

```python
# alembic/versions/001_initial_schema.py
"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2025-03-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Crear tablas principales
    op.create_table('variables',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('label', sa.String(), nullable=True),
        # ... más columnas
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    
    # Índices
    op.create_index('ix_variables_key', 'variables', ['key'])

def downgrade():
    op.drop_table('variables')
```

---

## Monitoreo y Observabilidad

### Prometheus Metrics

**Configuración de métricas:**

```python
# backend/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Métricas de negocio
RULES_EVALUATED_TOTAL = Counter(
    'rules_evaluated_total', 
    'Total number of rules evaluated',
    ['tenant_id', 'rule_id']
)

RECOMMENDATIONS_GENERATED_TOTAL = Counter(
    'recommendations_generated_total',
    'Total recommendations generated', 
    ['category', 'severity']
)

EVALUATION_DURATION_SECONDS = Histogram(
    'evaluation_duration_seconds',
    'Time spent evaluating rules for a user',
    ['tenant_id']
)

ACTIVE_RULES_COUNT = Gauge(
    'active_rules_count',
    'Number of active rules',
    ['tenant_id', 'category']
)

# Métricas técnicas
HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

DATABASE_QUERY_DURATION_SECONDS = Histogram(
    'database_query_duration_seconds',
    'Database query execution time',
    ['query_type']
)

# Endpoint para Prometheus
from fastapi import Response

@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Configuración Prometheus:**

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "eterna_rules_alerts.yml"

scrape_configs:
  - job_name: 'eterna-rules-backend'
    static_configs:
      - targets: ['eterna-rules-backend-service:80']
    metrics_path: '/metrics'
    scrape_interval: 30s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboard

**Dashboard JSON (extracto):**

```json
{
  "dashboard": {
    "id": null,
    "title": "ETERNA Rules Engine",
    "tags": ["eterna", "rules"],
    "panels": [
      {
        "title": "Rules Evaluation Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(rules_evaluated_total[5m])",
            "legendFormat": "{{tenant_id}} - {{rule_id}}"
          }
        ]
      },
      {
        "title": "Recommendations Generated",
        "type": "singlestat",
        "targets": [
          {
            "expr": "sum(increase(recommendations_generated_total[1h]))",
            "legendFormat": "Last Hour"
          }
        ]
      },
      {
        "title": "Average Evaluation Time",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(evaluation_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### Alerting Rules

```yaml
# eterna_rules_alerts.yml
groups:
  - name: eterna_rules
    rules:
      - alert: HighEvaluationLatency
        expr: histogram_quantile(0.95, rate(evaluation_duration_seconds_bucket[5m])) > 2.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High rule evaluation latency"
          description: "95th percentile evaluation time is {{ $value }}s"

      - alert: RulesEngineDown
        expr: up{job="eterna-rules-backend"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Rules Engine is down"
          description: "Rules Engine has been down for more than 1 minute"

      - alert: DatabaseConnectionFailed
        expr: database_query_duration_seconds{query_type="health_check"} > 5.0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection issues"
          description: "Database queries taking too long"

      - alert: LowRecommendationGeneration
        expr: rate(recommendations_generated_total[1h]) < 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low recommendation generation rate"
          description: "Only {{ $value }} recommendations generated in the last hour"
```

### Logging Centralizado

**Configuración structured logging:**

```python
# backend/logging_config.py
import structlog
import logging
import sys

def configure_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

# Uso en el código
logger = structlog.get_logger()

def evaluate_user(user_id, target_day, tenant_id="default"):
    logger.info("evaluation_started", 
                user_id=user_id, 
                target_day=str(target_day),
                tenant_id=tenant_id)
    
    try:
        # ... lógica de evaluación
        logger.info("evaluation_completed",
                   user_id=user_id,
                   recommendations_count=len(results),
                   duration_ms=duration)
    except Exception as e:
        logger.error("evaluation_failed",
                    user_id=user_id,
                    error=str(e),
                    exc_info=True)
        raise
```

**Fluentd configuración para Kubernetes:**

```yaml
# k8s/fluentd-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*eterna-rules*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      format json
      time_key time
      time_format %Y-%m-%dT%H:%M:%S.%NZ
    </source>

    <filter kubernetes.**>
      @type kubernetes_metadata
    </filter>

    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch.logging.svc.cluster.local
      port 9200
      index_name eterna-rules
      type_name logs
    </match>
```

---

## Seguridad

### HTTPS y Certificados SSL

**Cert-manager para Kubernetes:**

```yaml
# k8s/cert-manager-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: devops@eterna.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

### Secrets Management

**Usando Azure Key Vault / AWS Secrets Manager:**

```yaml
# k8s/secret-provider.yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: eterna-rules-secrets
  namespace: eterna-rules
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "true"
    userAssignedIdentityClientID: "client-id"
    keyvaultName: "eterna-keyvault"
    objects: |
      array:
        - |
          objectName: database-url
          objectType: secret
        - |
          objectName: jwt-secret-key
          objectType: secret
  secretObjects:
  - secretName: eterna-rules-secrets
    type: Opaque
    data:
    - objectName: database-url
      key: DATABASE_URL
    - objectName: jwt-secret-key
      key: JWT_SECRET_KEY
```

### Network Policies

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: eterna-rules-network-policy
  namespace: eterna-rules
spec:
  podSelector:
    matchLabels:
      app: eterna-rules-backend
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
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          name: redis
    ports:
    - protocol: TCP
      port: 6379
```

---

## CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy ETERNA Rules Engine

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: eterna/rules-engine

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest backend/tests/ --cov=backend --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
    
    - name: Build and push
      id: build
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to staging
      run: |
        echo "Deploying ${{ needs.build.outputs.image-tag }} to staging"
        # kubectl set image deployment/eterna-rules-backend backend=${{ needs.build.outputs.image-tag }}

  deploy-production:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to production
      run: |
        echo "Deploying ${{ needs.build.outputs.image-tag }} to production"
        # kubectl set image deployment/eterna-rules-backend backend=${{ needs.build.outputs.image-tag }}
```

### Dockerfile Optimizado

```dockerfile
# Dockerfile
# Multi-stage build para optimizar tamaño y seguridad
FROM node:18-alpine AS frontend-build
WORKDIR /app/admin-ui

# Instalar dependencias
COPY admin-ui/package*.json ./
RUN npm ci --only=production --no-audit

# Build frontend
COPY admin-ui/ ./
RUN npm run build

# Backend stage
FROM python:3.11-slim AS backend

# Crear usuario no-root
RUN groupadd -r eterna && useradd -r -g eterna eterna

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY backend/ ./backend/
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config.py ./

# Copiar frontend build
COPY --from=frontend-build /app/admin-ui/out ./static/

# Crear directorios necesarios
RUN mkdir -p /app/data /app/logs \
    && chown -R eterna:eterna /app

# Cambiar a usuario no-root
USER eterna

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Puerto
EXPOSE 8000

# Comando por defecto
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## Procedimientos Operacionales

### Runbooks

#### Deployment de Nueva Versión

```bash
#!/bin/bash
# scripts/deploy_production.sh

set -e

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

echo "🚀 Deploying ETERNA Rules Engine v$VERSION to production"

# 1. Validar imagen existe
docker pull ghcr.io/eterna/rules-engine:$VERSION

# 2. Backup de base de datos
kubectl exec -n eterna-rules deployment/postgres -- \
    pg_dump -U eterna_user eterna_rules_prod > backup_pre_$VERSION.sql

# 3. Aplicar migraciones si las hay
kubectl exec -n eterna-rules deployment/eterna-rules-backend -- \
    python -c "from alembic import command; from alembic.config import Config; cfg = Config('alembic.ini'); command.upgrade(cfg, 'head')"

# 4. Rolling update
kubectl set image deployment/eterna-rules-backend \
    backend=ghcr.io/eterna/rules-engine:$VERSION \
    -n eterna-rules

# 5. Esperar rollout
kubectl rollout status deployment/eterna-rules-backend -n eterna-rules --timeout=300s

# 6. Smoke tests
echo "🧪 Running smoke tests..."
curl -f https://api.eterna.com/health
curl -f https://api.eterna.com/rules?limit=1

echo "✅ Deployment completed successfully!"
```

#### Rollback de Emergencia

```bash
#!/bin/bash
# scripts/emergency_rollback.sh

set -e

echo "🚨 Emergency rollback initiated"

# 1. Rollback Kubernetes deployment
kubectl rollout undo deployment/eterna-rules-backend -n eterna-rules

# 2. Esperar rollback
kubectl rollout status deployment/eterna-rules-backend -n eterna-rules --timeout=180s

# 3. Verificar health
curl -f https://api.eterna.com/health

# 4. Notificar equipo
curl -X POST $SLACK_WEBHOOK_URL -H 'Content-type: application/json' \
    --data '{"text":"🚨 ETERNA Rules Engine rollback completed"}'

echo "✅ Emergency rollback completed"
```

#### Scaling Manual

```bash
#!/bin/bash
# scripts/scale_production.sh

REPLICAS=$1
if [ -z "$REPLICAS" ]; then
    echo "Usage: $0 <replica_count>"
    exit 1
fi

echo "📈 Scaling ETERNA Rules Engine to $REPLICAS replicas"

# Scale deployment
kubectl scale deployment/eterna-rules-backend --replicas=$REPLICAS -n eterna-rules

# Wait for scaling
kubectl rollout status deployment/eterna-rules-backend -n eterna-rules

# Check status
kubectl get pods -n eterna-rules -l app=eterna-rules-backend

echo "✅ Scaling completed"
```

### Monitoreo de Health Checks

```bash
#!/bin/bash
# scripts/health_monitor.sh
# Ejecutar cada 5 minutos vía cron

ENDPOINTS=(
    "https://api.eterna.com/health"
    "https://api.eterna.com/rules?limit=1"
)

for endpoint in "${ENDPOINTS[@]}"; do
    if ! curl -f -s "$endpoint" > /dev/null; then
        echo "❌ Health check failed for $endpoint"
        # Notificar a PagerDuty/Slack
        curl -X POST $PAGERDUTY_INTEGRATION_URL \
            -H "Content-Type: application/json" \
            -d "{\"routing_key\":\"$PAGERDUTY_KEY\",\"event_action\":\"trigger\",\"payload\":{\"summary\":\"ETERNA Rules Engine health check failed\",\"source\":\"$endpoint\",\"severity\":\"critical\"}}"
    else
        echo "✅ Health check passed for $endpoint"
    fi
done
```

### Backup y Restore Procedures

```bash
#!/bin/bash
# scripts/backup_restore.sh

function backup_database() {
    local backup_name="eterna_rules_$(date +%Y%m%d_%H%M%S)"
    
    kubectl exec -n eterna-rules deployment/postgres -- \
        pg_dump -U eterna_user -Fc eterna_rules_prod > "$backup_name.dump"
    
    # Subir a S3
    aws s3 cp "$backup_name.dump" s3://eterna-backups/database/
    
    echo "Backup completed: $backup_name.dump"
}

function restore_database() {
    local backup_file=$1
    if [ -z "$backup_file" ]; then
        echo "Usage: restore_database <backup_file>"
        return 1
    fi
    
    echo "⚠️  This will restore database from $backup_file"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled"
        return 1
    fi
    
    # Descargar backup
    aws s3 cp "s3://eterna-backups/database/$backup_file" ./
    
    # Scale down application
    kubectl scale deployment/eterna-rules-backend --replicas=0 -n eterna-rules
    
    # Restore
    kubectl exec -n eterna-rules deployment/postgres -- \
        pg_restore -U eterna_user -d eterna_rules_prod -c "$backup_file"
    
    # Scale up application
    kubectl scale deployment/eterna-rules-backend --replicas=3 -n eterna-rules
    
    echo "✅ Database restored from $backup_file"
}

case "$1" in
    backup)
        backup_database
        ;;
    restore)
        restore_database "$2"
        ;;
    *)
        echo "Usage: $0 {backup|restore} [backup_file]"
        exit 1
        ;;
esac
```

---

## Troubleshooting

### Problemas Comunes

#### 1. Pods en CrashLoopBackOff

```bash
# Diagnosticar
kubectl describe pod -n eterna-rules -l app=eterna-rules-backend
kubectl logs -n eterna-rules -l app=eterna-rules-backend --previous

# Posibles causas:
# - Configuración de base de datos incorrecta
# - Secrets no montados correctamente
# - Health check failing
# - Migraciones pendientes
```

#### 2. High Memory Usage

```bash
# Verificar uso de memoria
kubectl top pods -n eterna-rules

# Verificar métricas detalladas
kubectl exec -n eterna-rules deployment/eterna-rules-backend -- \
    python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"

# Posibles soluciones:
# - Aumentar límites de memoria
# - Optimizar queries de base de datos
# - Implementar cache con TTL
```

#### 3. Database Connection Issues

```bash
# Test conectividad
kubectl exec -n eterna-rules deployment/eterna-rules-backend -- \
    python -c "from backend.rules_engine.persistence import get_session; print('DB OK')"

# Verificar secrets
kubectl get secret eterna-rules-secrets -n eterna-rules -o yaml

# Verificar network policy
kubectl describe networkpolicy -n eterna-rules
```

#### 4. Slow API Responses

```bash
# Verificar métricas de latencia
curl -s https://api.eterna.com/metrics | grep evaluation_duration

# Verificar queries lentas en PostgreSQL
kubectl exec -n database deployment/postgres -- \
    psql -U eterna_user -d eterna_rules_prod \
    -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

### Emergency Contacts

| Rol | Contacto | Disponibilidad |
|-----|----------|----------------|
| DevOps Lead | devops-lead@eterna.com | 24/7 |
| Backend Lead | backend-lead@eterna.com | Business hours |
| Database Admin | dba@eterna.com | On-call rotation |
| Product Owner | product@eterna.com | Business hours |

### Escalation Matrix

1. **P0 (Critical)**: Sistema completamente down
   - Notificar: DevOps Lead inmediatamente
   - SLA: Respuesta en 15 minutos

2. **P1 (High)**: Funcionalidad principal afectada
   - Notificar: DevOps Lead + Backend Lead
   - SLA: Respuesta en 1 hora

3. **P2 (Medium)**: Funcionalidad secundaria afectada
   - Notificar: Backend Lead durante horas de negocio
   - SLA: Respuesta en 4 horas

4. **P3 (Low)**: Problemas menores o mejoras
   - Crear ticket en sistema de tracking
   - SLA: Respuesta en 24 horas
