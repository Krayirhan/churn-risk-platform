# API Documentation

## Overview

The Churn Risk Platform exposes a RESTful API built with FastAPI. All endpoints return JSON responses and follow standard HTTP status codes.

**Base URL**: `http://localhost:8000`

**Interactive Documentation**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

Currently, the API is open access (no authentication required). For production deployment, consider adding:
- API Key authentication
- JWT token-based auth
- Rate limiting

## Endpoints

### Core API

#### `GET /`

Welcome endpoint with basic service information.

**Response**:
```json
{
  "message": "🚀 Telco Customer Churn Risk Platform",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/health"
}
```

**Status Codes**:
- `200 OK` - Success

---

#### `GET /health`

Service health check. Verifies model and preprocessor availability.

**Response**:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "preprocessor_loaded": true,
  "timestamp": "2026-02-16T10:30:00Z"
}
```

**Status Codes**:
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Model or preprocessor not loaded

---

#### `GET /model-info`

Retrieve metadata and performance metrics for the active model.

**Response**:
```json
{
  "model_name": "XGBoost",
  "version": "0.1.0",
  "metrics": {
    "accuracy": 0.8127,
    "precision": 0.6771,
    "recall": 0.5562,
    "f1_score": 0.6108,
    "roc_auc": 0.8501
  },
  "feature_importance": {
    "TotalCharges": 0.156,
    "MonthlyCharges": 0.142,
    "tenure": 0.138,
    "Contract_Two year": 0.089,
    "InternetService_Fiber optic": 0.067
  },
  "training_date": "2026-02-15T14:22:10Z",
  "data_shape": {
    "n_samples": 7043,
    "n_features": 19
  }
}
```

**Status Codes**:
- `200 OK` - Success
- `404 Not Found` - Model info file not found

---

#### `POST /predict`

Predict churn risk for a single customer.

**Request Body**:
```json
{
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
}
```

**Field Descriptions**:

| Field | Type | Description | Valid Values |
|-------|------|-------------|--------------|
| `gender` | string | Customer gender | "Male", "Female" |
| `SeniorCitizen` | integer | Senior citizen flag | 0 (No), 1 (Yes) |
| `Partner` | string | Has partner | "Yes", "No" |
| `Dependents` | string | Has dependents | "Yes", "No" |
| `tenure` | integer | Months with company | 0-72 |
| `PhoneService` | string | Phone service subscribed | "Yes", "No" |
| `MultipleLines` | string | Multiple phone lines | "Yes", "No", "No phone service" |
| `InternetService` | string | Internet service type | "DSL", "Fiber optic", "No" |
| `OnlineSecurity` | string | Online security add-on | "Yes", "No", "No internet service" |
| `OnlineBackup` | string | Online backup add-on | "Yes", "No", "No internet service" |
| `DeviceProtection` | string | Device protection add-on | "Yes", "No", "No internet service" |
| `TechSupport` | string | Tech support add-on | "Yes", "No", "No internet service" |
| `StreamingTV` | string | TV streaming add-on | "Yes", "No", "No internet service" |
| `StreamingMovies` | string | Movie streaming add-on | "Yes", "No", "No internet service" |
| `Contract` | string | Contract type | "Month-to-month", "One year", "Two year" |
| `PaperlessBilling` | string | Paperless billing | "Yes", "No" |
| `PaymentMethod` | string | Payment method | "Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)" |
| `MonthlyCharges` | float | Monthly charge amount | 0-200 |
| `TotalCharges` | float | Total charges to date | 0-10000 |

**Response**:
```json
{
  "prediction": "Yes",
  "churn_probability": 0.73,
  "risk_level": "HIGH",
  "confidence": 0.73,
  "model_version": "0.1.0",
  "prediction_id": "pred_20260216_103045_a7f3c2"
}
```

**Response Fields**:
- `prediction`: Binary churn prediction ("Yes" or "No")
- `churn_probability`: Probability of churn (0.0-1.0)
- `risk_level`: Risk categorization ("LOW" < 0.3, "MEDIUM" 0.3-0.7, "HIGH" > 0.7)
- `confidence`: Model confidence score
- `model_version`: Version of model used
- `prediction_id`: Unique identifier for this prediction

**Status Codes**:
- `200 OK` - Prediction successful
- `422 Unprocessable Entity` - Invalid input data
- `500 Internal Server Error` - Prediction failed

**Example cURL**:
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d @customer_data.json
```

