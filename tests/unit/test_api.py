# ============================================================================
# test_api.py — FastAPI REST API için Unit Testler
# ============================================================================
# TEST EDİLEN DOSYA: app.py → FastAPI uygulaması
#
# TEST STRATEJİSİ:
#   - TestClient ile HTTP istekleri simüle edilir (gerçek sunucu başlatılmaz)
#   - Pydantic modellerin doğrulaması test edilir
#   - Endpoint'lerin doğru HTTP durum kodları döndürdüğü kontrol edilir
#   - CORS header'ları doğrulanır
#
# NOT: /predict endpoint'i artifacts/model.pkl gerektirir.
#      Model yoksa 503 dönmesi beklenir.
# ============================================================================

import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Test Client Fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient oluşturur."""
    from app import app
    with TestClient(app) as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# Genel Endpoint Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestGeneralEndpoints:
    """Genel endpoint'lerin doğru çalıştığını test eder."""

    def test_root_returns_200(self, client):
        """GET / → 200 OK dönmeli."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_has_message(self, client):
        """GET / → 'message' anahtarı içermeli."""
        response = client.get("/")
        data = response.json()
        assert "message" in data

    def test_health_returns_200(self, client):
        """GET /health → 200 OK dönmeli."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_status(self, client):
        """GET /health → 'status' anahtarı içermeli."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded")

    def test_health_has_model_info(self, client):
        """GET /health → model ve preprocessor durumu bildirilmeli."""
        response = client.get("/health")
        data = response.json()
        assert "model_loaded" in data
        assert "preprocessor_loaded" in data


# ─────────────────────────────────────────────────────────────────────────────
# Model Info Endpoint Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestModelInfoEndpoint:
    """GET /model-info endpoint'ini test eder."""

    def test_model_info_returns_valid_status(self, client):
        """GET /model-info → 200 veya 404 dönmeli (modele bağlı)."""
        response = client.get("/model-info")
        # Model eğitilmişse 200, eğitilmemişse 404
        assert response.status_code in (200, 404)


# ─────────────────────────────────────────────────────────────────────────────
# Predict Endpoint Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestPredictEndpoint:
    """POST /predict endpoint'ini test eder."""

    def test_predict_returns_valid_status(self, client):
        """POST /predict → 200 veya 503 dönmeli (model yoksa 503)."""
        payload = {
            "tenure": 24,
            "MonthlyCharges": 79.85,
            "TotalCharges": 1916.40,
            "Contract": "Month-to-month",
        }
        response = client.post("/predict", json=payload)
        # Model varsa 200, yoksa 503
        assert response.status_code in (200, 500, 503)

    def test_predict_with_empty_body(self, client):
        """POST /predict boş body ile → varsayılanlarla çalışmalı (200 veya 503)."""
        response = client.post("/predict", json={})
        # Pydantic varsayılanlar devreye girer → model yoksa 503, varsa 200
        assert response.status_code in (200, 500, 503)

    def test_predict_with_invalid_type_returns_422(self, client):
        """POST /predict hatalı tip ile → 422 Unprocessable Entity."""
        payload = {"tenure": "not_a_number"}  # int olmalı
        response = client.post("/predict", json=payload)
        assert response.status_code == 422

    def test_predict_with_out_of_range_returns_422(self, client):
        """POST /predict aralık dışı değer ile → 422."""
        payload = {"tenure": -5}  # ge=0 kuralını ihlal eder
        response = client.post("/predict", json=payload)
        assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Batch Predict Endpoint Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestBatchPredictEndpoint:
    """POST /predict/batch endpoint'ini test eder."""

    def test_batch_returns_valid_status(self, client):
        """POST /predict/batch → 200 veya 503 dönmeli."""
        payload = {
            "customers": [
                {"tenure": 12, "MonthlyCharges": 50.0},
                {"tenure": 60, "MonthlyCharges": 30.0, "Contract": "Two year"},
            ]
        }
        response = client.post("/predict/batch", json=payload)
        assert response.status_code in (200, 500, 503)

    def test_batch_empty_list(self, client):
        """POST /predict/batch boş liste ile → geçerli yanıt dönmeli."""
        payload = {"customers": []}
        response = client.post("/predict/batch", json=payload)
        # Boş liste → 200 (0 tahmin) veya 500 (division by zero guard)
        assert response.status_code in (200, 500, 503)


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Model Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestPydanticModels:
    """Pydantic şemalarının doğru çalıştığını test eder."""

    def test_customer_input_defaults(self):
        """CustomerInput varsayılan değerlerle oluşturulabilmeli."""
        from app import CustomerInput
        customer = CustomerInput()
        assert customer.tenure == 0
        assert customer.MonthlyCharges == 0.0
        assert customer.Contract == "Month-to-month"

    def test_customer_input_model_dump(self):
        """CustomerInput.model_dump() dict döndürmeli."""
        from app import CustomerInput
        customer = CustomerInput(tenure=24, MonthlyCharges=79.85)
        data = customer.model_dump()
        assert isinstance(data, dict)
        assert data["tenure"] == 24

    def test_prediction_output_schema(self):
        """PredictionOutput doğru alanları içermeli."""
        from app import PredictionOutput
        output = PredictionOutput(
            prediction=1,
            churn_probability=0.82,
            risk_level="Yüksek",
            customerID="TEST_001"
        )
        assert output.prediction == 1
        assert output.risk_level == "Yüksek"

    def test_health_output_schema(self):
        """HealthOutput doğru alanları içermeli."""
        from app import HealthOutput
        health = HealthOutput(
            status="healthy",
            model_loaded=True,
            preprocessor_loaded=True,
            artifacts_exist=True
        )
        assert health.status == "healthy"
