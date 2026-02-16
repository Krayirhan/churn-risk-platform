# ============================================================================
# test_model_evaluation.py — ModelEvaluation Sınıfı için Unit Testler
# ============================================================================
# TEST EDİLEN SINIF: src/components/model_evaluation.py → ModelEvaluation
#
# TEST STRATEJİSİ:
#   - Metrik hesaplama doğruluğu (bilinen girdiler → bilinen çıktılar)
#   - Confusion matrix hesaplaması
#   - JSON kayıt çıktıları
#   - Hata durumları
#
# NOT: Bu testler basit sklearn modelleri ile yapılır (LogReg).
#      Amacımız evaluation kodunu test etmek, model performansını DEĞİL.
# ============================================================================

import os
import pytest
import numpy as np
from sklearn.linear_model import LogisticRegression


# ─────────────────────────────────────────────────────────────────────────────
# Metrik Hesaplama Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestMetricComputation:
    """Metrik hesaplama fonksiyonlarının doğruluğunu test eder."""

    def _get_evaluator(self):
        """ModelEvaluation nesnesi oluşturur."""
        from src.components.model_evaluation import ModelEvaluation
        return ModelEvaluation()

    def test_compute_metrics_returns_dict(self):
        """_compute_metrics() dict döndürmeli."""
        evaluator = self._get_evaluator()

        y_true = np.array([0, 0, 1, 1, 0, 1])
        y_pred = np.array([0, 0, 1, 0, 0, 1])

        metrics = evaluator._compute_metrics(y_true, y_pred)
        assert isinstance(metrics, dict)

    def test_metrics_has_required_keys(self):
        """Metrik dict'inde accuracy, f1, recall, precision olmalı."""
        evaluator = self._get_evaluator()

        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 0])

        metrics = evaluator._compute_metrics(y_true, y_pred)

        required_keys = {"accuracy", "f1", "recall", "precision"}
        missing = required_keys - set(metrics.keys())
        assert len(missing) == 0, f"Eksik metrikler: {missing}"

    def test_perfect_prediction_gives_f1_one(self):
        """Mükemmel tahmin → F1 = 1.0 olmalı."""
        evaluator = self._get_evaluator()

        y = np.array([0, 1, 0, 1, 1, 0])
        metrics = evaluator._compute_metrics(y, y)  # tahmin = gerçek

        assert metrics["f1"] == 1.0, f"Mükemmel tahmin F1={metrics['f1']}, 1.0 olmalıydı"

    def test_metrics_with_proba_includes_auc(self):
        """Olasılık verildiğinde ROC-AUC ve PR-AUC eklenmeli."""
        evaluator = self._get_evaluator()

        y_true = np.array([0, 0, 1, 1, 0, 1])
        y_pred = np.array([0, 0, 1, 0, 0, 1])
        y_proba = np.array([0.1, 0.2, 0.9, 0.4, 0.15, 0.85])

        metrics = evaluator._compute_metrics(y_true, y_pred, y_proba)

        assert "roc_auc" in metrics, "ROC-AUC hesaplanmadı"
        assert "pr_auc" in metrics, "PR-AUC hesaplanmadı"
        assert 0.0 <= metrics["roc_auc"] <= 1.0
        assert 0.0 <= metrics["pr_auc"] <= 1.0

    def test_all_metrics_in_valid_range(self):
        """Tüm metrikler 0-1 arasında olmalı."""
        evaluator = self._get_evaluator()

        y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0])
        y_pred = np.array([0, 0, 0, 1, 1, 1, 1, 0])

        metrics = evaluator._compute_metrics(y_true, y_pred)

        for key in ["accuracy", "f1", "recall", "precision"]:
            assert 0.0 <= metrics[key] <= 1.0, f"{key}={metrics[key]} geçersiz aralık"


# ─────────────────────────────────────────────────────────────────────────────
# Confusion Matrix Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestConfusionMatrix:
    """Confusion matrix hesaplamasının doğruluğunu test eder."""

    def _get_evaluator(self):
        from src.components.model_evaluation import ModelEvaluation
        return ModelEvaluation()

    def test_cm_has_required_keys(self):
        """CM dict'inde TP, FP, TN, FN olmalı."""
        evaluator = self._get_evaluator()

        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 1, 1, 0])

        cm = evaluator._compute_confusion_matrix(y_true, y_pred)

        for key in ["true_negative", "false_positive", "false_negative", "true_positive"]:
            assert key in cm, f"CM'de '{key}' eksik"

    def test_cm_values_correct(self):
        """Bilinen girdiler için doğru CM değerleri dönmeli."""
        evaluator = self._get_evaluator()

        # Gerçek: [0, 0, 1, 1] | Tahmin: [0, 1, 1, 0]
        # TN=1 (0→0), FP=1 (0→1), TP=1 (1→1), FN=1 (1→0)
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 1, 1, 0])

        cm = evaluator._compute_confusion_matrix(y_true, y_pred)

        assert cm["true_negative"] == 1
        assert cm["false_positive"] == 1
        assert cm["true_positive"] == 1
        assert cm["false_negative"] == 1

    def test_cm_sum_equals_total(self):
        """TP + FP + TN + FN = toplam örnek sayısı olmalı."""
        evaluator = self._get_evaluator()

        n = 50
        y_true = np.random.choice([0, 1], n)
        y_pred = np.random.choice([0, 1], n)

        cm = evaluator._compute_confusion_matrix(y_true, y_pred)

        total = cm["true_negative"] + cm["false_positive"] + \
                cm["false_negative"] + cm["true_positive"]
        assert total == n, f"CM toplamı {total} ≠ {n}"


# ─────────────────────────────────────────────────────────────────────────────
# Tam Evaluation Akışı Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluationFlow:
    """Tam initiate() akışını basit bir model ile test eder."""

    def _train_simple_model(self, sample_npz_arrays):
        """Test için basit bir LogReg modeli eğitir."""
        X_train, X_test, y_train, y_test = sample_npz_arrays
        model = LogisticRegression(random_state=42, max_iter=500)
        model.fit(X_train, y_train)
        return model, X_test, y_test

    def test_initiate_returns_dict(self, sample_npz_arrays):
        """initiate() dict döndürmeli."""
        from src.components.model_evaluation import ModelEvaluation

        model, X_test, y_test = self._train_simple_model(sample_npz_arrays)
        evaluator = ModelEvaluation()
        result = evaluator.initiate(model=model, X_test=X_test, y_test=y_test)

        assert isinstance(result, dict)

    def test_initiate_result_has_metrics(self, sample_npz_arrays):
        """Sonuç dict'inde 'metrics' anahtarı olmalı."""
        from src.components.model_evaluation import ModelEvaluation

        model, X_test, y_test = self._train_simple_model(sample_npz_arrays)
        evaluator = ModelEvaluation()
        result = evaluator.initiate(model=model, X_test=X_test, y_test=y_test)

        assert "metrics" in result
        assert "confusion_matrix" in result

    def test_initiate_saves_json_files(self, sample_npz_arrays):
        """Metrik ve CM JSON dosyaları oluşturulmuş olmalı."""
        from src.components.model_evaluation import ModelEvaluation

        model, X_test, y_test = self._train_simple_model(sample_npz_arrays)
        evaluator = ModelEvaluation()
        evaluator.initiate(model=model, X_test=X_test, y_test=y_test)

        assert os.path.exists(evaluator.config.metrics_path), \
            "metrics.json oluşturulmadı"
        assert os.path.exists(evaluator.config.confusion_matrix_path), \
            "confusion_matrix.json oluşturulmadı"
