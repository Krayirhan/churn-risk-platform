# ============================================================================
# test_drift_detector.py — Drift Algılama Modülü Testleri
# ============================================================================

import os
import json
import pytest
import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE'LAR
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def reference_df():
    """Eğitim verisini simüle eden DataFrame."""
    np.random.seed(42)
    n = 200
    return pd.DataFrame({
        "tenure": np.random.randint(0, 73, n),
        "MonthlyCharges": np.round(np.random.uniform(18, 118, n), 2),
        "TotalCharges": np.round(np.random.uniform(0, 8000, n), 2),
        "Contract": np.random.choice(
            ["Month-to-month", "One year", "Two year"], n, p=[0.55, 0.25, 0.20]
        ),
        "InternetService": np.random.choice(
            ["DSL", "Fiber optic", "No"], n, p=[0.34, 0.44, 0.22]
        ),
        "PaymentMethod": np.random.choice(
            ["Electronic check", "Mailed check",
             "Bank transfer (automatic)", "Credit card (automatic)"],
            n, p=[0.34, 0.23, 0.22, 0.21]
        ),
    })


@pytest.fixture
def stable_production_df(reference_df):
    """Eğitim verisiyle aynı dağılımda production verisi (drift YOK)."""
    np.random.seed(123)
    n = 100
    return pd.DataFrame({
        "tenure": np.random.randint(0, 73, n),
        "MonthlyCharges": np.round(np.random.uniform(18, 118, n), 2),
        "TotalCharges": np.round(np.random.uniform(0, 8000, n), 2),
        "Contract": np.random.choice(
            ["Month-to-month", "One year", "Two year"], n, p=[0.55, 0.25, 0.20]
        ),
        "InternetService": np.random.choice(
            ["DSL", "Fiber optic", "No"], n, p=[0.34, 0.44, 0.22]
        ),
        "PaymentMethod": np.random.choice(
            ["Electronic check", "Mailed check",
             "Bank transfer (automatic)", "Credit card (automatic)"],
            n, p=[0.34, 0.23, 0.22, 0.21]
        ),
    })


@pytest.fixture
def drifted_production_df():
    """Belirgin drift olan production verisi."""
    np.random.seed(999)
    n = 100
    return pd.DataFrame({
        # Sayısal: çok farklı dağılım
        "tenure": np.random.randint(50, 73, n),        # Hep yüksek tenure
        "MonthlyCharges": np.round(np.random.uniform(90, 200, n), 2),  # Çok yüksek
        "TotalCharges": np.round(np.random.uniform(5000, 15000, n), 2),
        # Kategorik: tamamen farklı dağılım
        "Contract": np.random.choice(
            ["Month-to-month", "One year", "Two year"], n, p=[0.10, 0.10, 0.80]
        ),
        "InternetService": np.random.choice(
            ["DSL", "Fiber optic", "No"], n, p=[0.05, 0.90, 0.05]
        ),
        "PaymentMethod": np.random.choice(
            ["Electronic check", "Mailed check",
             "Bank transfer (automatic)", "Credit card (automatic)"],
            n, p=[0.70, 0.10, 0.10, 0.10]
        ),
    })


# ─────────────────────────────────────────────────────────────────────────────
# PSI HESAPLAMA TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestPSIComputation:
    """Population Stability Index hesaplama testleri."""

    def test_identical_distributions_psi_near_zero(self):
        """Aynı dağılımda PSI ≈ 0 olmalı."""
        from src.components.drift_detector import compute_psi
        np.random.seed(42)
        data = np.random.randn(1000)
        psi = compute_psi(data, data)
        assert psi < 0.01

    def test_different_distributions_psi_high(self):
        """Farklı dağılımlarda PSI yüksek olmalı."""
        from src.components.drift_detector import compute_psi
        ref = np.random.randn(1000)
        cur = np.random.randn(1000) + 5  # Çok farklı dağılım
        psi = compute_psi(ref, cur)
        assert psi > 0.1

    def test_psi_returns_float(self):
        """PSI float döndürmeli."""
        from src.components.drift_detector import compute_psi
        result = compute_psi(np.array([1, 2, 3, 4, 5]), np.array([2, 3, 4, 5, 6]))
        assert isinstance(result, float)

    def test_psi_nonnegative(self):
        """PSI negatif olmamalı."""
        from src.components.drift_detector import compute_psi
        np.random.seed(42)
        psi = compute_psi(np.random.randn(100), np.random.randn(100) + 1)
        assert psi >= 0


class TestCategoricalPSI:
    """Kategorik PSI testleri."""

    def test_identical_categorical_psi_near_zero(self):
        """Aynı kategorik dağılımda PSI ≈ 0."""
        from src.components.drift_detector import compute_categorical_psi
        ref = {"A": 0.5, "B": 0.3, "C": 0.2}
        cur = pd.Series(["A"] * 50 + ["B"] * 30 + ["C"] * 20)
        psi = compute_categorical_psi(ref, cur)
        assert psi < 0.05

    def test_different_categorical_psi_high(self):
        """Farklı kategorik dağılımda PSI yüksek."""
        from src.components.drift_detector import compute_categorical_psi
        ref = {"A": 0.8, "B": 0.1, "C": 0.1}
        cur = pd.Series(["A"] * 10 + ["B"] * 10 + ["C"] * 80)
        psi = compute_categorical_psi(ref, cur)
        assert psi > 0.2


