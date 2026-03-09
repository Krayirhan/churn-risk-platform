# Churn Risk Platform

End-to-end machine learning platform for predicting customer churn, serving real-time predictions via REST API, monitoring data drift, and supporting automated retraining — designed with production-grade architecture.

[![CI — Lint, Test & Build](https://github.com/Krayirhan/churn-risk-platform/workflows/CI%20%E2%80%94%20Lint%2C%20Test%20%26%20Build/badge.svg)](https://github.com/Krayirhan/churn-risk-platform/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker&logoColor=white)](Dockerfile)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-158%20passed-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-85%25-green.svg)](tests/)

---

## Highlights

- **Predicts customer churn** using 4 ML algorithms with automated hyperparameter tuning
- **Serves predictions via REST API** — single and batch (up to 100 customers per request)
- **Monitors data drift** in production using KS test & PSI statistical methods
- **Supports automated retraining** when model performance degrades or drift is detected
- **Full CI/CD pipeline** — lint, test, Docker build, container registry push, GitHub Release
- **Three-tier deployment** — Python ML API + C# API Gateway + Frontend Dashboard

---

## Problem Statement

Customer churn directly impacts revenue, customer lifetime value, and acquisition costs. In the telecom industry, acquiring a new customer costs **5-7x more** than retaining an existing one. Yet most companies identify churned customers **after** they leave — when it is too late.

This platform solves that problem by:

1. **Identifying high-risk customers early** so retention teams can take proactive action
2. **Quantifying churn probability** (0-100%) instead of a simple yes/no classification
3. **Explaining why** a customer is at risk (contract type, billing issues, service gaps)
4. **Detecting model degradation** over time via continuous drift monitoring
5. **Automating the feedback loop** — when data distribution shifts, the model retrains itself

---

## Architecture

<p align="center">
  <img src="docs/images/architecture.png" alt="System Architecture" width="800"/>
</p>

```
Raw Data (CSV)
    |
    v
+----------------+    +-----------------------+    +------------------+    +----------------+
|  Data          |--->|  Data                 |--->|  Model           |--->|  Model         |
|  Ingestion     |    |  Transformation       |    |  Training        |    |  Evaluation    |
|  - CSV load    |    |  - Cleaning           |    |  - GridSearchCV  |    |  - ROC/PR      |
|  - Splitting   |    |  - 10 new features    |    |  - 4 algorithms  |    |  - F1/Recall   |
+----------------+    |  - Scaling/Encoding   |    |  - Best model    |    |  - Confusion   |
                      +-----------------------+    +--------+---------+    +----------------+
                                                            |
                                                   +--------v---------+
                                                   |  artifacts/      |
                                                   |  model.pkl       |
                                                   |  preprocessor    |
                                                   |  metrics.json    |
                                                   +--------+---------+
                                                            |
                      +-------------------------------------+------------------------+
                      |                                     |                        |
              +-------v--------+                   +--------v--------+      +--------v--------+
              |  FastAPI       |                   |  Drift          |      |  Retrain        |
              |  10 endpoints  |                   |  Detector       |      |  Pipeline       |
              |  /predict      |                   |  KS test + PSI  |      |  Auto/Manual    |
              |  /batch        |                   |  Alerting       |      |  Cooldown       |
              +-------+--------+                   +-----------------+      +-----------------+
                      |
           +----------+------------+
           |          |            |
      +----v----+ +---v-----+ +---v-------+
      | Python  | |  C#     | | Frontend  |
      | :8000   | | :5001   | |  :5500    |
      | ML API  | |Gateway  | |Dashboard  |
      +---------+ +---------+ +-----------+
```

**Key design decisions:**
- **Config-driven** — all behavior controlled via YAML files, zero hardcoded values
- **Dual-mode ingestion** — supports both preprocessed (NPZ) and raw (CSV) data sources
- **Lazy loading** — model and preprocessor are loaded on first prediction, not at startup
- **Feature engineering in pipeline** — 10 business-logic features are computed both in training and inference, ensuring consistency

---

## Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **Core Language** | Python 3.10+ | Type hints, dataclasses, modern stdlib |
| **ML Training** | scikit-learn, XGBoost | GridSearchCV with 4 algorithms, class balancing |
| **Data Processing** | pandas, NumPy | Feature engineering, data cleaning |
| **API Framework** | FastAPI + Uvicorn | Async, auto-docs, Pydantic validation |
| **Statistics** | SciPy, StatsModels | KS test for drift, statistical significance testing |
| **Visualization** | Matplotlib, Seaborn, Plotly | ROC/PR curves, confusion matrix, EDA |
| **API Gateway** | C# .NET 10 (ASP.NET Core) | Type-safe forwarding, Swagger, enterprise integration |
| **Frontend** | HTML5, CSS3, JavaScript | Prediction dashboard, system monitoring |
| **Containerization** | Docker, Docker Compose | Multi-container deployment (3 services) |
| **CI/CD** | GitHub Actions | Lint, Test, Build, Push, Release pipeline |
| **Testing** | pytest, pytest-cov, httpx | 158 tests, 85% coverage, unit + integration |
| **Code Quality** | flake8, black, isort, pre-commit | Enforced style, import sorting, hooks |

---

## Installation

### Requirements
- Python 3.10 or higher
- Git
- Docker (optional, for containerized deployment)

### Clone and Setup

```bash
git clone https://github.com/Krayirhan/churn-risk-platform.git
cd churn-risk-platform
```

**Linux / macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Usage

### 1. Train a Model

```bash
python main.py --train
```

This runs the full pipeline: Ingestion, Feature Engineering, GridSearchCV (4 models), Evaluation. Saves `model.pkl` + `preprocessor.pkl` + `metrics.json` to `artifacts/`.

### 2. Start the API

```bash
python main.py --serve
```

Interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI).

### 3. Make a Prediction (CLI)

```bash
python main.py --predict-inline '{
  "tenure": 2,
  "MonthlyCharges": 89.10,
  "Contract": "Month-to-month",
  "InternetService": "Fiber optic",
  "OnlineSecurity": "No",
  "TechSupport": "No",
  "PaymentMethod": "Electronic check"
}'
```

### 4. Run with Docker (all 3 services)

```bash
docker compose up --build
```

| Service | Port | Description |
|---------|------|-------------|
| Python ML API | `localhost:8000` | FastAPI with 10 endpoints |
| C# API Gateway | `localhost:5001` | ASP.NET Core forwarding layer |
| Frontend Dashboard | `localhost:5500` | Web UI for predictions |

### 5. Monitor and Retrain

```bash
# View model health and drift status
python main.py --monitor

# Force retraining via API
curl -X POST http://localhost:8000/monitor/retrain?force=true
```

---

## API Reference

### Single Prediction

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "tenure": 2,
    "MonthlyCharges": 89.10,
    "TotalCharges": 178.20,
    "Contract": "Month-to-month",
    "InternetService": "Fiber optic",
    "OnlineSecurity": "No",
    "TechSupport": "No",
    "PaymentMethod": "Electronic check"
  }'
