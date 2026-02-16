# ============================================================================
# test_predict_pipeline.py — PredictPipeline ve CustomData için Unit Testler
# ============================================================================
# TEST EDİLEN SINIFLAR:
#   src/pipeline/predict_pipeline.py → PredictPipeline, CustomData, classify_risk
#
# TEST STRATEJİSİ:
#   - CustomData: Doğrulama, DataFrame dönüşümü, from_dict fabrika metodu
#   - classify_risk: Risk seviyesi eşik kontrolü
#   - PredictPipeline: Yapı ve konfigürasyon testleri
#     (tam predict testi integration test'te yapılır)
# ============================================================================

import pytest
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# CustomData Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestCustomData:
    """CustomData dataclass'ının doğru çalıştığını test eder."""

    def test_default_creation(self):
        """Varsayılan değerlerle oluşturulabilmeli."""
        from src.pipeline.predict_pipeline import CustomData
        data = CustomData()
        assert data.tenure == 0
        assert data.MonthlyCharges == 0.0
        assert data.customerID == "PREDICT_USER"

    def test_custom_creation(self):
        """Özel değerlerle oluşturulabilmeli."""
        from src.pipeline.predict_pipeline import CustomData
        data = CustomData(tenure=24, MonthlyCharges=79.85, Contract="One year")
        assert data.tenure == 24
        assert data.MonthlyCharges == 79.85
        assert data.Contract == "One year"

    def test_to_dataframe_returns_df(self):
        """to_dataframe() tek satırlık DataFrame döndürmeli."""
        from src.pipeline.predict_pipeline import CustomData
        data = CustomData(tenure=12, MonthlyCharges=50.0)
        df = data.to_dataframe()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_to_dataframe_has_columns(self):
        """DataFrame tüm sütunları içermeli."""
        from src.pipeline.predict_pipeline import CustomData
        data = CustomData()
        df = data.to_dataframe()

        expected_cols = [
            "tenure", "MonthlyCharges", "TotalCharges", "gender",
            "Contract", "InternetService", "customerID"
        ]
        for col in expected_cols:
            assert col in df.columns, f"'{col}' sütunu eksik"

    def test_from_dict_filters_unknown_keys(self):
        """from_dict() bilinmeyen anahtarları sessizce yok saymalı."""
        from src.pipeline.predict_pipeline import CustomData
        input_dict = {
            "tenure": 36,
            "MonthlyCharges": 99.0,
            "unknown_field": "test",       # Bu alan yok sayılmalı
            "timestamp": "2025-01-01",     # Bu da yok sayılmalı
        }
        data = CustomData.from_dict(input_dict)
        assert data.tenure == 36
        assert data.MonthlyCharges == 99.0
        assert not hasattr(data, "unknown_field")

    def test_from_dict_uses_defaults_for_missing(self):
        """from_dict() eksik alanlar için varsayılan kullanmalı."""
        from src.pipeline.predict_pipeline import CustomData
        data = CustomData.from_dict({"tenure": 6})
        assert data.tenure == 6
        assert data.MonthlyCharges == 0.0  # Varsayılan
        assert data.Contract == "Month-to-month"  # Varsayılan


# ─────────────────────────────────────────────────────────────────────────────
# classify_risk Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyRisk:
    """Risk seviyesi sınıflandırma fonksiyonunu test eder."""

    def test_low_risk(self):
        """Olasılık < 0.3 → Düşük risk."""
        from src.pipeline.predict_pipeline import classify_risk
        assert classify_risk(0.0) == "Düşük"
        assert classify_risk(0.15) == "Düşük"
        assert classify_risk(0.29) == "Düşük"

    def test_medium_risk(self):
        """0.3 ≤ olasılık < 0.6 → Orta risk."""
        from src.pipeline.predict_pipeline import classify_risk
        assert classify_risk(0.3) == "Orta"
        assert classify_risk(0.45) == "Orta"
        assert classify_risk(0.59) == "Orta"

    def test_high_risk(self):
        """Olasılık ≥ 0.6 → Yüksek risk."""
        from src.pipeline.predict_pipeline import classify_risk
        assert classify_risk(0.6) == "Yüksek"
        assert classify_risk(0.85) == "Yüksek"
        assert classify_risk(1.0) == "Yüksek"

    def test_boundary_values(self):
        """Sınır değerleri doğru sınıflandırılmalı."""
        from src.pipeline.predict_pipeline import classify_risk
        assert classify_risk(0.3) == "Orta"    # Alt sınır: Orta
        assert classify_risk(0.6) == "Yüksek"  # Alt sınır: Yüksek


# ─────────────────────────────────────────────────────────────────────────────
# PredictPipeline Yapı Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestPredictPipelineStructure:
    """PredictPipeline sınıfının yapısını test eder."""

    def test_pipeline_instantiation(self):
        """Pipeline nesnesi hatasız oluşturulabilmeli."""
        from src.pipeline.predict_pipeline import PredictPipeline
        pipeline = PredictPipeline()
        assert pipeline is not None

    def test_pipeline_has_predict_method(self):
        """Pipeline predict() metoduna sahip olmalı."""
        from src.pipeline.predict_pipeline import PredictPipeline
        pipeline = PredictPipeline()
        assert callable(getattr(pipeline, "predict", None))

    def test_pipeline_has_predict_batch_method(self):
        """Pipeline predict_batch() metoduna sahip olmalı."""
        from src.pipeline.predict_pipeline import PredictPipeline
        pipeline = PredictPipeline()
        assert callable(getattr(pipeline, "predict_batch", None))

    def test_pipeline_lazy_loading(self):
        """Model ve preprocessor başlangıçta None olmalı (lazy loading)."""
        from src.pipeline.predict_pipeline import PredictPipeline
        pipeline = PredictPipeline()
        assert pipeline._model is None
        assert pipeline._preprocessor is None

    def test_predict_without_model_raises(self):
        """Model dosyası yokken predict() hata fırlatmalı."""
        from src.pipeline.predict_pipeline import PredictPipeline
        pipeline = PredictPipeline()
        pipeline.model_path = "nonexistent/model.pkl"
        pipeline.preprocessor_path = "nonexistent/preprocessor.pkl"

        with pytest.raises(Exception):
            pipeline.predict({"tenure": 12, "MonthlyCharges": 50.0})
