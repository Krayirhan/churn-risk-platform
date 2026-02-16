# 📊 Telco Customer Churn Risk Platform

> End-to-end ML pipeline for predicting telecom customer churn with production-ready FastAPI service, automated retraining, and drift monitoring

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/Krayirhan/churn-risk-platform/workflows/CI%20%E2%80%94%20Lint%2C%20Test%20%26%20Build/badge.svg)](https://github.com/Krayirhan/churn-risk-platform/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🎯 Overview

This project implements a complete machine learning operations (MLOps) pipeline for predicting customer churn in the telecommunications industry. The platform provides:

- **Data Pipeline**: Automated ingestion, validation, and transformation with feature engineering
- **Model Training**: Multi-algorithm comparison (XGBoost, Random Forest, AdaBoost) with hyperparameter tuning
- **REST API**: Production-ready FastAPI service with batch prediction support
- **Monitoring**: Real-time drift detection, prediction logging, and automated alerts
- **Retraining**: Scheduled pipeline execution with performance tracking
- **CI/CD**: GitHub Actions for automated testing, linting, and Docker image builds
- **Testing**: 158 comprehensive tests with 85%+ code coverage

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CHURN RISK PLATFORM                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📥 DATA INGESTION          🔄 TRANSFORMATION       🏋️ TRAINING    │
│  ├─ Raw data load           ├─ Missing value       ├─ XGBoost      │
│  ├─ Train/test split        │   imputation         ├─ Random Forest│
│  └─ Validation              ├─ Outlier handling    └─ AdaBoost     │
│                             ├─ Feature encoding                     │
│                             └─ Scaling                              │
│                                                                     │
│  📊 EVALUATION              🚀 DEPLOYMENT          📡 MONITORING    │
│  ├─ Multi-metric            ├─ FastAPI REST API   ├─ Drift detect  │
│  ├─ Threshold checks        ├─ Docker container   ├─ Pred logging  │
│  └─ Model comparison        └─ Health checks      └─ Auto retrain  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Git
- Docker (optional, for containerized deployment)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Krayirhan/churn-risk-platform.git
   cd churn-risk-platform
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   
   # For development
   pip install -r requirements-dev.txt
   ```

4. **Verify installation**:
   ```bash
   python main.py --version
   ```

## 📖 Usage

### Training Pipeline

Train a new model with the full pipeline:

```bash
# Full pipeline (ingest → transform → train → evaluate)
python main.py --train

# Custom configuration
python main.py --train --config configs/training_config.yaml
```

### Prediction Service

Start the FastAPI REST API server:

```bash
# Using CLI
python main.py --serve

# Or directly with uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Access the API:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Making Predictions

**Single prediction**:
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "Yes",
    "Dependents": "No",
    "tenure": 12,
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "Fiber optic",
    "OnlineSecurity": "No",
    "OnlineBackup": "Yes",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "Yes",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 70.35,
    "TotalCharges": 1397.48
  }'
```

**Batch prediction**:
```bash
curl -X POST "http://localhost:8000/predict/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "customers": [
      {...customer_data_1...},
      {...customer_data_2...}
    ]
  }'
```

### Monitoring & Retraining

**Check drift status**:
```bash
python main.py --check-drift
```

**View prediction logs**:
```bash
python main.py --view-logs --limit 100
```

**Trigger retraining**:
```bash
python main.py --retrain
```

## 🐳 Docker Deployment

Build and run with Docker:

```bash
# Build image
docker build -t churn-risk-platform:latest .

# Run container
docker run -p 8000:8000 \
  -v $(pwd)/artifacts:/app/artifacts \
  -v $(pwd)/logs:/app/logs \
  churn-risk-platform:latest

