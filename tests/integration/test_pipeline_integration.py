# ============================================================================
# test_pipeline_integration.py — Uçtan Uca Pipeline Entegrasyon Testi
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Unit testler her bileşeni izole test eder.
#   Integration testi ise bileşenlerin BİRLİKTE doğru çalıştığını test eder:
#     DataIngestion → DataTransformation → ModelTrainer → ModelEvaluation
#
# BU TEST NE YAPAR?
#   1. Sentetik .npz dosyası oluşturur (Notebook simülasyonu)
#   2. DataIngestion ile yükler
#   3. ModelTrainer ile 4 modeli eğitip en iyisini seçer
#   4. ModelEvaluation ile değerlendirir
#   5. Tüm artifact'ların oluştuğunu doğrular
#
# NOT: Bu test yavaş çalışabilir (~30-60 sn) çünkü GridSearchCV yapılır.
#      CI/CD'de ayrı bir "slow tests" grubunda çalıştırılabilir.
# ============================================================================

import os
import pytest
import numpy as np


@pytest.mark.integration
class TestFullPipeline:
    """Ingestion → Training → Evaluation tam akış testi."""

    def test_npz_mode_full_pipeline(self, tmp_path):
        """
        MOD 1 (NPZ): Notebook artifact'ından tam pipeline akışı.
        Bu test notebook'un çıktısını simüle eder.
        """
        from src.components.data_ingestion import DataIngestion
        from src.components.model_trainer import ModelTrainer
        from src.components.model_evaluation import ModelEvaluation

        # ─── HAZIRLIK: Sentetik NPZ oluştur ───
        np.random.seed(42)
        n, f = 300, 25
        X = np.random.randn(n, f)
        y = np.random.choice([0, 1], n, p=[0.73, 0.27])

        npz_path = str(tmp_path / "telco_prepared_dataset.npz")
        np.savez_compressed(npz_path, X=X, y=y)

        # ─── ADIM 1: DataIngestion ───
        ingestion = DataIngestion()
        ingestion.config.npz_path = npz_path
        X_train, X_test, y_train, y_test = ingestion._load_from_notebook_npz()

        # Boyut kontrolü
        assert X_train.shape[0] + X_test.shape[0] == n
        assert X_train.shape[1] == f

        # ─── ADIM 2: ModelTrainer ───
        trainer = ModelTrainer()
        trainer.config.min_acceptable_f1 = 0.0  # Sentetik veri → eşik düşür
        best_f1, report = trainer.initiate(X_train, X_test, y_train, y_test)

        # Sonuç kontrolü
        assert isinstance(best_f1, float)
        assert "best_model" in report
        assert len(report["all_models"]) >= 2

        # ─── ADIM 3: ModelEvaluation ───
        evaluator = ModelEvaluation()
        eval_result = evaluator.initiate(
            X_test=X_test,
            y_test=y_test,
            model_name=report["best_model"]
        )

        # Metrik kontrolü
        assert "metrics" in eval_result
        assert "confusion_matrix" in eval_result
        assert eval_result["metrics"]["f1"] is not None

        # ─── ADIM 4: Artifact Kontrolü ───
        assert os.path.exists(trainer.config.model_path), \
            "model.pkl oluşturulmadı!"
        assert os.path.exists(evaluator.config.metrics_path), \
            "metrics.json oluşturulmadı!"
        assert os.path.exists(evaluator.config.confusion_matrix_path), \
            "confusion_matrix.json oluşturulmadı!"

    def test_pipeline_produces_consistent_churn_rate(self, tmp_path):
        """
        Stratified split sonrası train ve test'teki churn oranları
        orijinal oranla tutarlı olmalı (±%5 tolerans).
        """
        from src.components.data_ingestion import DataIngestion

        np.random.seed(42)
        n = 500
        churn_rate = 0.27
        X = np.random.randn(n, 10)
        y = np.random.choice([0, 1], n, p=[1 - churn_rate, churn_rate])

        npz_path = str(tmp_path / "telco_prepared_dataset.npz")
        np.savez_compressed(npz_path, X=X, y=y)

        ingestion = DataIngestion()
        ingestion.config.npz_path = npz_path
        _, _, y_train, y_test = ingestion._load_from_notebook_npz()

        original_rate = y.mean()
        train_rate = y_train.mean()
        test_rate = y_test.mean()

        # Stratified split churn oranını korumalı (±%5 tolerans)
        assert abs(train_rate - original_rate) < 0.05, \
            f"Train churn oranı ({train_rate:.3f}) orijinalden ({original_rate:.3f}) çok farklı"
        assert abs(test_rate - original_rate) < 0.05, \
            f"Test churn oranı ({test_rate:.3f}) orijinalden ({original_rate:.3f}) çok farklı"
