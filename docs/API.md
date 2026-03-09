# API Documentation

## Overview

The Churn Risk Platform exposes a RESTful API built with FastAPI. All endpoints return JSON responses and follow standard HTTP status codes.

**Base URL**: `http://localhost:8000`

**Interactive Documentation**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

API key authentication is built-in and controlled via the `API_KEY` environment variable:

- **Development mode** (default): When `API_KEY` is not set, all endpoints are open access.
- **Production mode**: Set `API_KEY=your-secret-key` in `.env`. Protected endpoints require the `X-API-Key` header.

**Protected endpoints**: `/predict`, `/predict/batch`, all `/monitor/*` endpoints.
**Public endpoints**: `/`, `/health`, `/model-info`.

```bash
# Example authenticated request
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d @customer_data.json
```

## Rate Limiting

Built-in IP-based rate limiting (sliding window):
- **Default**: 100 requests per 60 seconds per IP
- **Configuration**: `RATE_LIMIT_WINDOW` (seconds) and `RATE_LIMIT_MAX` (requests) environment variables
- **Response**: HTTP 429 when limit exceeded

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

**Response** (healthy):
```json
{
  "status": "healthy",
  "model_loaded": true,
  "preprocessor_loaded": true,
  "artifacts_exist": true
}
```

**Response** (degraded — artifacts missing):
```json
{
  "status": "degraded",
  "model_loaded": false,
  "preprocessor_loaded": false,
  "artifacts_exist": false
}
```

> **Note**: This endpoint always returns HTTP 200. Check the `status` field to determine service health. Kubernetes probes should check `status == "healthy"`.

**Status Codes**:
- `200 OK` - Always returned (check `status` field for actual health)

---

#### `GET /model-info`

Retrieve performance metrics for the active model.

**Response**:
```json
{
  "model_name": "XGBoost",
  "accuracy": 0.8127,
  "precision": 0.6771,
  "recall": 0.5562,
  "f1": 0.6108,
  "roc_auc": 0.8501,
  "pr_auc": 0.7234
}
```

> **Note**: Metrics are returned as flat top-level fields (not nested under `metrics`). All metric fields are nullable — they return `null` if not available.

**Status Codes**:
- `200 OK` - Success
- `404 Not Found` - Model has not been trained yet

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
  "prediction": 1,
  "churn_probability": 0.73,
  "risk_level": "Yüksek",
  "customerID": "API_USER"
}
```

**Response Fields**:
- `prediction`: Binary churn prediction (`0` stay, `1` churn)
- `churn_probability`: Probability of churn (0.0-1.0)
- `risk_level`: Risk categorization ("Düşük", "Orta", "Yüksek")
- `customerID`: Customer identifier

**Status Codes**:
- `200 OK` - Prediction successful
- `422 Unprocessable Entity` - Invalid input data
- `503 Service Unavailable` - Model artifacts missing
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
- Maximum 100 customers per batch
- Request timeout: 60 seconds

**Response**:
```json
{
  "predictions": [
    {
      "prediction": 1,
      "churn_probability": 0.73,
      "risk_level": "Yüksek",
      "customerID": "CUST_001"
    },
    {
      "prediction": 0,
      "churn_probability": 0.22,
      "risk_level": "Düşük",
      "customerID": "CUST_002"
    }
  ],
  "total": 2,
  "churn_count": 1,
  "churn_rate": 50.0
}
```

**Status Codes**:
- `200 OK` - Batch prediction successful
- `400 Bad Request` - Batch size exceeded
- `422 Unprocessable Entity` - Invalid input data
- `503 Service Unavailable` - Model artifacts missing
- `500 Internal Server Error` - Prediction failed

---

### Monitoring API

#### `GET /monitor/stats`

Retrieve prediction stats from logs.

**Query Parameters**:
- `days` (optional, default=7): lookback window in days

**Response**:
```json
{
  "total_predictions": 120,
  "churn_count": 35,
  "churn_rate": 29.17,
  "avg_churn_probability": 0.46,
  "risk_distribution": {
    "Düşük": 52,
    "Orta": 33,
    "Yüksek": 35
  }
}
```

---

#### `GET /monitor/drift`

Analyze drift on recent prediction features.

**Response**:
```json
{
  "drift_detected": true,
  "drifted_features": ["MonthlyCharges", "Contract"],
  "total_features_checked": 6,
  "drift_ratio": 0.3333,
  "alert_level": "critical",
  "sample_size": 500,
  "threshold": 0.3
}
```

---

#### `GET /monitor/health-report`

Get combined monitoring decision (performance + drift).

**Response**:
```json
{
  "timestamp": "2026-02-16T10:35:00",
  "needs_retrain": true,
  "retrain_reason": ["performance_degraded", "drift_detected"],
  "overall_status": "retrain_needed",
  "performance": {},
  "drift": {}
}
```

---

#### `POST /monitor/retrain`

Trigger model retraining pipeline.

**Query Parameters**:
- `force` (optional, default=`false`): skip cooldown and checks

**Response**:
```json
{
  "retrained": true,
  "reason": "manual",
  "message": "Retrain tamamlandı",
  "timestamp": "2026-02-16T10:40:00"
}
```

---

#### `GET /monitor/retrain-history`

View retraining history.

**Response**:
```json
{
  "history": [
    {
      "timestamp": "2026-02-10T08:15:00",
      "reason": "drift_detected",
      "best_model": "LogisticRegression",
      "best_f1": 0.6321
    }
  ]
}
```

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
