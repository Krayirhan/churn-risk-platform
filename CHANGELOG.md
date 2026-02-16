# Changelog

All notable changes to the Telco Customer Churn Risk Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive project documentation (README, API docs, deployment guide)
- Architecture diagrams and system design documentation

## [0.1.0] - 2026-02-16

### Added

#### Phase 1: Project Setup & Configuration
- Initial project structure with modular architecture
- Configuration management via YAML files (`training_config.yaml`, `monitoring.yaml`)
- Custom exception handling and structured logging system
- Docker containerization with multi-stage builds
- Docker Compose for local development
- GitHub Actions CI/CD pipeline (lint → test → build)
- Pre-commit hooks for code quality
- Comprehensive `.gitignore` and `.dockerignore`

#### Phase 2: Data Science Notebook
- Exploratory Data Analysis (EDA) notebook (`01_eda_feature_engineering.ipynb`)
- Feature engineering analysis:
  - Outlier detection and handling strategies
  - Missing value imputation methods
  - Feature encoding (Label, OneHot, Target)
  - Feature scaling techniques
- Model performance benchmarking:
  - XGBoost (best: 81.27% accuracy, 85.01% ROC AUC)
  - Random Forest (78.94% accuracy)
  - AdaBoost (79.73% accuracy)
- Statistical validation and hypothesis testing

#### Phase 3: Model Engineering Components
- **Data Ingestion** (`src/components/data_ingestion.py`):
  - Train/test split with stratification
  - Data validation and integrity checks
  - Artifact management
- **Data Transformation** (`src/components/data_transformation.py`):
  - Automated feature preprocessing pipeline
  - Outlier capping with IQR method
  - Missing value imputation (median/mode)
  - Feature encoding and scaling
  - Preprocessor object persistence
- **Model Trainer** (`src/components/model_trainer.py`):
  - Multi-algorithm training (XGBoost, Random Forest, AdaBoost)
  - GridSearchCV hyperparameter tuning
  - Best model selection with configurable thresholds
  - Model serialization
- **Model Evaluation** (`src/components/model_evaluation.py`):
  - Comprehensive metrics (accuracy, precision, recall, F1, ROC AUC)
  - Confusion matrix generation
  - Feature importance analysis
  - JSON report generation
- **Training Pipeline** (`src/pipeline/train_pipeline.py`):
  - End-to-end orchestration
  - Error handling and logging
- **Prediction Pipeline** (`src/pipeline/predict_pipeline.py`):
  - Single and batch prediction support
  - Model/preprocessor loading
  - Input validation
- Test suite: 98 comprehensive tests with 82% coverage

#### Phase 4: Serve & API
- **FastAPI REST API** (`app.py`):
  - `GET /` - Welcome endpoint
  - `GET /health` - Service health check
  - `GET /model-info` - Model metadata and metrics
  - `POST /predict` - Single customer prediction
  - `POST /predict/batch` - Batch predictions
- **CLI Interface** (`main.py`):
  - `--train` - Execute training pipeline
  - `--predict` - Interactive prediction mode
  - `--serve` - Start FastAPI server
  - `--version` - Display version info
- Pydantic models for request/response validation
- CORS middleware for cross-origin requests
- Automatic OpenAPI/Swagger documentation
- Uvicorn ASGI server integration
- API test suite (10 tests)

#### Phase 5: Monitor & Retrain
- **Drift Detection** (`src/components/drift_detector.py`):
  - Kolmogorov-Smirnov statistical test
  - Population Stability Index (PSI) calculation
  - Feature-level drift analysis
  - Alert threshold configuration
- **Prediction Logger** (`src/components/prediction_logger.py`):
  - JSON-based prediction history
  - Metadata tracking (timestamp, model version, confidence)
  - Query interface with filtering
- **Model Monitor** (`src/components/model_monitor.py`):
  - Drift monitoring orchestration
  - Performance degradation detection
  - Alert generation system
  - Comprehensive monitoring reports
- **Retrain Pipeline** (`src/pipeline/retrain_pipeline.py`):
  - Automated retraining workflow
  - Performance comparison (old vs new model)
  - Conditional model replacement
  - Retraining history tracking
- **API Endpoints**:
  - `GET /monitoring/drift` - Drift detection results
  - `GET /monitoring/predictions` - Prediction logs
  - `GET /monitoring/status` - Monitoring status
  - `POST /monitoring/retrain` - Trigger retraining
  - `GET /monitoring/retrain/history` - Retraining history
- **CLI Commands**:
  - `--check-drift` - Run drift detection
  - `--view-logs` - View prediction logs
  - `--retrain` - Trigger retraining
- Monitoring configuration (`configs/monitoring.yaml`)
- Test suite: 60 new tests (158 total, 85% coverage)

### Fixed
- Build system configuration in `pyproject.toml` (setuptools backend)
- Flake8 linting errors (94 errors → 0):
  - Removed unused imports (F401)
  - Fixed empty f-strings (F541)
  - Fixed continuation line indentation (E128)
  - Fixed inline comment spacing (E261)
  - Added blank lines before functions/classes (E302)
  - Fixed type hint spacing (E231)
- CI workflow: Added whitespace error exceptions (W291, W293, W391)

### Changed
- Updated CI workflow to extend flake8 ignore list
- Improved error messages and logging throughout codebase
- Enhanced test coverage across all modules

## [0.0.1] - 2026-01-15

### Added
- Initial repository setup
- Basic project skeleton
- Dataset integration (Telco Customer Churn from Kaggle)

---

## Version History Summary

| Version | Date       | Key Features                                    |
|---------|------------|-------------------------------------------------|
| 0.1.0   | 2026-02-16 | Full ML pipeline, API, monitoring, CI/CD        |
| 0.0.1   | 2026-01-15 | Initial setup                                   |

---

## Maintenance Notes

### Adding New Features
When adding features to this changelog:
1. Place new changes under `[Unreleased]` section
2. Use appropriate subsections: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`
3. Be specific and include relevant file references
4. Update version number and date when releasing

### Release Process
1. Move `[Unreleased]` changes to new version section
2. Update version in `pyproject.toml`
3. Create Git tag: `git tag -a v0.1.0 -m "Release v0.1.0"`
4. Push tag: `git push origin v0.1.0`
5. Create GitHub release with changelog excerpt