---

#### `POST /predict/batch`

Predict churn risk for multiple customers in a single request.

**Request Body**:
```json
{
  "customers": [
    {
      "gender": "Female",
      "SeniorCitizen": 0,
      "Partner": "Yes",
      ...
    },
    {
      "gender": "Male",
      "SeniorCitizen": 1,
      "Partner": "No",
      ...
    }
  ]
}
```

**Request Limits**:
- Maximum 1000 customers per batch
- Request timeout: 60 seconds

**Response**:
```json
{
  "predictions": [
    {
      "customer_index": 0,
      "prediction": "Yes",
      "churn_probability": 0.73,
      "risk_level": "HIGH",
      "confidence": 0.73
    },
    {
      "customer_index": 1,
      "prediction": "No",
      "churn_probability": 0.22,
      "risk_level": "LOW",
      "confidence": 0.78
    }
  ],
  "summary": {
    "total_customers": 2,
    "predicted_churners": 1,
    "churn_rate": 0.50,
    "avg_churn_probability": 0.475,
    "processing_time_ms": 45
  },
  "model_version": "0.1.0",
  "batch_id": "batch_20260216_103055_b9e1f7"
}
```

**Status Codes**:
- `200 OK` - Batch prediction successful
- `422 Unprocessable Entity` - Invalid input data or batch size exceeded
- `500 Internal Server Error` - Prediction failed

---

### Monitoring API

#### `GET /monitoring/drift`

Check for data drift in recent predictions.

**Query Parameters**:
- `window_days` (optional, default=7): Number of days to analyze

**Example**: `GET /monitoring/drift?window_days=7`

**Response**:
```json
{
  "drift_detected": true,
  "drift_score": 0.27,
  "threshold": 0.25,
  "features_with_drift": [
    {
      "feature": "MonthlyCharges",
      "ks_statistic": 0.18,
      "psi_score": 0.31,
      "drift_detected": true
    },
    {
      "feature": "tenure",
      "ks_statistic": 0.09,
      "psi_score": 0.12,
      "drift_detected": false
    }
  ],
  "analysis_period": {
    "start_date": "2026-02-09",
    "end_date": "2026-02-16",
    "n_predictions": 1523
  },
  "recommendation": "RETRAIN_RECOMMENDED",
  "timestamp": "2026-02-16T10:35:00Z"
}
```

**Status Codes**:
- `200 OK` - Drift analysis successful
- `400 Bad Request` - Invalid parameters
- `500 Internal Server Error` - Analysis failed

---

#### `GET /monitoring/predictions`

Retrieve logged prediction history.

**Query Parameters**:
- `limit` (optional, default=100): Maximum number of records
- `offset` (optional, default=0): Pagination offset
- `start_date` (optional): Filter from date (ISO format)
- `end_date` (optional): Filter to date (ISO format)
- `risk_level` (optional): Filter by risk level ("LOW", "MEDIUM", "HIGH")

**Example**: `GET /monitoring/predictions?limit=50&risk_level=HIGH`