```

**Response:**
```json
{
  "prediction": 1,
  "churn_probability": 0.82,
  "risk_level": "Yuksek",
  "customerID": "API_USER"
}
```

### Batch Prediction

```bash
curl -X POST http://localhost:8000/predict/batch \
  -H "Content-Type: application/json" \
  -d '{
    "customers": [
      {"tenure": 2, "MonthlyCharges": 89.10, "Contract": "Month-to-month"},
      {"tenure": 48, "MonthlyCharges": 25.0, "Contract": "Two year"}
    ]
  }'
```

### All Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Service health (model loaded, artifacts exist) |
| `GET` | `/model-info` | Active model name and performance metrics |
| `POST` | `/predict` | Single customer churn prediction |
| `POST` | `/predict/batch` | Batch prediction (max 100 per request) |
| `GET` | `/monitor/stats` | Prediction statistics over N days |
| `GET` | `/monitor/drift` | Data drift analysis (KS + PSI) |
| `GET` | `/monitor/health-report` | Full monitoring report |
| `POST` | `/monitor/retrain` | Trigger model retraining |
| `GET` | `/monitor/retrain-history` | Retraining audit log |

> **Interactive docs:** [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)

---

## Model Performance

**Production model: XGBClassifier** — selected by GridSearchCV based on best F1 score on imbalanced data.

| Metric | Score |
|--------|------:|
| **ROC-AUC** | **0.845** |
| **Recall** | **0.791** |
| **PR-AUC** | **0.655** |
| **F1 Score** | **0.632** |
| **Accuracy** | 0.755 |
| **Precision** | 0.526 |

> **Why recall matters most:** On imbalanced churn data (~27% positive class), missing a churning customer is far more costly than a false alarm. This model catches **79% of actual churners** while maintaining a balanced F1 score.

<details>
<summary><strong>Evaluation Charts</strong> (click to expand)</summary>

<br/>

<p align="center">
  <img src="docs/images/model_metrics.png" alt="Model Metrics" width="600"/>
</p>

<p align="center">
  <img src="docs/images/roc_curve.png" alt="ROC Curve" width="450"/>
  <img src="docs/images/pr_curve.png" alt="Precision-Recall Curve" width="450"/>
</p>

<p align="center">
  <img src="docs/images/confusion_matrix.png" alt="Confusion Matrix" width="400"/>
</p>

</details>

---

## Model Explainability

Understanding **why** the model predicts churn is critical for actionable business decisions.

<p align="center">
  <img src="docs/images/feature_importance.png" alt="Feature Importance" width="600"/>
</p>

| Rank | Feature | Business Interpretation |
|------|---------|------------------------|
| 1 | **IsMonthToMonth** | Month-to-month contracts churn ~2x more than yearly contracts |
| 2 | **tenure** | Customers under 12 months tenure are significantly more likely to churn |
| 3 | **LoyaltyIndex** | `log1p(tenure)` — low loyalty score signals disengagement |
| 4 | **RiskScope** | Fiber optic + no security + no tech support = highest churn combination |
| 5 | **ChargeGap** | Gap between current and average charges — billing surprises trigger churn |
| 6 | **IsElectronicCheck** | Electronic check users churn 2.3x more than auto-pay users |
| 7 | **UnitCost** | High cost per add-on service = low perceived value |
| 8 | **TotalCharges** | Low lifetime value = customer has not committed |
| 9 | **MonthlyCharges** | Higher monthly bills correlate with higher churn |
| 10 | **IsPaperless** | Paperless billing customers show 21% higher churn rate |

### Target Distribution

<p align="center">
  <img src="docs/images/churn_distribution.png" alt="Churn Distribution" width="400"/>
</p>

The dataset is **imbalanced** (~73% No Churn, ~27% Churn). We use `class_weight="balanced"` and `scale_pos_weight` to handle this, and optimize for F1/Recall instead of accuracy.

---

## Project Structure

```
churn-risk-platform/
|
+-- app.py                          # FastAPI REST API (10 endpoints, auth, rate limiting)
+-- main.py                         # CLI entry point (train / predict / serve / monitor)
+-- Dockerfile                      # Multi-stage Python container
+-- Dockerfile.csharp               # .NET API Gateway container
+-- Dockerfile.frontend             # nginx:alpine frontend container
+-- docker-compose.yml              # 3-service orchestration
+-- Makefile                        # Task automation (install, test, lint, train, serve, clean)
+-- pyproject.toml                  # PEP 621 project metadata + tool config
|
+-- src/                            # Core application code
|   +-- components/
|   |   +-- data_ingestion.py       #   CSV/NPZ loading, stratified train-test split
|   |   +-- data_transformation.py  #   Cleaning, 10 feature engineering, ColumnTransformer
|   |   +-- model_trainer.py        #   GridSearchCV with 4 algorithms
|   |   +-- model_evaluation.py     #   Metrics calculation, ROC/PR curves, confusion matrix
|   |   +-- drift_detector.py       #   KS test + PSI for drift detection
|   |   +-- prediction_logger.py    #   JSONL daily prediction logging
|   |   +-- model_monitor.py        #   Performance tracking + drift alerts
|   |
|   +-- pipeline/
|   |   +-- train_pipeline.py       #   Ingestion -> Transform -> Train -> Evaluate chain
|   |   +-- predict_pipeline.py     #   Single and batch inference with risk classification
|   |   +-- retrain_pipeline.py     #   Automated retraining with cooldown logic
|   |
|   +-- utils/common.py             #   YAML/JSON loaders, object serialization, helpers
|   +-- exception.py                #   Custom exception with file/line traceback
|   +-- logger.py                   #   Timestamped structured logging
|
+-- configs/                        # All behavior is config-driven
|   +-- config.yaml                 #   File paths, split params, target column
|   +-- model_params.yaml           #   Hyperparameter grids for 4 algorithms
|   +-- monitoring.yaml             #   Drift thresholds, retrain triggers, logging
|   +-- processing.yaml             #   Column types, imputation, scaling, encoding
|
+-- tests/                          # 158 tests, 85% coverage
|   +-- conftest.py                 #   Shared fixtures (synthetic data, temp dirs)
|   +-- unit/                       #   Component-level tests (12 test files)
|   +-- integration/                #   End-to-end pipeline tests
|
+-- notebooks/
|   +-- 01_analysis_and_engineering.ipynb  # EDA, statistical tests, feature engineering
|
+-- backend-csharp/                 # C# .NET API Gateway
|   +-- Controllers/                #   ChurnController (5 endpoints)
|   +-- Services/                   #   PythonApiService (HTTP forwarding + API key)
|   +-- Models/                     #   Request/Response DTOs
|
+-- frontend-dashboard/             # Web prediction dashboard
|   +-- index.html                  #   Dashboard layout
|   +-- css/style.css               #   Styling
|   +-- js/app.js                   #   API communication, form handling
|
+-- .github/workflows/
|   +-- ci.yml                      #   Lint -> Test -> C# Build -> Docker Build
|   +-- cd.yml                      #   Tag -> CI Gate -> GHCR Push -> GitHub Release
|
+-- artifacts/                      # Generated: model.pkl, preprocessor.pkl, metrics.json
+-- data/raw/                       # Source dataset (churn.csv)
+-- docs/                           # API.md, ARCHITECTURE.md, DEPLOYMENT.md, images/
+-- logs/                           # Runtime and prediction logs
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov=app --cov-report=term-missing

