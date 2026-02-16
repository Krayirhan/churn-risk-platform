# ============================================================================
# test_prediction_logger.py — Tahmin Loglama Modülü Testleri
# ============================================================================

import os
import json
import pytest
import pandas as pd
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG & LOGGER FIXTURE
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def logger_with_tmp(tmp_path):
    """Geçici dizinle PredictionLogger oluşturur."""
    from src.components.prediction_logger import PredictionLogger, PredictionLoggerConfig
    config = PredictionLoggerConfig()
    config.log_dir = str(tmp_path / "predictions")
    config.enabled = True
    config.file_prefix = "predictions"
    config.max_retention_days = 90
    return PredictionLogger(config=config)


@pytest.fixture
def sample_prediction():
    """Örnek tahmin verileri."""
    return {
        "input_features": {
            "tenure": 24,
            "MonthlyCharges": 79.85,
            "TotalCharges": 1916.4,
            "Contract": "Month-to-month",
        },
        "prediction": 1,
        "churn_probability": 0.82,
        "risk_level": "Yüksek",
        "customer_id": "CUST-0001",
    }


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestPredictionLoggerConfig:
    """Config testleri."""

    def test_config_loads(self):
        from src.components.prediction_logger import PredictionLoggerConfig
        config = PredictionLoggerConfig()
        assert config.enabled is True

    def test_config_has_log_dir(self):
        from src.components.prediction_logger import PredictionLoggerConfig
        config = PredictionLoggerConfig()
        assert config.log_dir is not None

    def test_config_has_prefix(self):
        from src.components.prediction_logger import PredictionLoggerConfig
        config = PredictionLoggerConfig()
        assert config.file_prefix == "predictions"


# ─────────────────────────────────────────────────────────────────────────────
# LOG YAZMA TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestPredictionLogWrite:
    """Tahmin loglama testleri."""

    def test_log_creates_file(self, logger_with_tmp, sample_prediction):
        """Log dosyası oluşturulmalı."""
        path = logger_with_tmp.log(**sample_prediction)
        assert os.path.exists(path)

    def test_log_file_is_jsonl(self, logger_with_tmp, sample_prediction):
        """Log dosyası geçerli JSONL formatında olmalı."""
        path = logger_with_tmp.log(**sample_prediction)
        with open(path, "r") as f:
            line = f.readline()
        data = json.loads(line)
        assert "timestamp" in data
        assert "prediction" in data

    def test_log_contains_all_fields(self, logger_with_tmp, sample_prediction):
        """Log kaydı tüm alanları içermeli."""
        path = logger_with_tmp.log(**sample_prediction)
        with open(path, "r") as f:
            data = json.loads(f.readline())
        expected_keys = {"timestamp", "customerID", "prediction",
                         "churn_probability", "risk_level", "model_version",
                         "input_features"}
        assert expected_keys.issubset(set(data.keys()))

    def test_log_appends_multiple(self, logger_with_tmp, sample_prediction):
        """Birden fazla log satırı eklenebilmeli (append)."""
        logger_with_tmp.log(**sample_prediction)
        logger_with_tmp.log(**sample_prediction)
        logger_with_tmp.log(**sample_prediction)
        path = logger_with_tmp._get_log_path()
        with open(path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 3

    def test_log_disabled_returns_empty(self, tmp_path):
        """Devre dışıyken boş string döndürmeli."""
        from src.components.prediction_logger import PredictionLogger, PredictionLoggerConfig
        config = PredictionLoggerConfig()
        config.enabled = False
        config.log_dir = str(tmp_path / "disabled")
        logger = PredictionLogger(config=config)
        result = logger.log(
            input_features={}, prediction=0,
            churn_probability=0.1, risk_level="Düşük"
        )
        assert result == ""

    def test_log_with_extra_metadata(self, logger_with_tmp):
        """Extra metadata eklenebilmeli."""
        path = logger_with_tmp.log(
            input_features={"tenure": 5},
            prediction=0,
            churn_probability=0.15,
            risk_level="Düşük",
            extra={"source": "api", "latency_ms": 42},
        )
        with open(path, "r") as f:
            data = json.loads(f.readline())
        assert "extra" in data
        assert data["extra"]["source"] == "api"


# ─────────────────────────────────────────────────────────────────────────────
# LOG OKUMA TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestPredictionLogRead:
    """Tahmin logu okuma testleri."""

    def test_get_recent_returns_dataframe(self, logger_with_tmp, sample_prediction):
        """get_recent DataFrame döndürmeli."""
        logger_with_tmp.log(**sample_prediction)
        df = logger_with_tmp.get_recent(n=10, days=1)
        assert isinstance(df, pd.DataFrame)

    def test_get_recent_returns_correct_count(self, logger_with_tmp, sample_prediction):
        """Doğru sayıda log satırı okunmalı."""
        for _ in range(5):
            logger_with_tmp.log(**sample_prediction)
        df = logger_with_tmp.get_recent(n=10, days=1)
        assert len(df) == 5

    def test_get_recent_limit(self, logger_with_tmp, sample_prediction):
        """n parametresi doğru çalışmalı."""
        for _ in range(10):
            logger_with_tmp.log(**sample_prediction)
        df = logger_with_tmp.get_recent(n=3, days=1)
        assert len(df) == 3

    def test_get_recent_empty_returns_empty_df(self, logger_with_tmp):
        """Log yokken boş DataFrame dönmeli."""
        df = logger_with_tmp.get_recent(n=10, days=1)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_get_features_df_flattens_inputs(self, logger_with_tmp, sample_prediction):
        """get_features_df input_features'ı düz sütunlara açmalı."""
        logger_with_tmp.log(**sample_prediction)
        features = logger_with_tmp.get_features_df(n=10, days=1)
        assert isinstance(features, pd.DataFrame)
        assert "tenure" in features.columns


# ─────────────────────────────────────────────────────────────────────────────
# İSTATİSTİK TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestPredictionLogStats:
    """İstatistik hesaplama testleri."""

    def test_stats_has_required_keys(self, logger_with_tmp, sample_prediction):
        """Stats gerekli key'leri içermeli."""
        for _ in range(5):
            logger_with_tmp.log(**sample_prediction)
        stats = logger_with_tmp.get_stats(days=1)
        assert "total_predictions" in stats
        assert stats["total_predictions"] == 5

    def test_stats_empty_log(self, logger_with_tmp):
        """Boş logda total_predictions=0 dönmeli."""
        stats = logger_with_tmp.get_stats(days=1)
        assert stats["total_predictions"] == 0

    def test_stats_churn_rate(self, logger_with_tmp):
        """Churn oranı doğru hesaplanmalı."""
        # 3 churn, 2 non-churn → %60
        for _ in range(3):
            logger_with_tmp.log(
                input_features={}, prediction=1,
                churn_probability=0.8, risk_level="Yüksek"
            )
        for _ in range(2):
            logger_with_tmp.log(
                input_features={}, prediction=0,
                churn_probability=0.2, risk_level="Düşük"
            )
        stats = logger_with_tmp.get_stats(days=1)
        assert stats["churn_rate"] == 60.0