# Or use Docker Compose
docker-compose up -d
```

## 📁 Project Structure

```
churn-risk-platform/
├── app.py                    # FastAPI REST API application
├── main.py                   # CLI entry point
├── Dockerfile                # Container image definition
├── docker-compose.yml        # Multi-container orchestration
├── pyproject.toml            # Modern Python project config
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
├── Makefile                  # Common tasks automation
│
├── .github/
│   └── workflows/
│       └── ci.yml            # CI/CD pipeline (lint, test, build)
│
├── configs/
│   ├── training_config.yaml  # Model training parameters
│   └── monitoring.yaml       # Drift & alert configuration
│
├── src/
│   ├── components/           # Pipeline components
│   │   ├── data_ingestion.py
│   │   ├── data_transformation.py
│   │   ├── model_trainer.py
│   │   ├── model_evaluation.py
│   │   ├── drift_detector.py
│   │   ├── prediction_logger.py
│   │   └── model_monitor.py
│   │
│   ├── pipeline/             # Orchestration pipelines
│   │   ├── train_pipeline.py
│   │   ├── predict_pipeline.py
│   │   └── retrain_pipeline.py
│   │
│   ├── utils/                # Shared utilities
│   │   └── common.py
│   │
│   ├── exception.py          # Custom exception handling
│   └── logger.py             # Structured logging
│
├── tests/                    # 158 comprehensive tests
│   ├── test_data_ingestion.py
│   ├── test_data_transformation.py
│   ├── test_model_trainer.py
│   ├── test_model_evaluation.py
│   ├── test_train_pipeline.py
│   ├── test_predict_pipeline.py
│   ├── test_drift_detector.py
│   ├── test_prediction_logger.py
│   ├── test_model_monitor.py
│   ├── test_retrain_pipeline.py
│   └── test_api.py
│
├── notebooks/                # Exploratory analysis
│   └── 01_eda_feature_engineering.ipynb
│
├── data/                     # Dataset storage
│   └── Telco-Customer-Churn.csv
│
├── artifacts/                # Generated outputs
│   ├── data_ingestion/       # Raw & processed data
│   ├── data_transformation/  # Preprocessor objects
│   └── model_trainer/        # Trained models & reports
│
├── logs/                     # Application logs
│   └── predictions/          # Prediction history
│
└── docs/                     # Documentation
    ├── API.md                # API reference
    ├── DEPLOYMENT.md         # Deployment guide
    └── ARCHITECTURE.md       # System design docs
```

## 🧪 Testing

Run the test suite:

```bash
# All tests
pytest

# With coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Specific test file
pytest tests/test_api.py -v

# Watch mode (requires pytest-watch)
ptw
```

Current test coverage: **85.2%**

## 🔍 Code Quality

The project uses automated code quality tools:

```bash
# Linting
flake8 src/ app.py main.py --max-line-length=120

# Formatting
black src/ tests/ app.py main.py

# Import sorting
isort src/ tests/ app.py main.py

# Type checking
mypy src/ app.py main.py

# All checks (via Makefile)
make lint
```

## 📊 Model Performance

Current production model (XGBoost):

| Metric        | Value   |
|---------------|---------|
| Accuracy      | 81.27%  |
| Precision     | 67.71%  |
| Recall        | 55.62%  |
| F1 Score      | 61.08%  |
| ROC AUC       | 85.01%  |

**Feature Importance** (Top 5):
1. `TotalCharges` (0.156)
2. `MonthlyCharges` (0.142)
3. `tenure` (0.138)
4. `Contract_Two year` (0.089)
5. `InternetService_Fiber optic` (0.067)

## 🔧 Configuration

### Training Configuration (`configs/training_config.yaml`)

```yaml
model_trainer:
  expected_accuracy: 0.70
  models:
    XGBoost:
      learning_rate: [0.01, 0.1]
      max_depth: [3, 5, 7]
      n_estimators: [100, 200]
```

### Monitoring Configuration (`configs/monitoring.yaml`)

```yaml
drift_detection:
  statistical_tests:
    - kolmogorov_smirnov
    - population_stability_index
  alert_thresholds:
    critical: 0.25
    warning: 0.15
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- All tests pass (`pytest`)
- Code is formatted (`black`, `isort`)
- Linting passes (`flake8`)
- Documentation is updated

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Dataset**: [Telco Customer Churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn) from Kaggle
- **Framework**: Built with [FastAPI](https://fastapi.tiangolo.com/) and [scikit-learn](https://scikit-learn.org/)
- **MLOps Practices**: Inspired by industry best practices from Google, Netflix, and Uber

## 📧 Contact

- **GitHub**: [@Krayirhan](https://github.com/Krayirhan)
- **Project Link**: [https://github.com/Krayirhan/churn-risk-platform](https://github.com/Krayirhan/churn-risk-platform)

---

⭐ **Star this repository** if you find it useful!