# Only unit tests
pytest tests/unit/ -v

# Only API tests
pytest tests/unit/test_api.py -v
```

| Module | Tests | Coverage |
|--------|------:|----------|
| Data Ingestion | 15 | 92% |
| Data Transformation | 18 | 88% |
| Model Trainer | 20 | 85% |
| Model Evaluation | 12 | 90% |
| Predict Pipeline | 15 | 89% |
| Drift Detector | 18 | 86% |
| API (app.py) | 20 | 82% |
| Integration | 10 | — |
| **Total** | **158** | **85%** |

---

## CI/CD Pipeline

### Continuous Integration (every push to main / develop)

```
Lint (flake8) -> Test (pytest + coverage) -> C# Build (.NET) -> Frontend Check -> Docker Build + Smoke Test
```

### Continuous Deployment (on v*.*.* tag)

```
CI Gate (lint + test) -> Docker Build -> Push to ghcr.io -> GitHub Release with changelog
```

```bash
# Create a release
git tag v1.0.0
git push origin v1.0.0
# Automatically: test -> build -> push image -> create GitHub Release
```

---

## Monitoring and Drift Detection

The platform continuously monitors prediction distribution and data quality.

**Drift Detection Methods:**

| Method | Applies To | Threshold | What It Detects |
|--------|-----------|-----------|-----------------|
| Kolmogorov-Smirnov test | Numerical features | p < 0.05 | Distribution shift in tenure, charges, etc. |
| Population Stability Index | Categorical features | PSI > 0.2 | Category proportion changes |

**Alert triggers:**
- Drift detected in 30%+ of features triggers a warning
- F1 drops below configured threshold triggers retrain recommendation
- Manual retrain via API or CLI always available

```bash
# Check drift status
curl http://localhost:8000/monitor/drift