# ─────────────────────────────────────────────────────────────────────────────
# DRIFT DETECTOR TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestDriftDetectorConfig:
    """DriftDetectorConfig testleri."""

    def test_config_loads(self):
        from src.components.drift_detector import DriftDetectorConfig
        config = DriftDetectorConfig()
        assert config.enabled is True

    def test_config_has_num_features(self):
        from src.components.drift_detector import DriftDetectorConfig
        config = DriftDetectorConfig()
        assert len(config.num_features) > 0

    def test_config_has_cat_features(self):
        from src.components.drift_detector import DriftDetectorConfig
        config = DriftDetectorConfig()
        assert len(config.cat_features) > 0


class TestDriftDetectorSaveReference:
    """Referans istatistik kaydetme testleri."""

    def test_save_reference_creates_file(self, reference_df, tmp_path):
        from src.components.drift_detector import DriftDetector, DriftDetectorConfig
        config = DriftDetectorConfig()
        config.reference_data_path = str(tmp_path / "ref_stats.json")
        detector = DriftDetector(config=config)
        path = detector.save_reference_stats(reference_df)
        assert os.path.exists(path)

    def test_reference_file_has_numerical(self, reference_df, tmp_path):
        from src.components.drift_detector import DriftDetector, DriftDetectorConfig
        config = DriftDetectorConfig()
        config.reference_data_path = str(tmp_path / "ref_stats2.json")
        detector = DriftDetector(config=config)
        detector.save_reference_stats(reference_df)
        with open(config.reference_data_path) as f:
            data = json.load(f)
        assert "numerical" in data
        assert "tenure" in data["numerical"]

    def test_reference_file_has_categorical(self, reference_df, tmp_path):
        from src.components.drift_detector import DriftDetector, DriftDetectorConfig
        config = DriftDetectorConfig()
        config.reference_data_path = str(tmp_path / "ref_stats3.json")
        detector = DriftDetector(config=config)
        detector.save_reference_stats(reference_df)
        with open(config.reference_data_path) as f:
            data = json.load(f)
        assert "categorical" in data
        assert "Contract" in data["categorical"]


class TestDriftDetectorAnalyze:
    """Drift analizi testleri."""

    def test_analyze_stable_no_drift(self, reference_df, stable_production_df, tmp_path):
        """Stabil veride drift algılanmamalı."""
        from src.components.drift_detector import DriftDetector, DriftDetectorConfig
        config = DriftDetectorConfig()
        config.reference_data_path = str(tmp_path / "ref_stable.json")
        config.min_sample_size = 10
        detector = DriftDetector(config=config)
        detector.save_reference_stats(reference_df)
        report = detector.analyze(stable_production_df)
        assert report["alert_level"] in ("none", "warning")

    def test_analyze_drifted_detects(self, reference_df, drifted_production_df, tmp_path):
        """Belirgin drift'te en az bir feature drift algılanmalı."""
        from src.components.drift_detector import DriftDetector, DriftDetectorConfig
        config = DriftDetectorConfig()
        config.reference_data_path = str(tmp_path / "ref_drifted.json")
        config.min_sample_size = 10
        detector = DriftDetector(config=config)
        detector.save_reference_stats(reference_df)
        report = detector.analyze(drifted_production_df)
        assert len(report["drifted_features"]) > 0

    def test_analyze_returns_required_keys(self, reference_df, stable_production_df, tmp_path):
        """Rapor gerekli key'leri içermeli."""
        from src.components.drift_detector import DriftDetector, DriftDetectorConfig
        config = DriftDetectorConfig()
        config.reference_data_path = str(tmp_path / "ref_keys.json")
        config.min_sample_size = 10
        detector = DriftDetector(config=config)
        detector.save_reference_stats(reference_df)
        report = detector.analyze(stable_production_df)
        required = {"drift_detected", "drifted_features", "total_features_checked",
                     "drift_ratio", "alert_level", "numerical_results", "categorical_results"}
        assert required.issubset(set(report.keys()))

    def test_analyze_insufficient_samples(self, reference_df, tmp_path):
        """Yetersiz örnekte drift analizi yapılmamalı."""
        from src.components.drift_detector import DriftDetector, DriftDetectorConfig
        config = DriftDetectorConfig()
        config.reference_data_path = str(tmp_path / "ref_small.json")
        config.min_sample_size = 1000  # Çok yüksek eşik
        detector = DriftDetector(config=config)
        detector.save_reference_stats(reference_df)
        small_df = reference_df.head(5)
        report = detector.analyze(small_df)
        assert report["drift_detected"] is False

    def test_analyze_disabled_returns_false(self, tmp_path):
        """Drift devre dışıyken False döndürmeli."""
        from src.components.drift_detector import DriftDetector, DriftDetectorConfig
        config = DriftDetectorConfig()
        config.enabled = False
        detector = DriftDetector(config=config)
        report = detector.analyze(pd.DataFrame({"a": [1]}))
        assert report["drift_detected"] is False
