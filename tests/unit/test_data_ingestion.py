# ============================================================================
# test_data_ingestion.py — DataIngestion Sınıfı için Unit Testler
# ============================================================================
# TEST EDİLEN SINIF: src/components/data_ingestion.py → DataIngestion
#
# TEST STRATEJİSİ:
#   - NPZ modu (Mod 1): Sentetik .npz dosyası oluşturup yükleme test edilir
#   - CSV modu (Mod 2): Sentetik CSV ile okuma ve split test edilir
#   - Config doğrulama: DataIngestionConfig'in config.yaml'ı doğru okuduğu test edilir
#   - Hata durumları: Dosya yokken doğru hata fırlatıldığı test edilir
#
# ÖNEMLİ: Gerçek veriye (churn.csv) bağımlı değil — sentetik veri kullanılır.
# ============================================================================

import os
import pytest
import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Config Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestDataIngestionConfig:
    """DataIngestionConfig'in config.yaml'ı doğru okuyup okumadığını test eder."""

    def test_config_loads_without_error(self):
        """Config nesnesi hatasız oluşturulabilmeli."""
        from src.components.data_ingestion import DataIngestionConfig
        config = DataIngestionConfig()
        assert config is not None

    def test_config_has_required_fields(self):
        """Config'de gerekli alanlar mevcut olmalı."""
        from src.components.data_ingestion import DataIngestionConfig
        config = DataIngestionConfig()

        # Tüm zorunlu alanlar tanımlı olmalı
        assert hasattr(config, "npz_path")
        assert hasattr(config, "raw_data_path")
        assert hasattr(config, "test_size")
        assert hasattr(config, "random_state")
        assert hasattr(config, "target_col")

    def test_config_test_size_valid_range(self):
        """test_size 0 ile 1 arasında olmalı."""
        from src.components.data_ingestion import DataIngestionConfig
        config = DataIngestionConfig()
        assert 0.0 < config.test_size < 1.0, f"test_size={config.test_size} geçersiz!"


# ─────────────────────────────────────────────────────────────────────────────
# NPZ Modu (Mod 1) Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestNpzMode:
    """Notebook artifact'ından (.npz) veri yükleme testleri."""

    def test_npz_loading_returns_four_arrays(self, tmp_path):
        """NPZ modunda 4 numpy array dönmeli: X_train, X_test, y_train, y_test."""
        from src.components.data_ingestion import DataIngestion

        # Sentetik .npz oluştur
        n, f = 200, 20
        X = np.random.randn(n, f)
        y = np.random.choice([0, 1], n, p=[0.73, 0.27])
        npz_path = str(tmp_path / "telco_prepared_dataset.npz")
        np.savez_compressed(npz_path, X=X, y=y)

        # DataIngestion'ın config'ini override et
        ingestion = DataIngestion()
        ingestion.config.npz_path = npz_path

        result = ingestion._load_from_notebook_npz()

        assert len(result) == 4, "NPZ modu 4 eleman döndürmeli"
        X_train, X_test, y_train, y_test = result
        assert isinstance(X_train, np.ndarray)
        assert isinstance(y_test, np.ndarray)

    def test_npz_split_preserves_total_count(self, tmp_path):
        """Train + Test toplam satır sayısı orijinal ile aynı olmalı."""
        from src.components.data_ingestion import DataIngestion

        n = 200
        X = np.random.randn(n, 10)
        y = np.random.choice([0, 1], n)
        npz_path = str(tmp_path / "telco_prepared_dataset.npz")
        np.savez_compressed(npz_path, X=X, y=y)

        ingestion = DataIngestion()
        ingestion.config.npz_path = npz_path
        X_train, X_test, y_train, y_test = ingestion._load_from_notebook_npz()

        total = len(y_train) + len(y_test)
        assert total == n, f"Toplam {total} ≠ orijinal {n}"

    def test_npz_missing_key_raises(self, tmp_path):
        """NPZ'de 'y' key'i yoksa KeyError fırlatmalı."""
        from src.components.data_ingestion import DataIngestion

        # Sadece X kaydet, y yok
        X = np.random.randn(50, 5)
        npz_path = str(tmp_path / "bad.npz")
        np.savez_compressed(npz_path, X=X)

        ingestion = DataIngestion()
        ingestion.config.npz_path = npz_path

        with pytest.raises(Exception):
            ingestion._load_from_notebook_npz()


# ─────────────────────────────────────────────────────────────────────────────
# CSV Modu (Mod 2) Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestCsvMode:
    """Ham CSV'den veri okuma testleri."""

    def test_csv_loading_returns_two_dataframes(self, tmp_path, sample_raw_dataframe):
        """CSV modunda 2 DataFrame dönmeli: train_df, test_df."""
        from src.components.data_ingestion import DataIngestion

        # Sentetik CSV kaydet
        csv_path = str(tmp_path / "churn.csv")
        sample_raw_dataframe.to_csv(csv_path, index=False)

        ingestion = DataIngestion()
        ingestion.config.raw_data_path = csv_path

        train_df, test_df = ingestion._load_from_raw_csv()

        assert isinstance(train_df, pd.DataFrame)
        assert isinstance(test_df, pd.DataFrame)

    def test_csv_target_converted_to_binary(self, tmp_path, sample_raw_dataframe):
        """Churn sütunu Yes/No'dan 0/1'e dönüştürülmeli."""
        from src.components.data_ingestion import DataIngestion

        csv_path = str(tmp_path / "churn.csv")
        sample_raw_dataframe.to_csv(csv_path, index=False)

        ingestion = DataIngestion()
        ingestion.config.raw_data_path = csv_path

        train_df, test_df = ingestion._load_from_raw_csv()

        # Hedef sütun sadece 0 ve 1 içermeli
        all_values = set(train_df["Churn"].unique()) | set(test_df["Churn"].unique())
        assert all_values.issubset({0, 1}), f"Churn sütununda beklenmeyen değerler: {all_values}"

    def test_csv_missing_file_raises(self):
        """Var olmayan CSV dosyası için hata fırlatmalı."""
        from src.components.data_ingestion import DataIngestion

        ingestion = DataIngestion()
        ingestion.config.raw_data_path = "nonexistent/churn.csv"
        ingestion.config.npz_path = "nonexistent/data.npz"  # NPZ de yok

        with pytest.raises(Exception):
            ingestion._load_from_raw_csv()
