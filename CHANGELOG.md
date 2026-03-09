# Changelog

All notable changes to the Churn Risk Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- SQLite prediction history for persistent `todayPredictions` counter
- SHAP values for per-prediction explanations
- Real-time drift dashboard (Grafana)
- Kubernetes deployment manifests
- Scheduled retraining (APScheduler)
- Alerting on drift (Email / Slack)

---

## [0.3.0] - 2026-03-10

### Added
- **6-Model Comparison Table** — frontend dashboard now shows all 6 models ranked by weighted score
  - Columns: Model, Recall, F1, Precision, ROC-AUC, Accuracy, Ağırlıklı Skor
  - Accuracy computed for all models from confusion matrix math (validated against stored metrics)
  - Winner badge and highlighted row for selected model
- **`GET /model-comparison` endpoint** — returns full ranked model list as JSON
- **C# proxy** — `PythonApiService.GetModelComparisonAsync()` + `ChurnController.GetModelComparison()`
- **Frontend stat cards redesigned from scratch** with correct KPI hierarchy:
  - Card 1 — Servis Durumu: operational (Aktif / Hata), not a model metric
  - Card 2 — Churn Recall: primary big number + AUC + F1 + Accuracy sub-labels
  - Card 3 — Veri Drift: drift monitoring with dynamic icon + color
  - Card 4 — Tahmin Yapıldı: session prediction count
- **`artifacts/model_comparison.json`** — saved on every training run, includes all 6 models with accuracy

### Changed
- Primary metric in Card 2 changed from **Accuracy (73.24%)** to **Recall (80.2%)** — the actual optimization target
- `updateHealthStatus()`, `updateModelInfo()`, `updateDriftStatus()` fully rewritten to match new element IDs
- `model_trainer.py` now saves `test_accuracy` per model in comparison report

### Fixed
- Old element ID `modelStatus` removed — replaced with `serviceStatus`, `serviceDetail`, `serviceIconBg`
- Error handler in `checkSystemHealth()` updated to new card IDs

---

## [0.2.0] - 2026-03-01

### Added
- **6 ML models** (up from 4): LogisticRegression, RandomForest, XGBClassifier, GradientBoostingClassifier, LGBMClassifier, CatBoostClassifier
- **Optuna Bayesian hyperparameter optimization** — 60 trials for XGB, LGBM, CatBoost after GridSearchCV
- **SMOTE oversampling** — class imbalance handled in training pipeline
- **Recall-optimized model selection** — criterion: `0.7 × Recall + 0.3 × F1`
- **Threshold optimization** — sweep from 0.30–0.60, LogisticRegression optimal at **0.40**
- **Real confidence score** — derived from `predict_proba`, replaces placeholder
- **Case-insensitive input normalization** — Pydantic model normalizes field keys
- **C# .NET 8.0 API Gateway** (`backend-csharp/`) — 5 endpoints, Swagger, CORS
- **Frontend Dashboard** (`frontend-dashboard/`) — HTML/CSS/JS, real-time status, prediction form
- **`GET /model-comparison`** — Python endpoint
- Prediction logging fix — emoji removed from `metrics.json` (Windows UTF-8 crash fix)

### Changed
- **Winner model changed**: XGBClassifier → **LogisticRegression** (Recall=80.2%, AUC=0.8453, F1=0.6141)
- Model selection scoring: F1-only → weighted `0.7 × Recall + 0.3 × F1`
- `model_params.yaml` extended with grids for all 6 models

### Fixed
- `metrics.json` emoji crash on Windows (UTF-8 encoding)
- CI whitespace lint ignore (W291, W293, W391)
- Flake8 errors: F401, F541, F841, E128, E261, E302, E231 — all resolved

---

## [0.1.0] - 2026-02-16

### Added

#### Phase 1 — Project Setup & Configuration
- Modular project structure (`src/components`, `src/pipeline`, `src/utils`)
- Config-driven architecture — all behavior via YAML (`config.yaml`, `model_params.yaml`, `monitoring.yaml`, `processing.yaml`)
- Custom exception handling and structured timestamped logging
- Docker multi-stage build + Docker Compose (3-service orchestration)
- GitHub Actions CI/CD: lint → test → Docker build → GitHub Release
- Pre-commit hooks (flake8, black, isort)

#### Phase 2 — Data Science Notebook
- EDA notebook `01_analysis_and_engineering.ipynb`
- Feature engineering analysis: outlier detection, imputation, encoding, scaling
- Statistical validation: Chi-Square, Welch T-Test, VIF analysis
- 10 custom business-logic features:
  `IsMonthToMonth`, `LoyaltyIndex`, `RiskScope`, `ChargeGap`, `IsElectronicCheck`,
  `UnitCost`, `IsPaperless`, `AvgServiceCount`, `TenureBin`, `ChargePerTenure`

#### Phase 3 — ML Pipeline Components
- **Data Ingestion** — CSV loading, stratified 80/20 split, artifact management
- **Data Transformation** — ColumnTransformer, IQR capping, median/mode imputation, OneHot encoding
- **Model Trainer** — multi-algorithm GridSearchCV, best model selection with min F1 threshold
- **Model Evaluation** — full metrics (accuracy, F1, recall, precision, ROC-AUC, PR-AUC), confusion matrix, ROC/PR curves
- **Training Pipeline** — end-to-end orchestration with error propagation

#### Phase 4 — FastAPI REST API
- 11 REST endpoints with Swagger/OpenAPI docs
- Pydantic request/response validation
- API key authentication (`X-API-Key` header)
- Rate limiting (sliding window, configurable)
- CORS middleware
- Batch prediction (up to 100 customers/request)
- CLI entry point (`main.py --train / --serve / --predict / --monitor`)

#### Phase 5 — Monitoring & Retraining
- **Drift Detector** — KS test (numerical) + PSI (categorical), feature-level alerts
- **Prediction Logger** — daily JSONL with input hash, probability, risk level, model version
- **Model Monitor** — drift orchestration, performance degradation detection
- **Retrain Pipeline** — automated retraining with cooldown, old/new metric comparison
- 5 monitoring endpoints: `/monitor/stats`, `/monitor/drift`, `/monitor/health-report`, `/monitor/retrain`, `/monitor/retrain-history`

#### Phase 6 — Quality & Packaging
- 158 tests, 75% coverage (unit + integration)
- `pyproject.toml` — PEP 621 metadata, project URLs, classifiers
- `MANIFEST.in`, `.readthedocs.yml`
- `Makefile` with 15+ commands

#### Phase 7 — Documentation
- `README.md` — badges, quick start, architecture diagram, full API reference
- `CHANGELOG.md`, `LICENSE` (MIT), `CONTRIBUTING.md`
- `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/PACKAGING.md`

---

## Version History

| Version | Date       | Highlight                                                        |
|---------|------------|------------------------------------------------------------------|
| 0.3.0   | 2026-03-10 | Frontend card redesign, 6-model comparison table with Accuracy   |
| 0.2.0   | 2026-03-01 | 6 models, Optuna, SMOTE, threshold opt, C# gateway, frontend     |
| 0.1.0   | 2026-02-16 | Full ML pipeline, 11-endpoint API, monitoring, CI/CD, 158 tests  |