# View prediction statistics (last 7 days)
curl http://localhost:8000/monitor/stats?days=7

# Trigger retraining
curl -X POST http://localhost:8000/monitor/retrain?force=true
```

---

## Configuration

All behavior is controlled via YAML — no hardcoded values in source code.

| File | Purpose |
|------|---------|
| `configs/config.yaml` | Data paths, train/test split ratio, target column |
| `configs/model_params.yaml` | Hyperparameter search grids for 4 algorithms |
| `configs/monitoring.yaml` | Drift thresholds, retrain triggers, prediction logging |
| `configs/processing.yaml` | Column types, imputation strategy, scaling, encoding |

---

## Roadmap

- [x] Churn prediction model (4 algorithms, GridSearchCV, class balancing)
- [x] FastAPI inference service (10 endpoints, Swagger docs)
- [x] Feature engineering (10 custom business-logic features)
- [x] Data drift monitoring (KS test + PSI)
- [x] Automated retraining pipeline with cooldown
- [x] Prediction logging (JSONL daily logs)
- [x] CI/CD with GitHub Actions (lint + test + Docker + GHCR)
- [x] Docker multi-container deployment (Python + C# + Frontend)
- [x] C# API Gateway with API key forwarding
- [x] Frontend prediction dashboard
- [x] 158 tests with 85% coverage
- [x] Security: API key auth, rate limiting, CORS
- [ ] SHAP values for per-prediction explanations
- [ ] Real-time drift dashboard (Grafana integration)
- [ ] A/B testing framework for model comparison
- [ ] Model registry with versioning (MLflow)
- [ ] Kubernetes deployment manifests
- [ ] Scheduled automatic retraining (cron/APScheduler)
- [ ] Alerting on drift events (Email / Slack)

---

## Dataset

[Telco Customer Churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn) — 7,043 customers, 21 original features, binary target (Churn: Yes/No).

After feature engineering: **29 features** including 10 custom business-logic features derived from domain knowledge and statistical testing (Chi-Square, Welch T-Test, VIF analysis).

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## Contributing

Contributions, issues, and feature requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
pip install -r requirements-dev.txt
pre-commit install

# Before submitting a PR
pytest tests/ -v
flake8 src/ app.py main.py --max-line-length=120
black src/ tests/ app.py main.py
```

---

## Contact

**Muhsin Furkan Turan**

[![GitHub](https://img.shields.io/badge/GitHub-Krayirhan-181717.svg?logo=github)](https://github.com/Krayirhan)
