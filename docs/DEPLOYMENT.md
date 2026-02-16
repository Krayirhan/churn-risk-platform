# Deployment Guide

This guide covers deployment strategies for the Telco Customer Churn Risk Platform across different environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Production Checklist](#production-checklist)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS, or Windows 10/11
- **Python**: 3.10 or higher
- **RAM**: Minimum 4GB, recommended 8GB
- **Disk Space**: 2GB for code + models + logs
- **Network**: Internet connection for package installation

### Software Dependencies

- Git
- Docker (optional, for containerized deployment)
- Docker Compose (optional)
- Make (optional, for automation)

---

## Local Development

### Step 1: Clone Repository

```bash
git clone https://github.com/Krayirhan/churn-risk-platform.git
cd churn-risk-platform
```

### Step 2: Create Virtual Environment

**Windows**:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux/Mac**:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies (optional)
pip install -r requirements-dev.txt
```

### Step 4: Configure Environment

Create `.env` file (optional):
```env
# Application settings
APP_NAME=churn-risk-platform
APP_VERSION=0.1.0
ENVIRONMENT=development

# API settings
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Model settings
MODEL_PATH=artifacts/model_trainer
DATA_PATH=data
LOGS_PATH=logs

# Monitoring settings
DRIFT_CHECK_INTERVAL_HOURS=24
RETRAIN_THRESHOLD=0.05
ALERT_EMAIL=alerts@example.com
```

### Step 5: Train Initial Model

```bash
python main.py --train
```

**Expected Output**:
```
[INFO] Data ingestion completed: 7043 samples
[INFO] Data transformation completed: preprocessor saved
[INFO] Model training completed: XGBoost selected
[INFO] Model evaluation: Accuracy=0.8127, ROC AUC=0.8501
[SUCCESS] Training pipeline completed successfully
```

### Step 6: Start API Server

```bash
python main.py --serve
```

Or with uvicorn directly:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Step 7: Verify Installation

Open browser: `http://localhost:8000/docs`

Test health endpoint:
```bash
curl http://localhost:8000/health
```

---

## Docker Deployment

### Step 1: Build Docker Image

```bash
docker build -t churn-risk-platform:latest .
```

**Build with specific version**:
```bash
docker build -t churn-risk-platform:0.1.0 .
```

**Build arguments** (optional):
```bash
docker build \
  --build-arg PYTHON_VERSION=3.10 \
  --build-arg APP_VERSION=0.1.0 \
  -t churn-risk-platform:latest .
```

### Step 2: Run Container

**Basic run**:
```bash
docker run -d \
  --name churn-api \
  -p 8000:8000 \
  churn-risk-platform:latest
```

**With volume mounts** (persist data):
```bash
docker run -d \
  --name churn-api \
  -p 8000:8000 \
  -v $(pwd)/artifacts:/app/artifacts \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  churn-risk-platform:latest
```

**With environment variables**:
```bash
docker run -d \
  --name churn-api \
  -p 8000:8000 \
  -e API_HOST=0.0.0.0 \
  -e API_PORT=8000 \
  -e ENVIRONMENT=production \
  churn-risk-platform:latest
```

### Step 3: Verify Container

```bash
# Check container status
docker ps

# View logs
docker logs churn-api

# Test API
curl http://localhost:8000/health
```

### Step 4: Docker Compose (Recommended)

**Start services**:
```bash
docker-compose up -d
```

**View logs**:
```bash
docker-compose logs -f
```

**Stop services**:
```bash
docker-compose down
```

**Update and restart**:
```bash
docker-compose pull
docker-compose up -d --force-recreate
```

### Docker Compose Configuration

The included `docker-compose.yml` provides:
- API service with health checks
- Volume mounts for persistence
- Network configuration
- Environment variable management
- Restart policies

---

## Cloud Deployment

### AWS Deployment

#### Option 1: AWS EC2

1. **Launch EC2 Instance**:
   - AMI: Ubuntu 20.04 LTS
   - Instance Type: t3.medium (2 vCPU, 4GB RAM)
   - Security Group: Allow inbound on port 8000

2. **SSH to instance**:
   ```bash
   ssh -i your-key.pem ubuntu@ec2-instance-ip
   ```

3. **Install Docker**:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker ubuntu
   ```

4. **Deploy application**:
   ```bash
   git clone https://github.com/Krayirhan/churn-risk-platform.git
   cd churn-risk-platform
   docker-compose up -d
   ```

5. **Configure nginx reverse proxy** (optional):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

#### Option 2: AWS ECS (Elastic Container Service)

1. **Push image to ECR**:
   ```bash
   aws ecr create-repository --repository-name churn-risk-platform
   
   $(aws ecr get-login --no-include-email)
   
   docker tag churn-risk-platform:latest \
     123456789.dkr.ecr.us-east-1.amazonaws.com/churn-risk-platform:latest
   
   docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/churn-risk-platform:latest
   ```

2. **Create ECS Task Definition** (JSON):
   ```json
   {
     "family": "churn-risk-platform",
     "containerDefinitions": [{
       "name": "api",
       "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/churn-risk-platform:latest",
       "memory": 2048,
       "cpu": 1024,
       "portMappings": [{
         "containerPort": 8000,
         "protocol": "tcp"
       }],
       "environment": [
         {"name": "ENVIRONMENT", "value": "production"}
       ]
     }]
   }
   ```

3. **Create ECS Service** with load balancer

#### Option 3: AWS Lambda + API Gateway (Serverless)

For serverless deployment, use Mangum adapter:

```python
# lambda_handler.py
from mangum import Mangum
from app import app

handler = Mangum(app)
```

Package and deploy with AWS SAM or Serverless Framework.

---

### Google Cloud Platform (GCP)

#### Cloud Run Deployment

1. **Build and push to Container Registry**:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/churn-risk-platform
   ```

2. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy churn-risk-platform \
     --image gcr.io/PROJECT_ID/churn-risk-platform \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2
   ```

3. **Access service**:
   ```
   https://churn-risk-platform-xxxxx-uc.a.run.app
   ```

---

### Azure Deployment

#### Azure Container Instances

```bash
az container create \
  --resource-group churn-risk-rg \
  --name churn-api \
  --image churn-risk-platform:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --ip-address Public \
  --environment-variables ENVIRONMENT=production
```

#### Azure App Service

```bash
az webapp create \
  --resource-group churn-risk-rg \
  --plan churn-app-plan \
  --name churn-risk-api \
  --deployment-container-image-name churn-risk-platform:latest
```

---

### Kubernetes Deployment

**Deployment manifest** (`k8s/deployment.yaml`):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: churn-risk-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: churn-risk-platform
  template:
    metadata:
      labels:
        app: churn-risk-platform
    spec:
      containers:
      - name: api
        image: churn-risk-platform:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: churn-risk-service
spec:
  type: LoadBalancer
  selector:
    app: churn-risk-platform
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

**Deploy**:
```bash
kubectl apply -f k8s/deployment.yaml
kubectl get pods
kubectl get services
```

---

## Production Checklist

### Security

- [ ] Enable HTTPS/TLS with valid certificates
- [ ] Implement authentication (API keys, OAuth2, JWT)
- [ ] Add rate limiting to prevent abuse
- [ ] Configure CORS properly (restrict origins)
- [ ] Use secrets management (AWS Secrets Manager, Azure Key Vault)
- [ ] Enable firewall rules (only necessary ports)
- [ ] Regular security updates for dependencies
- [ ] Implement input validation and sanitization
- [ ] Add audit logging for predictions

### Performance

- [ ] Configure uvicorn workers: `--workers 4`
- [ ] Enable caching for model loading
- [ ] Use connection pooling for databases (if applicable)
- [ ] Optimize model inference (quantization, ONNX runtime)
- [ ] Set up CDN for static assets
- [ ] Configure load balancing for horizontal scaling
- [ ] Implement request queueing for batch processing
- [ ] Monitor memory usage and optimize

### Reliability

- [ ] Set up health checks and readiness probes
- [ ] Configure auto-restart policies
- [ ] Implement circuit breakers
- [ ] Set up database backups (artifacts, logs)
- [ ] Configure log rotation
- [ ] Add error tracking (Sentry, Rollbar)
- [ ] Implement retry logic for failed predictions
- [ ] Set up alerting for critical errors

### Monitoring

- [ ] Application metrics (Prometheus + Grafana)
- [ ] API performance monitoring (response times, error rates)
- [ ] Model performance tracking (accuracy, drift)
- [ ] Infrastructure monitoring (CPU, memory, disk)
- [ ] Log aggregation (ELK Stack, CloudWatch)
- [ ] Set up dashboards for key metrics
- [ ] Configure alerts (Slack, PagerDuty, email)
- [ ] Track business metrics (predictions/day, churn rate trends)

### Compliance

- [ ] GDPR compliance (data privacy, right to deletion)
- [ ] Data retention policies
- [ ] Model explainability documentation
- [ ] Bias and fairness auditing
- [ ] Terms of service and privacy policy
- [ ] Data anonymization for logs
- [ ] Regular compliance audits

---

## Monitoring & Maintenance

### Application Monitoring

**Prometheus metrics endpoint** (future enhancement):
```python
# Add to app.py
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

Access metrics: `http://localhost:8000/metrics`

### Model Retraining Schedule

Set up cron job for automated retraining:

```bash
# crontab -e
0 2 * * 0 cd /app && python main.py --retrain >> /app/logs/retrain.log 2>&1
```

Or use Airflow/Prefect for workflow orchestration.

### Log Management

**Log rotation configuration** (`/etc/logrotate.d/churn-risk-platform`):
```
/app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 app app
    sharedscripts
    postrotate
        docker-compose restart > /dev/null 2>&1 || true
    endscript
}
```

### Database Backups

Backup artifacts and logs:
```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

tar -czf $BACKUP_DIR/artifacts.tar.gz artifacts/
tar -czf $BACKUP_DIR/logs.tar.gz logs/

# Upload to S3
aws s3 cp $BACKUP_DIR s3://churn-backups/ --recursive
```

Run daily:
```bash
0 3 * * * /app/scripts/backup.sh
```

---

## Troubleshooting

### Issue: Container fails to start

**Symptoms**: Container exits immediately

**Diagnosis**:
```bash
docker logs churn-api
docker inspect churn-api
```

**Common causes**:
- Missing model files in artifacts/
- Port 8000 already in use
- Insufficient memory

**Solutions**:
```bash
# Train model first
docker run -v $(pwd):/app churn-risk-platform python main.py --train

# Use different port
docker run -p 8080:8000 churn-risk-platform

# Increase memory limit
docker run --memory=4g churn-risk-platform
```

---

### Issue: API returns 503 Service Unavailable

**Symptoms**: `/health` endpoint returns 503

**Diagnosis**:
```bash
curl -v http://localhost:8000/health
docker exec -it churn-api ls artifacts/model_trainer/
```

**Cause**: Model not loaded (missing artifacts)

**Solution**:
```bash
# Re-train model
docker exec -it churn-api python main.py --train

# Or mount pre-trained model
docker run -v /path/to/artifacts:/app/artifacts churn-risk-platform
```

---

### Issue: Predictions are slow

**Symptoms**: High response times (>1s)

**Diagnosis**:
```bash
# Check resource usage
docker stats churn-api

# Profile API
pip install py-spy
py-spy record -o profile.svg -- python main.py --serve
```

**Solutions**:
- Increase worker count: `uvicorn app:app --workers 4`
- Optimize model (ONNX, quantization)
- Add caching for frequent predictions
- Scale horizontally with load balancer

---

### Issue: Out of memory errors

**Symptoms**: Container killed by OOM killer

**Diagnosis**:
```bash
dmesg | grep -i "out of memory"
docker stats
```

**Solutions**:
```bash
# Increase Docker memory
docker run --memory=8g churn-risk-platform

# Optimize model loading (lazy loading)
# Clear logs regularly
# Use batch prediction for large datasets
```

---

### Issue: Model drift detected

**Symptoms**: High drift scores in `/monitoring/drift`

**Response**:
1. Investigate drift details:
   ```bash
   python main.py --check-drift
   ```

2. Analyze feature distributions:
   ```python
   from src.components.drift_detector import DriftDetector
   detector = DriftDetector()
   report = detector.detect_drift(new_data)
   ```

3. Trigger retraining if needed:
   ```bash
   python main.py --retrain
   ```

4. Review and deploy new model

---

## Performance Benchmarks

**Hardware**: AWS EC2 t3.medium (2 vCPU, 4GB RAM)

| Metric | Value |
|--------|-------|
| Single prediction latency | 8-15ms |
| Batch prediction (100 customers) | 120-180ms |
| Throughput (with 4 workers) | ~500 req/s |
| Model loading time | 2-3s |
| Memory usage (idle) | 180MB |
| Memory usage (under load) | 350MB |

---

## Support and Resources

- **Documentation**: [README.md](../README.md)
- **API Reference**: [API.md](API.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **GitHub Issues**: [https://github.com/Krayirhan/churn-risk-platform/issues](https://github.com/Krayirhan/churn-risk-platform/issues)
- **CI/CD Pipeline**: [https://github.com/Krayirhan/churn-risk-platform/actions](https://github.com/Krayirhan/churn-risk-platform/actions)

---

## Next Steps

After successful deployment:

1. Configure monitoring and alerting
2. Set up automated backups
3. Implement authentication and rate limiting
4. Configure log aggregation
5. Set up retraining schedule
6. Perform load testing
7. Document runbooks for common incidents
8. Train operations team

For production support, create detailed runbooks for:
- Incident response procedures
- Rollback procedures
- Scaling procedures
- Disaster recovery procedures
