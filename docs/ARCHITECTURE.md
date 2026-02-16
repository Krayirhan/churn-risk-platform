# Architecture Documentation

## Overview

The Telco Customer Churn Risk Platform is built on a modular, production-ready architecture that follows MLOps best practices. This document provides a comprehensive view of the system design, component interactions, and architectural decisions.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CLIENT APPLICATIONS                               │
│  (Web Apps, Mobile Apps, Backend Services, Dashboards)                  │
└────────────┬─────────────────────────────────────────────────┬──────────┘
             │                                                   │
             │ HTTP/JSON                                         │ HTTP/JSON
             │                                                   │
┌────────────▼─────────────────────────────────────────────────▼──────────┐
│                           API GATEWAY / LOAD BALANCER                    │
│                        (nginx, AWS ALB, Kubernetes Ingress)              │
└────────────┬─────────────────────────────────────────────────┬──────────┘
             │                                                   │
    ┌────────▼────────┐                                ┌────────▼────────┐
    │  Prediction API  │                                │  Monitoring API  │
    │   (FastAPI)      │                                │   (FastAPI)      │
    │                  │                                │                  │
    │ • /predict       │                                │ • /drift         │
    │ • /predict/batch │                                │ • /predictions   │
    │ • /health        │                                │ • /retrain       │
    │ • /model-info    │                                │ • /status        │
    └────────┬─────────┘                                └────────┬─────────┘
             │                                                   │
    ┌────────▼─────────────────────────────────────────────────▼─────────┐
    │                        CORE ML PIPELINE                             │
    │                                                                      │
    │  ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐      │
    │  │ Predict       │  │ Train          │  │ Retrain          │      │
    │  │ Pipeline      │  │ Pipeline       │  │ Pipeline         │      │
    │  └───────┬───────┘  └────┬───────────┘  └────────┬─────────┘      │
    │          │               │                        │                │
    │  ┌───────▼───────────────▼────────────────────────▼─────────┐      │
    │  │              COMPONENT LAYER                              │      │
    │  │                                                            │      │
    │  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  │      │
    │  │  │ Data         │  │ Data          │  │ Model        │  │      │
    │  │  │ Ingestion    │  │ Transform     │  │ Trainer      │  │      │
    │  │  └──────────────┘  └───────────────┘  └──────────────┘  │      │
    │  │                                                            │      │
    │  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  │      │
    │  │  │ Model        │  │ Drift         │  │ Prediction   │  │      │
    │  │  │ Evaluation   │  │ Detector      │  │ Logger       │  │      │
    │  │  └──────────────┘  └───────────────┘  └──────────────┘  │      │
    │  │                                                            │      │
    │  │  ┌──────────────────────────────────────────────┐        │      │
    │  │  │ Model Monitor                                 │        │      │
    │  │  └──────────────────────────────────────────────┘        │      │
    │  └────────────────────────────────────────────────────────┘        │
    └──────────────────────────────────┬──────────────────────────────────┘
                                       │
    ┌──────────────────────────────────▼──────────────────────────────────┐
    │                        STORAGE LAYER                                 │
    │                                                                       │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
    │  │ Model        │  │ Artifacts    │  │ Logs         │              │
    │  │ Registry     │  │ (Data,       │  │ (Predictions,│              │
    │  │ (.pkl files) │  │  Preprocessor│  │  Monitoring) │              │
    │  └──────────────┘  └──────────────┘  └──────────────┘              │
    │                                                                       │
    │  ┌──────────────┐  ┌──────────────┐                                │
    │  │ Config       │  │ Raw Data     │                                │
    │  │ (YAML)       │  │ (CSV)        │                                │
    │  └──────────────┘  └──────────────┘                                │
    └───────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. API Layer

**Technology**: FastAPI + Uvicorn ASGI

**Responsibilities**:
- HTTP request handling
- Input validation (Pydantic models)
- Authentication & authorization (future)
- Rate limiting (future)
- CORS handling
- API documentation (OpenAPI/Swagger)

**Key Components**:
- `app.py` - Main FastAPI application
- Pydantic models for request/response schemas
- Middleware for cross-cutting concerns
- Lifecycle management (startup/shutdown)

**Endpoints**:
```
Core Prediction:
├── GET  /                → Welcome & info
├── GET  /health          → Health check
├── GET  /model-info      → Model metadata
├── POST /predict         → Single prediction
└── POST /predict/batch   → Batch predictions

Monitoring:
├── GET  /monitoring/drift         → Drift analysis
├── GET  /monitoring/predictions   → Prediction logs
├── GET  /monitoring/status        → System status
├── POST /monitoring/retrain       → Trigger retraining
└── GET  /monitoring/retrain/history → Retrain history
```

---

### 2. Pipeline Layer

**Pipelines** orchestrate multi-step workflows by composing components.

#### Training Pipeline (`src/pipeline/train_pipeline.py`)

**Flow**:
```
Data Ingestion → Data Transformation → Model Training → Model Evaluation
```

**Outputs**:
- Train/test datasets
- Preprocessor object (sklearn Pipeline)
- Trained models (XGBoost, RF, AdaBoost)
- Evaluation reports (JSON)

**Error Handling**: Component-level exceptions with rollback

#### Prediction Pipeline (`src/pipeline/predict_pipeline.py`)

**Flow**:
```
Load Model + Preprocessor → Transform Input → Predict → Format Response
```

**Features**:
- Lazy loading (models cached in memory)
- Batch prediction support
- Confidence scoring
- Prediction logging integration

#### Retrain Pipeline (`src/pipeline/retrain_pipeline.py`)

**Flow**:
```
Check Drift → Retrain Model → Evaluate → Compare → Deploy (if better)
```

**Decision Logic**:
```python
if new_accuracy > old_accuracy + threshold:
    deploy_new_model()
else:
    keep_old_model()
```

**Outputs**: Retraining history with metrics comparison

---

### 3. Component Layer

Modular, reusable components implementing single responsibilities.

#### Data Ingestion (`src/components/data_ingestion.py`)

**Responsibilities**:
- Load raw data from CSV
- Perform train/test split (stratified)
- Validate data integrity
- Save split datasets

**Configuration**:
```yaml
data_ingestion:
  test_size: 0.2
  random_state: 42
  stratify: true
```

**Outputs**:
- `artifacts/data_ingestion/train.csv`
- `artifacts/data_ingestion/test.csv`
- `artifacts/data_ingestion/raw.csv`

#### Data Transformation (`src/components/data_transformation.py`)

**Responsibilities**:
- Handle missing values (imputation)
- Cap outliers (IQR method)
- Encode categorical features (OneHot, Label)
- Scale numerical features (StandardScaler)
- Create preprocessing pipeline

**Pipeline Structure**:
```
Numerical Features:
├── Imputer (median) → Outlier Capper → StandardScaler

Categorical Features:
├── Imputer (mode) → OneHotEncoder
```

**Outputs**:
- `artifacts/data_transformation/preprocessor.pkl`
- Transformed train/test arrays

#### Model Trainer (`src/components/model_trainer.py`)

**Responsibilities**:
- Train multiple algorithms
- Hyperparameter tuning (GridSearchCV)
- Model selection based on metrics
- Model serialization

**Algorithms**:
```python
models = {
    "XGBoost": XGBClassifier,
    "Random Forest": RandomForestClassifier,
    "AdaBoost": AdaBoostClassifier
}
```

**Selection Criteria**:
1. Must exceed accuracy threshold (default: 0.70)
2. Highest accuracy among qualifying models
3. If tie, prefer best ROC AUC

**Outputs**:
- `artifacts/model_trainer/model.pkl` (best model)
- Hyperparameter search results

#### Model Evaluation (`src/components/model_evaluation.py`)

**Responsibilities**:
- Calculate classification metrics
- Generate confusion matrix
- Compute feature importance
- Create evaluation report

**Metrics**:
- Accuracy
- Precision
- Recall
- F1 Score
- ROC AUC Score

**Outputs**:
- `artifacts/model_trainer/model_report.json`
- Feature importance rankings

#### Drift Detector (`src/components/drift_detector.py`)

**Responsibilities**:
- Detect distribution shifts in features
- Calculate statistical tests (KS, PSI)
- Generate drift reports
- Trigger alerts

**Statistical Tests**:

1. **Kolmogorov-Smirnov Test**:
   - Measures maximum distance between CDFs
   - Threshold: KS > 0.15 indicates drift

2. **Population Stability Index (PSI)**:
   ```
   PSI = Σ (actual% - expected%) × ln(actual% / expected%)
   ```
   - PSI < 0.1: No significant change
   - PSI 0.1-0.25: Moderate drift
   - PSI > 0.25: Significant drift

**Alert Levels**:
- `WARNING`: 0.15 < score < 0.25
- `CRITICAL`: score ≥ 0.25

#### Prediction Logger (`src/components/prediction_logger.py`)

**Responsibilities**:
- Log all predictions with metadata
- Query prediction history
- Provide analytics on prediction patterns

**Log Format**:
```json
{
  "prediction_id": "pred_20260216_103045_a7f3c2",
  "timestamp": "2026-02-16T10:30:45Z",
  "prediction": "Yes",
  "churn_probability": 0.73,
  "risk_level": "HIGH",
  "model_version": "0.1.0",
  "input_hash": "7f3a9b...",
  "inference_time_ms": 12.5
}
```

**Storage**: JSON files in `logs/predictions/`

#### Model Monitor (`src/components/model_monitor.py`)

**Responsibilities**:
- Orchestrate drift detection
- Monitor prediction quality
- Generate comprehensive reports
- Manage alerting

**Monitoring Workflow**:
```
Load Recent Predictions → Check Drift → Analyze Performance → Alert if Needed
```

**Reports Include**:
- Drift status per feature
- Prediction distribution
- Model health indicators
- Recommended actions

---

### 4. Storage Layer

#### Artifact Storage

```
artifacts/
├── data_ingestion/
│   ├── train.csv           # Training dataset
│   ├── test.csv            # Test dataset
│   └── raw.csv             # Raw input data
│
├── data_transformation/
│   └── preprocessor.pkl    # Sklearn Pipeline object
│
└── model_trainer/
    ├── model.pkl           # Best trained model
    └── model_report.json   # Evaluation metrics
```

#### Configuration Storage

```
configs/
├── training_config.yaml    # Model training parameters
└── monitoring.yaml         # Drift & alert thresholds
```

#### Log Storage

```
logs/
├── application.log         # General application logs
└── predictions/
    └── predictions_YYYYMMDD.json  # Daily prediction logs
```

---

## Data Flow

### Training Flow

```
1. User triggers: python main.py --train
                  ↓
2. Data Ingestion Component
   - Load data/Telco-Customer-Churn.csv
   - Split train/test (80/20)
   - Save to artifacts/data_ingestion/
                  ↓
3. Data Transformation Component
   - Create preprocessing pipeline
   - Fit on training data
   - Transform train & test
   - Save preprocessor.pkl
                  ↓
4. Model Trainer Component
   - Train XGBoost, RF, AdaBoost
   - GridSearch hyperparameters
   - Select best model
   - Save model.pkl
                  ↓
5. Model Evaluation Component
   - Test on holdout set
   - Calculate metrics
   - Generate report
   - Save model_report.json
                  ↓
6. Training Complete
   - Model ready for serving
```

### Prediction Flow

```
1. Client sends POST /predict
   {customer_data}
                  ↓
2. FastAPI validates input (Pydantic)
                  ↓
3. Prediction Pipeline
   - Load model.pkl (if not cached)
   - Load preprocessor.pkl (if not cached)
   - Transform input features
   - Generate prediction + probability
                  ↓
4. Response Formatter
   - Add metadata (model version, prediction ID)
   - Calculate risk level (LOW/MEDIUM/HIGH)
   - Format JSON response
                  ↓
5. Prediction Logger (async)
   - Log to predictions JSON
   - Store for drift monitoring
                  ↓
6. Return JSON response to client
```

### Monitoring & Retraining Flow

```
1. Scheduled Job (cron / Airflow)
                  ↓
2. Model Monitor checks drift
   - Load recent predictions
   - Compare to training distribution
   - Calculate KS & PSI scores
                  ↓
3. If drift detected (score > threshold)
                  ↓
4. Trigger Retrain Pipeline
   - Re-run full training pipeline
   - Evaluate new model
   - Compare to current model
                  ↓
5. If new model better (accuracy + threshold)
   - Replace model.pkl
   - Update model_report.json
   - Log retrain history
                  ↓
6. Alert via configured channels
   - Email
   - Slack
   - Dashboard
                  ↓
7. Continue monitoring
```

---

## Design Patterns

### 1. Dependency Injection

Components receive configuration via constructors:

```python
class ModelTrainer:
    def __init__(self, config: dict):
        self.config = config
        self.expected_accuracy = config['expected_accuracy']
```

### 2. Pipeline Pattern

Orchestrators compose components:

```python
def train_pipeline():
    ingestion = DataIngestion()
    transformation = DataTransformation()
    trainer = ModelTrainer()
    
    train_data = ingestion.initiate()
    arrays = transformation.initiate(train_data)
    model = trainer.initiate(arrays)
```

### 3. Strategy Pattern

Model selection via pluggable algorithms:

```python
models = {
    "XGBoost": XGBClassifier(params),
    "Random Forest": RandomForestClassifier(params)
}
best_model = select_best(models, X_test, y_test)
```

### 4. Singleton Pattern

Lazy model loading with caching:

```python
class PredictPipeline:
    _model = None
    _preprocessor = None
    
    def load_model(self):
        if self._model is None:
            self._model = load_object("model.pkl")
        return self._model
```

### 5. Factory Pattern

Exception creation:

```python
raise CustomException(e, sys)  # Auto-captures context
```

---

## Technology Stack

### Core Framework
- **Python 3.10**: Primary language
- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation

### Machine Learning
- **scikit-learn**: Preprocessing, evaluation
- **XGBoost**: Gradient boosting
- **pandas**: Data manipulation
- **numpy**: Numerical operations

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Local orchestration
- **GitHub Actions**: CI/CD
- **pytest**: Testing framework
- **flake8**: Linting

### Storage
- **pickle**: Model serialization
- **JSON**: Logs, reports, config
- **YAML**: Human-readable config
- **CSV**: Dataset storage

---

## Scalability Considerations

### Horizontal Scaling

**API Layer**:
```
Load Balancer
    ↓
├── API Instance 1 (Docker container)
├── API Instance 2 (Docker container)
└── API Instance N (Docker container)
```

**Configuration**:
- Stateless API (no session storage)
- Shared storage for models (EFS, S3)
- Distributed caching (Redis) for hot models

### Vertical Scaling

**Resource Allocation**:
- CPU: 2-4 cores for model inference
- RAM: 4-8GB for model + data in memory
- Disk: SSD for fast model loading

### Batch Processing

For high-throughput scenarios:
- Message queue (RabbitMQ, Kafka)
- Batch predictions (100-1000 records)
- Async processing with Celery

---

## Security Architecture

### Current State
- Open API (no authentication)
- Input validation via Pydantic
- CORS middleware

### Production Requirements

**Authentication**:
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@app.post("/predict")
async def predict(
    data: CustomerInput,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    verify_token(credentials.credentials)
    ...
```

**Rate Limiting**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/predict")
@limiter.limit("100/minute")
async def predict(...):
    ...
```

**Secrets Management**:
- Use environment variables
- AWS Secrets Manager / Azure Key Vault
- Never commit secrets to git

---

## Disaster Recovery

### Backup Strategy

**Models & Artifacts**:
- Daily backups to cloud storage (S3, Azure Blob)
- Versioned model registry
- Retention: 30 days

**Logs**:
- Centralized log aggregation (ELK, CloudWatch)
- Retention: 90 days

**Configuration**:
- Version controlled in git
- Automated deployment via CI/CD

### Recovery Procedures

**Model Rollback**:
```bash
# Restore previous model version
aws s3 cp s3://backups/model_v0.0.9.pkl artifacts/model_trainer/model.pkl
docker-compose restart
```

**Data Recovery**:
```bash
# Restore from backup
tar -xzf backups/artifacts_20260215.tar.gz
```

---

## Performance Optimization

### Model Inference

**Current**: ~12ms per prediction

**Optimizations**:
1. **Model quantization**: Reduce model size
2. **ONNX Runtime**: Faster inference engine
3. **Caching**: Cache frequent predictions
4. **Batch inference**: Process multiple records together

### API Response Time

**Current**: ~15ms end-to-end

**Optimizations**:
1. **Connection pooling**: Reuse connections
2. **Async logging**: Non-blocking prediction logging
3. **Compression**: gzip response bodies
4. **CDN**: Cache static assets

---

## Monitoring & Observability

### Application Metrics

- Request rate (req/s)
- Response time (p50, p95, p99)
- Error rate (%)
- Model prediction distribution

### Model Metrics

- Drift score (daily)
- Prediction accuracy (on labeled data)
- Feature importance changes
- Churn rate trends

### Infrastructure Metrics

- CPU utilization (%)
- Memory usage (MB)
- Disk I/O (MB/s)
- Network traffic (Mbps)

---

## Future Enhancements

### Phase 6: Advanced Features

1. **Model Explainability**:
   - SHAP values for predictions
   - LIME for local explanations
   - Feature contribution visualization

2. **A/B Testing**:
   - Multi-model serving
   - Traffic splitting
   - Performance comparison

3. **Real-time Retraining**:
   - Online learning
   - Incremental updates
   - Streaming data ingestion

4. **Advanced Monitoring**:
   - Anomaly detection in predictions
   - Performance degradation alerts
   - Automated model rollback

### Phase 7: Enterprise Features

1. **Multi-tenancy**: Separate models per customer
2. **Feature Store**: Centralized feature management
3. **Model Governance**: Approval workflows, audit trails
4. **SLA Guarantees**: 99.9% uptime, <100ms p99 latency

---

## References

- **MLOps Best Practices**: [ml-ops.org](https://ml-ops.org/)
- **FastAPI Documentation**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
- **Scikit-learn Pipeline**: [sklearn Pipeline](https://scikit-learn.org/stable/modules/compose.html)
- **Model Monitoring**: [Evidently AI](https://evidentlyai.com/)

---

## Glossary

- **Artifact**: Generated output from pipeline stages (models, data, reports)
- **Drift**: Statistical change in data distribution over time
- **Pipeline**: Orchestrated sequence of ML operations
- **Preprocessor**: Transformation logic (scaling, encoding) saved as object
- **PSI**: Population Stability Index, drift metric
- **ROC AUC**: Area Under Receiver Operating Characteristic curve
- **Threshold**: Minimum acceptable model performance metric

---

## Contact & Contribution

For architecture questions or suggestions:
- **GitHub Issues**: [github.com/Krayirhan/churn-risk-platform/issues](https://github.com/Krayirhan/churn-risk-platform/issues)
- **Pull Requests**: Welcome! Follow [CONTRIBUTING.md](../CONTRIBUTING.md)
