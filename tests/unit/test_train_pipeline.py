# ============================================================================
# test_train_pipeline.py — TrainPipeline Sınıfı için Unit Testler
# ============================================================================
# TEST EDİLEN SINIF: src/pipeline/train_pipeline.py → TrainPipeline
#
# TEST STRATEJİSİ:
#   - Pipeline nesnesinin doğru oluşturulduğu test edilir
#   - Her adım metodunun varlığı doğrulanır
#   - Tam pipeline (sentetik NPZ verisi ile) çalıştırılıp sonuç kontrol edilir
#
# ÖNEMLİ: Gerçek veriye bağımlı değil — conftest.py'deki fixture'lar kullanılır.
# ============================================================================

import pytest
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Yapı Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainPipelineStructure:
    """TrainPipeline sınıfının doğru yapılandırıldığını test eder."""

    def test_pipeline_instantiation(self):
        """Pipeline nesnesi hatasız oluşturulabilmeli."""
        from src.pipeline.train_pipeline import TrainPipeline
        pipeline = TrainPipeline()
        assert pipeline is not None

    def test_pipeline_has_timings(self):
        """Pipeline nesnesi timings dict'ine sahip olmalı."""
        from src.pipeline.train_pipeline import TrainPipeline
        pipeline = TrainPipeline()
        assert isinstance(pipeline.timings, dict)

    def test_pipeline_has_step_methods(self):
        """Pipeline 4 adım metoduna sahip olmalı."""
        from src.pipeline.train_pipeline import TrainPipeline
        pipeline = TrainPipeline()
        assert hasattr(pipeline, "_step_ingestion")
        assert hasattr(pipeline, "_step_transformation")
        assert hasattr(pipeline, "_step_training")
        assert hasattr(pipeline, "_step_evaluation")

    def test_pipeline_has_run_method(self):
        """Pipeline'ın ana run() metodu olmalı."""
        from src.pipeline.train_pipeline import TrainPipeline
        pipeline = TrainPipeline()
        assert callable(getattr(pipeline, "run", None))


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Çalışma Testleri (Sentetik NPZ ile)
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainPipelineExecution:
    """Pipeline'ın uçtan uca çalışmasını sentetik veri ile test eder."""

    def test_run_returns_dict(self, tmp_path, sample_npz_arrays):
        """run() bir dict döndürmeli."""
        from src.pipeline.train_pipeline import TrainPipeline

        X_train, X_test, y_train, y_test = sample_npz_arrays
        X = np.vstack([X_train, X_test])
        y = np.concatenate([y_train, y_test])
        npz_path = str(tmp_path / "telco_prepared_dataset.npz")
        np.savez_compressed(npz_path, X=X, y=y)

        pipeline = TrainPipeline()

        # _step_ingestion'ı override et — sentetik NPZ kullan
        def mock_ingestion():
            from sklearn.model_selection import train_test_split
            data = np.load(npz_path)
            return train_test_split(
                data["X"], data["y"],
                test_size=0.2, random_state=42, stratify=data["y"]
            )

        pipeline._step_ingestion = mock_ingestion

        # Training adımını da override et — F1 eşiğini bypass et
        def mock_training(Xt, Xte, yt, yte):
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import f1_score
            import time

            pipeline.timings["training"] = 0.0
            model = LogisticRegression(random_state=42, max_iter=200)
            model.fit(Xt, yt)
            y_pred = model.predict(Xte)
            f1 = round(float(f1_score(yte, y_pred, zero_division=0)), 4)

            from src.utils.common import save_object, save_json
            save_object("artifacts/model.pkl", model)
            report = {
                "best_model": "LogisticRegression",
                "best_f1": f1,
                "all_models": {"LogisticRegression": {
                    "test_f1": f1, "test_recall": 0.5,
                    "test_precision": 0.5, "test_accuracy": 0.5,
                    "test_roc_auc": 0.5, "best_params": {},
                    "cv_best_score": 0.5
                }}
            }
            save_json(report, "artifacts/metrics.json")
            return f1, report

        pipeline._step_training = mock_training

        result = pipeline.run()
        assert isinstance(result, dict)

    def test_run_result_has_required_keys(self, tmp_path, sample_npz_arrays):
        """run() sonucu gerekli anahtarları içermeli."""
        from src.pipeline.train_pipeline import TrainPipeline

        X_train, X_test, y_train, y_test = sample_npz_arrays
        X = np.vstack([X_train, X_test])
        y = np.concatenate([y_train, y_test])
        npz_path = str(tmp_path / "telco_prepared_dataset.npz")
        np.savez_compressed(npz_path, X=X, y=y)

        pipeline = TrainPipeline()

        def mock_ingestion():
            from sklearn.model_selection import train_test_split
            data = np.load(npz_path)
            return train_test_split(
                data["X"], data["y"],
                test_size=0.2, random_state=42, stratify=data["y"]
            )

        pipeline._step_ingestion = mock_ingestion

        def mock_training(Xt, Xte, yt, yte):
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import f1_score

            pipeline.timings["training"] = 0.0
            model = LogisticRegression(random_state=42, max_iter=200)
            model.fit(Xt, yt)
            y_pred = model.predict(Xte)
            f1 = round(float(f1_score(yte, y_pred, zero_division=0)), 4)

            from src.utils.common import save_object, save_json
            save_object("artifacts/model.pkl", model)
            report = {
                "best_model": "LogisticRegression",
                "best_f1": f1,
                "all_models": {"LogisticRegression": {
                    "test_f1": f1, "test_recall": 0.5,
                    "test_precision": 0.5, "test_accuracy": 0.5,
                    "test_roc_auc": 0.5, "best_params": {},
                    "cv_best_score": 0.5
                }}
            }
            save_json(report, "artifacts/metrics.json")
            return f1, report

        pipeline._step_training = mock_training

        result = pipeline.run()

        required_keys = ["best_model", "best_f1", "timings", "mode", "total_time"]
        for key in required_keys:
            assert key in result, f"Sonuçta '{key}' anahtarı eksik"
