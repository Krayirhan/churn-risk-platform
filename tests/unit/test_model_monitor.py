# ============================================================================
# test_model_monitor.py — Model Performans İzleme Testleri
# ============================================================================

import os
import json
import pytest
from datetime import datetime, timedelta


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE'LAR
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def baseline_metrics_file(tmp_path):
    """Baseline metrik dosyası oluşturur."""
    metrics = {
        "model_name": "XGBClassifier",
        "metrics": {
            "accuracy": 0.80,
            "f1": 0.62,
            "recall": 0.55,
            "precision": 0.71,
            "roc_auc": 0.85,
        },
    }
    path = tmp_path / "metrics.json"
    with open(path, "w") as f:
        json.dump(metrics, f)
    return str(path)


@pytest.fixture
def monitor_with_baseline(tmp_path, baseline_metrics_file):
    """Baseline dosyası ile ModelMonitor oluşturur."""
    from src.components.model_monitor import ModelMonitor, ModelMonitorConfig
    config = ModelMonitorConfig()
    config.baseline_path = baseline_metrics_file
    config.history_path = str(tmp_path / "retrain_history.json")
    config.cooldown_hours = 24
    return ModelMonitor(config=config)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestModelMonitorConfig:
    """Config testleri."""

    def test_config_loads(self):
        from src.components.model_monitor import ModelMonitorConfig
        config = ModelMonitorConfig()
        assert config.enabled is True

    def test_config_has_thresholds(self):
        from src.components.model_monitor import ModelMonitorConfig
        config = ModelMonitorConfig()
        assert "f1" in config.degradation_thresholds


# ─────────────────────────────────────────────────────────────────────────────
# PERFORMANS KONTROLÜ TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPerformance:
    """Performans karşılaştırma testleri."""

    def test_healthy_performance(self, monitor_with_baseline):
        """Baseline'a yakın metrikler 'healthy' döndürmeli."""
        current = {"f1": 0.61, "recall": 0.54, "precision": 0.70, "roc_auc": 0.84}
        result = monitor_with_baseline.check_performance(current)
        assert result["performance_ok"] is True
        assert result["status"] == "healthy"

    def test_degraded_performance(self, monitor_with_baseline):
        """Ciddi düşüşte 'degraded' veya 'critical' döndürmeli."""
        current = {"f1": 0.30, "recall": 0.25, "precision": 0.35, "roc_auc": 0.60}
        result = monitor_with_baseline.check_performance(current)
        assert result["performance_ok"] is False
        assert len(result["degraded_metrics"]) > 0

    def test_comparisons_has_correct_structure(self, monitor_with_baseline):
        """Karşılaştırma dict'i doğru yapıda olmalı."""
        current = {"f1": 0.58, "recall": 0.50, "precision": 0.68, "roc_auc": 0.82}
        result = monitor_with_baseline.check_performance(current)
        for metric, comp in result["comparisons"].items():
            assert "baseline" in comp
            assert "current" in comp
            assert "drop_pct" in comp
            assert "degraded" in comp

    def test_single_degraded_metric(self, monitor_with_baseline):
        """Tek metrik bozulduğunda status='degraded' olmalı."""
        current = {"f1": 0.30, "recall": 0.54, "precision": 0.70, "roc_auc": 0.84}
        result = monitor_with_baseline.check_performance(current)
        assert result["status"] in ("degraded", "critical")

    def test_returns_required_keys(self, monitor_with_baseline):
        """Sonuç gerekli key'leri içermeli."""
        current = {"f1": 0.60, "recall": 0.54}
        result = monitor_with_baseline.check_performance(current)
        required = {"performance_ok", "degraded_metrics", "comparisons", "status"}
        assert required.issubset(set(result.keys()))


# ─────────────────────────────────────────────────────────────────────────────
# TAM KONTROL TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestFullCheck:
    """full_check() birleşik kontrol testleri."""

    def test_stable_when_no_issues(self, monitor_with_baseline):
        """Her şey OK ise 'stable' döndürmeli."""
        current = {"f1": 0.61, "recall": 0.54, "precision": 0.70, "roc_auc": 0.84}
        drift_report = {"drift_detected": False, "drift_ratio": 0, "drifted_features": [], "alert_level": "none"}
        result = monitor_with_baseline.full_check(current, drift_report)
        assert result["overall_status"] == "stable"
        assert result["needs_retrain"] is False

    def test_retrain_needed_with_both_issues(self, monitor_with_baseline):
        """Hem drift hem performans sorunu varsa retrain gerekli."""
        current = {"f1": 0.30, "recall": 0.25, "precision": 0.35, "roc_auc": 0.60}
        drift_report = {"drift_detected": True, "drift_ratio": 0.5, "drifted_features": ["tenure"], "alert_level": "critical"}
        result = monitor_with_baseline.full_check(current, drift_report)
        assert result["overall_status"] == "retrain_needed"
        assert result["needs_retrain"] is True

    def test_drift_warning_performance_ok(self, monitor_with_baseline):
        """Drift var ama performans OK → retrain gerekmez."""
        current = {"f1": 0.61, "recall": 0.54, "precision": 0.70, "roc_auc": 0.84}
        drift_report = {"drift_detected": True, "drift_ratio": 0.5, "drifted_features": ["tenure"], "alert_level": "critical"}
        result = monitor_with_baseline.full_check(current, drift_report)
        assert result["overall_status"] == "drift_warning"
        assert result["needs_retrain"] is False

    def test_degraded_no_drift(self, monitor_with_baseline):
        """Performans düşmüş drift yok → retrain gerekli."""
        current = {"f1": 0.30, "recall": 0.25, "precision": 0.35, "roc_auc": 0.60}
        drift_report = {"drift_detected": False, "drift_ratio": 0, "drifted_features": [], "alert_level": "none"}
        result = monitor_with_baseline.full_check(current, drift_report)
        assert result["overall_status"] == "degraded"
        assert result["needs_retrain"] is True

    def test_full_check_has_timestamp(self, monitor_with_baseline):
        """Rapor timestamp içermeli."""
        result = monitor_with_baseline.full_check()
        assert "timestamp" in result


# ─────────────────────────────────────────────────────────────────────────────
# RETRAİN GEÇMİŞİ TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestRetrainHistory:
    """Retrain geçmişi testleri."""

    def test_empty_history(self, monitor_with_baseline):
        """Boş geçmiş dönmeli."""
        history = monitor_with_baseline.get_retrain_history()
        assert isinstance(history, list)
        assert len(history) == 0

    def test_log_retrain_event(self, monitor_with_baseline):
        """Retrain olayı kaydedilmeli."""
        monitor_with_baseline.log_retrain_event("manual", {"best_model": "XGB", "best_f1": 0.65})
        history = monitor_with_baseline.get_retrain_history()
        assert len(history) == 1
        assert history[0]["reason"] == "manual"

    def test_can_retrain_initially(self, monitor_with_baseline):
        """İlk durumda retrain yapılabilmeli."""
        assert monitor_with_baseline.can_retrain() is True

    def test_cooldown_blocks_retrain(self, monitor_with_baseline):
        """Cooldown süresi içinde retrain engellenebilmeli."""
        # Yeni retrain logla
        monitor_with_baseline.log_retrain_event("manual", {"best_model": "XGB", "best_f1": 0.65})
        # Cooldown 24 saat → hemen tekrar False döndürmeli
        assert monitor_with_baseline.can_retrain() is False
