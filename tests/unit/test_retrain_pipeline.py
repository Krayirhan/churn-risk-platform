# ============================================================================
# test_retrain_pipeline.py — Retrain Pipeline Testleri
# ============================================================================

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# YAPI TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestRetrainPipelineStructure:
    """RetrainPipeline yapısal testleri."""

    def test_instantiation(self):
        """Pipeline oluşturulabilmeli."""
        from src.pipeline.retrain_pipeline import RetrainPipeline
        pipeline = RetrainPipeline()
        assert pipeline is not None

    def test_has_run_method(self):
        """run() metodu olmalı."""
        from src.pipeline.retrain_pipeline import RetrainPipeline
        pipeline = RetrainPipeline()
        assert hasattr(pipeline, "run")

    def test_has_enabled_flag(self):
        """enabled flag'i olmalı."""
        from src.pipeline.retrain_pipeline import RetrainPipeline
        pipeline = RetrainPipeline()
        assert hasattr(pipeline, "enabled")

    def test_has_auto_retrain_flag(self):
        """auto_retrain flag'i olmalı."""
        from src.pipeline.retrain_pipeline import RetrainPipeline
        pipeline = RetrainPipeline()
        assert hasattr(pipeline, "auto_retrain")


# ─────────────────────────────────────────────────────────────────────────────
# KARAR MANTIK TESTLERİ
# ─────────────────────────────────────────────────────────────────────────────

class TestRetrainDecisionLogic:
    """Retrain karar mantığı testleri (mock ile — gerçek eğitim yapmaz)."""

    def test_disabled_returns_not_retrained(self):
        """enabled=False ise retrain yapılmamalı."""
        from src.pipeline.retrain_pipeline import RetrainPipeline
        pipeline = RetrainPipeline()
        pipeline.enabled = False
        result = pipeline.run(reason="manual", force=False)
        assert result["retrained"] is False

    def test_auto_retrain_off_blocks_non_manual(self):
        """auto_retrain=False ve manual olmayan neden → iptal."""
        from src.pipeline.retrain_pipeline import RetrainPipeline
        pipeline = RetrainPipeline()
        pipeline.enabled = True
        pipeline.auto_retrain = False
        result = pipeline.run(reason="drift_detected", force=False)
        assert result["retrained"] is False

    def test_monitoring_report_no_retrain_needed(self):
        """Monitoring raporu retrain gerektirmiyorsa iptal."""
        from src.pipeline.retrain_pipeline import RetrainPipeline
        pipeline = RetrainPipeline()
        pipeline.enabled = True
        pipeline.auto_retrain = True
        report = {"needs_retrain": False}
        result = pipeline.run(reason="scheduled", monitoring_report=report, force=False)
        assert result["retrained"] is False

    @patch("src.pipeline.train_pipeline.TrainPipeline")
    @patch("src.pipeline.retrain_pipeline.RetrainPipeline._update_reference_stats")
    @patch("src.components.model_monitor.ModelMonitor.log_retrain_event")
    @patch("src.components.model_monitor.ModelMonitor.can_retrain", return_value=True)
    def test_force_bypasses_all_checks(
        self, mock_can, mock_log, mock_ref, mock_train_cls
    ):
        """force=True ile tüm kontroller atlanmalı ve eğitim başlamalı."""
        mock_train = MagicMock()
        mock_train.run.return_value = {
            "best_model": "MockModel",
            "best_f1": 0.99,
            "total_time": "1s",
            "mode": "test",
            "timings": {},
        }
        mock_train_cls.return_value = mock_train

        from src.pipeline.retrain_pipeline import RetrainPipeline
        pipeline = RetrainPipeline()
        result = pipeline.run(reason="manual", force=True)

        assert result["retrained"] is True
        assert result["reason"] == "manual"
        mock_train.run.assert_called_once()

    def test_result_has_required_keys(self):
        """Sonuç dict'i gerekli key'leri içermeli."""
        from src.pipeline.retrain_pipeline import RetrainPipeline
        pipeline = RetrainPipeline()
        pipeline.enabled = False
        result = pipeline.run(reason="test")
        required = {"retrained", "reason", "result", "message", "timestamp"}
        assert required.issubset(set(result.keys()))

    def test_result_has_timestamp(self):
        """Sonuçta timestamp olmalı."""
        from src.pipeline.retrain_pipeline import RetrainPipeline
        pipeline = RetrainPipeline()
        pipeline.enabled = False
        result = pipeline.run(reason="test")
        assert "timestamp" in result
        # ISO format olmalı
        datetime.fromisoformat(result["timestamp"])
