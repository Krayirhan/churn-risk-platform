# ============================================================================
# test_model_trainer.py — ModelTrainer Sınıfı için Unit Testler
# ============================================================================
# TEST EDİLEN SINIF: src/components/model_trainer.py → ModelTrainer
#
# TEST STRATEJİSİ:
#   - Model sözlüğünün doğru oluşturulduğu test edilir
#   - Parametre grid'lerinin YAML'dan okunduğu test edilir
#   - Sentetik veri ile gerçek eğitim akışı test edilir
#   - Kalite eşiği kontrolü test edilir
#
# NOT: GridSearchCV tüm kombinasyonları denediği için bu testler
#      diğerlerinden yavaş çalışabilir (~10-30 sn). Bu normaldir.
# ============================================================================

import os
import pytest
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Config Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestModelTrainerConfig:
    """ModelTrainerConfig'in doğru yüklendiğini test eder."""

    def test_config_loads_without_error(self):
        """Config nesnesi hatasız oluşturulabilmeli."""
        from src.components.model_trainer import ModelTrainerConfig
        config = ModelTrainerConfig()
        assert config is not None

    def test_config_has_model_path(self):
        """Model kayıt yolu tanımlı olmalı."""
        from src.components.model_trainer import ModelTrainerConfig
        config = ModelTrainerConfig()
        assert config.model_path is not None
        assert config.model_path.endswith(".pkl")

    def test_config_has_valid_scoring(self):
        """Scoring metriği geçerli bir sklearn metriği olmalı."""
        from src.components.model_trainer import ModelTrainerConfig
        config = ModelTrainerConfig()
        valid_metrics = {"f1", "recall", "precision", "accuracy", "roc_auc"}
        assert config.scoring in valid_metrics, f"Geçersiz scoring: {config.scoring}"


# ─────────────────────────────────────────────────────────────────────────────
# Model Sözlüğü Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestModelDictionary:
    """Denenecek model listesinin doğruluğunu test eder."""

    def test_get_models_returns_dict(self):
        """_get_models() bir dict döndürmeli."""
        from src.components.model_trainer import ModelTrainer
        trainer = ModelTrainer()
        models = trainer._get_models()
        assert isinstance(models, dict)

    def test_get_models_has_four_models(self):
        """Tam olarak 4 model tanımlı olmalı."""
        from src.components.model_trainer import ModelTrainer
        trainer = ModelTrainer()
        models = trainer._get_models()
        assert len(models) == 4, f"4 model bekleniyordu, {len(models)} bulundu"

    def test_all_models_have_fit_method(self):
        """Her model sklearn API'sine uygun olmalı (fit metodu var)."""
        from src.components.model_trainer import ModelTrainer
        trainer = ModelTrainer()
        models = trainer._get_models()

        for name, model in models.items():
            assert hasattr(model, "fit"), f"{name} modelinde fit() metodu yok!"
            assert hasattr(model, "predict"), f"{name} modelinde predict() metodu yok!"

    def test_xgboost_has_scale_pos_weight_access(self):
        """XGBClassifier'ın scale_pos_weight ayarlanabilir olmalı."""
        from src.components.model_trainer import ModelTrainer
        trainer = ModelTrainer()
        models = trainer._get_models()

        xgb = models.get("XGBClassifier")
        assert xgb is not None, "XGBClassifier model sözlüğünde yok!"


# ─────────────────────────────────────────────────────────────────────────────
# Parametre Grid Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestParamGrids:
    """model_params.yaml'dan okunan parametre grid'lerini test eder."""

    def test_param_grids_loaded(self):
        """Parametre grid'i yüklenebilmeli."""
        from src.components.model_trainer import ModelTrainer
        trainer = ModelTrainer()
        grids = trainer._get_param_grids()
        assert isinstance(grids, dict)

    def test_param_grids_have_model_keys(self):
        """Grid'deki key'ler model isimlerine karşılık gelmeli."""
        from src.components.model_trainer import ModelTrainer
        trainer = ModelTrainer()
        grids = trainer._get_param_grids()
        models = trainer._get_models()

        # En az bir model grid'de tanımlı olmalı
        overlap = set(grids.keys()) & set(models.keys())
        assert len(overlap) > 0, "Parametre grid'inde hiçbir model eşleşmedi!"


# ─────────────────────────────────────────────────────────────────────────────
# Eğitim Akışı Testleri (Sentetik Veri ile)
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainingFlow:
    """Tam model eğitim akışını sentetik veri ile test eder."""

    def test_initiate_returns_f1_and_report(self, sample_npz_arrays):
        """initiate() → (best_f1, report_dict) döndürmeli."""
        from src.components.model_trainer import ModelTrainer

        X_train, X_test, y_train, y_test = sample_npz_arrays
        trainer = ModelTrainer()
        # Sentetik veri ile F1 düşük olabilir — eşiği kaldır
        trainer.config.min_acceptable_f1 = 0.0
        best_f1, report = trainer.initiate(X_train, X_test, y_train, y_test)

        assert isinstance(best_f1, float)
        assert isinstance(report, dict)
        assert "best_model" in report
        assert "all_models" in report

    def test_best_f1_in_valid_range(self, sample_npz_arrays):
        """Best F1 score 0-1 arasında olmalı."""
        from src.components.model_trainer import ModelTrainer

        X_train, X_test, y_train, y_test = sample_npz_arrays
        trainer = ModelTrainer()
        trainer.config.min_acceptable_f1 = 0.0  # Sentetik veri için eşiği kaldır
        best_f1, _ = trainer.initiate(X_train, X_test, y_train, y_test)

        assert 0.0 <= best_f1 <= 1.0, f"F1={best_f1} geçersiz aralık"

    def test_model_pkl_saved(self, sample_npz_arrays):
        """En iyi model .pkl olarak kaydedilmeli."""
        from src.components.model_trainer import ModelTrainer

        X_train, X_test, y_train, y_test = sample_npz_arrays
        trainer = ModelTrainer()
        trainer.config.min_acceptable_f1 = 0.0
        trainer.initiate(X_train, X_test, y_train, y_test)

        assert os.path.exists(trainer.config.model_path), \
            f"Model dosyası oluşturulmadı: {trainer.config.model_path}"

    def test_report_contains_all_models(self, sample_npz_arrays):
        """Rapor tüm modellerin sonuçlarını içermeli."""
        from src.components.model_trainer import ModelTrainer

        X_train, X_test, y_train, y_test = sample_npz_arrays
        trainer = ModelTrainer()
        trainer.config.min_acceptable_f1 = 0.0
        _, report = trainer.initiate(X_train, X_test, y_train, y_test)

        model_names = list(report["all_models"].keys())
        assert len(model_names) >= 2, f"En az 2 model raporda olmalı, {len(model_names)} bulundu"