**Response**:
```json
{
  "predictions": [
    {
      "prediction_id": "pred_20260216_103045_a7f3c2",
      "timestamp": "2026-02-16T10:30:45Z",
      "prediction": "Yes",
      "churn_probability": 0.73,
      "risk_level": "HIGH",
      "model_version": "0.1.0",
      "input_hash": "7f3a9b..."
    }
  ],
  "pagination": {
    "total": 1523,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

**Status Codes**:
- `200 OK` - Logs retrieved successfully
- `400 Bad Request` - Invalid parameters

---

#### `GET /monitoring/status`

Get comprehensive monitoring status.

**Response**:
```json
{
  "model_status": "HEALTHY",
  "drift_status": "WARNING",
  "last_drift_check": "2026-02-16T10:35:00Z",
  "drift_score": 0.19,
  "predictions_today": 342,
  "predictions_total": 15234,
  "last_retrain": "2026-02-10T08:15:00Z",
  "days_since_retrain": 6,
  "avg_prediction_time_ms": 12.5,
  "model_version": "0.1.0"
}
```

**Status Codes**:
- `200 OK` - Status retrieved successfully

---

#### `POST /monitoring/retrain`

Trigger model retraining pipeline.

**Request Body** (optional):
```json
{
  "force": false,
  "notify": true
}
```

**Parameters**:
- `force` (optional): Skip performance checks, always retrain
- `notify` (optional): Send notifications on completion

**Response**:
```json
{
  "status": "RETRAINING_STARTED",
  "job_id": "retrain_20260216_104000",
  "estimated_time_minutes": 15,
  "message": "Retraining pipeline initiated successfully"
}
```

**Status Codes**:
- `202 Accepted` - Retraining started
- `409 Conflict` - Retraining already in progress
- `500 Internal Server Error` - Failed to start retraining

---

#### `GET /monitoring/retrain/history`

View retraining history and results.

**Query Parameters**:
- `limit` (optional, default=10): Number of records

**Response**:
```json
{
  "retraining_history": [
    {
      "job_id": "retrain_20260210_081500",
      "start_time": "2026-02-10T08:15:00Z",
      "end_time": "2026-02-10T08:28:32Z",
      "duration_minutes": 13.5,
      "status": "COMPLETED",
      "old_model_accuracy": 0.8127,
      "new_model_accuracy": 0.8245,
      "improvement": 0.0118,
      "model_replaced": true
    }
  ],
  "summary": {
    "total_retrainings": 5,
    "successful": 5,
    "failed": 0,
    "avg_improvement": 0.0092
  }
}
```

**Status Codes**:
- `200 OK` - History retrieved successfully

---

## Error Handling

All endpoints follow a consistent error response format:

```json
{
  "detail": "Error message describing what went wrong",
  "error_type": "ValidationError",
  "timestamp": "2026-02-16T10:40:00Z"
}
```

### Common HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 202 | Accepted | Request accepted for async processing |
| 400 | Bad Request | Invalid parameters or malformed request |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error in request body |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Service temporarily unavailable |

---

## Rate Limiting

**Current**: No rate limiting implemented

**Production Recommendations**:
- 100 requests/minute per IP for `/predict`
- 10 requests/minute per IP for `/predict/batch`
- 20 requests/minute per IP for monitoring endpoints

Implement with middleware like `slowapi` or nginx rate limiting.

---

## Webhooks (Future Feature)

Planned webhook support for:
- Drift detection alerts
- Retraining completion notifications
- Performance degradation warnings

---

## SDKs and Client Libraries

### Python Client Example

```python
import requests

class ChurnRiskClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def predict(self, customer_data):
        response = requests.post(
            f"{self.base_url}/predict",
            json=customer_data
        )
        response.raise_for_status()
        return response.json()
    
    def batch_predict(self, customers):
        response = requests.post(
            f"{self.base_url}/predict/batch",
            json={"customers": customers}
        )
        response.raise_for_status()
        return response.json()
    
    def check_health(self):
        response = requests.get(f"{self.base_url}/health")
        return response.status_code == 200

# Usage
client = ChurnRiskClient()
result = client.predict({
    "gender": "Female",
    "tenure": 12,
    ...
})
print(f"Churn probability: {result['churn_probability']}")
```

---

## Versioning

API versioning strategy (future):
- URL path versioning: `/api/v1/predict`, `/api/v2/predict`
- Header-based versioning: `Accept: application/vnd.churn-risk.v1+json`

Current version: **v0.1.0** (no version prefix in URLs)

---

## Support

For API support:
- GitHub Issues: [https://github.com/Krayirhan/churn-risk-platform/issues](https://github.com/Krayirhan/churn-risk-platform/issues)
- Documentation: [README.md](../README.md)
