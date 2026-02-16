# ============================================================================
# test_common.py — src/utils/common.py için Unit Testler
# ============================================================================
# TEST EDİLEN FONKSİYONLAR:
#   save_object, load_object, save_json, load_json, load_yaml, load_npz
#
# NEDEN BU TESTLER?
#   common.py tüm projenin temel taşı. Eğer save_object bozulursa
#   model eğitimi, eğer load_yaml bozulursa tüm config sistemi çöker.
#   Bu yüzden her fonksiyonu izole olarak test ediyoruz.
#
# ÖNEMLİ PRENSİP: Her test fonksiyonu TEK BİR ŞEYİ test eder.
#   God-test (dev test) yok — her fonksiyonun kendi testi var.
# ============================================================================

import os
import json
import pickle
import pytest
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# save_object / load_object Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveLoadObject:
    """Pickle tabanlı nesne kaydetme/yükleme testleri."""

    def test_save_and_load_dict(self, tmp_path):
        """Basit bir dict nesnesini kaydet ve geri yükle."""
        from src.utils.common import save_object, load_object

        test_obj = {"model": "xgboost", "score": 0.85}
        file_path = str(tmp_path / "test.pkl")

        save_object(file_path, test_obj)
        loaded = load_object(file_path)

        # Yüklenen nesne orijinal ile aynı olmalı
        assert loaded == test_obj

    def test_save_creates_directory(self, tmp_path):
        """Hedef klasör yoksa otomatik oluşturmalı."""
        from src.utils.common import save_object

        # Var olmayan bir alt klasöre kaydet
        file_path = str(tmp_path / "nested" / "deep" / "model.pkl")
        save_object(file_path, [1, 2, 3])

        assert os.path.exists(file_path)

    def test_load_nonexistent_file_raises(self):
        """Var olmayan dosya yüklenirken hata fırlatmalı."""
        from src.utils.common import load_object

        with pytest.raises(Exception):
            load_object("nonexistent/path/model.pkl")

    def test_save_load_numpy_array(self, tmp_path):
        """Numpy array'i pickle ile kaydet/yükle — ML modeli simülasyonu."""
        from src.utils.common import save_object, load_object

        arr = np.array([1.0, 2.0, 3.0])
        file_path = str(tmp_path / "array.pkl")

        save_object(file_path, arr)
        loaded = load_object(file_path)

        np.testing.assert_array_equal(loaded, arr)


# ─────────────────────────────────────────────────────────────────────────────
# save_json / load_json Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveLoadJson:
    """JSON tabanlı metrik kaydetme/yükleme testleri."""

    def test_save_and_load_json(self, tmp_path):
        """Metrik dict'ini JSON olarak kaydet ve geri yükle."""
        from src.utils.common import save_json, load_json

        metrics = {"f1": 0.82, "recall": 0.78, "model": "XGBClassifier"}
        file_path = str(tmp_path / "metrics.json")

        save_json(metrics, file_path)
        loaded = load_json(file_path)

        assert loaded == metrics

    def test_json_turkish_chars(self, tmp_path):
        """Türkçe karakterler bozulmadan kaydedilmeli (ensure_ascii=False)."""
        from src.utils.common import save_json, load_json

        data = {"açıklama": "Model başarıyla eğitildi", "sınıf": "Churn"}
        file_path = str(tmp_path / "turkish.json")

        save_json(data, file_path)
        loaded = load_json(file_path)

        assert loaded["açıklama"] == "Model başarıyla eğitildi"

    def test_load_nonexistent_json_raises(self):
        """Var olmayan JSON dosyası yüklenirken hata fırlatmalı."""
        from src.utils.common import load_json

        with pytest.raises(Exception):
            load_json("nonexistent.json")


# ─────────────────────────────────────────────────────────────────────────────
# load_yaml Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadYaml:
    """YAML config dosyası okuma testleri."""

    def test_load_valid_yaml(self, tmp_path):
        """Geçerli bir YAML dosyasını okuyup dict döndürmeli."""
        from src.utils.common import load_yaml

        yaml_content = "key1: value1\nkey2: 42\nnested:\n  a: 1\n  b: 2\n"
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        result = load_yaml(str(yaml_file))

        assert result["key1"] == "value1"
        assert result["key2"] == 42
        assert result["nested"]["a"] == 1

    def test_load_nonexistent_yaml_raises(self):
        """Var olmayan YAML dosyası yüklenirken hata fırlatmalı."""
        from src.utils.common import load_yaml

        with pytest.raises(Exception):
            load_yaml("nonexistent.yaml")

    def test_config_yaml_exists(self, project_root):
        """Projenin ana config.yaml dosyası mevcut olmalı."""
        config_path = os.path.join(project_root, "configs", "config.yaml")
        assert os.path.exists(config_path), "configs/config.yaml bulunamadı!"


# ─────────────────────────────────────────────────────────────────────────────
# load_npz Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadNpz:
    """Numpy .npz dosyası yükleme testleri."""

    def test_load_npz_returns_correct_keys(self, tmp_path):
        """NPZ dosyasından doğru key'ler dönmeli."""
        from src.utils.common import load_npz

        X = np.random.randn(100, 10)
        y = np.random.randint(0, 2, 100)
        npz_path = str(tmp_path / "data.npz")
        np.savez_compressed(npz_path, X=X, y=y)

        result = load_npz(npz_path)

        assert "X" in result
        assert "y" in result
        assert result["X"].shape == (100, 10)
        assert result["y"].shape == (100,)

    def test_load_npz_data_integrity(self, tmp_path):
        """Kaydedilen ve yüklenen veriler birebir aynı olmalı."""
        from src.utils.common import load_npz

        original = np.array([1.1, 2.2, 3.3, 4.4])
        npz_path = str(tmp_path / "check.npz")
        np.savez_compressed(npz_path, data=original)

        result = load_npz(npz_path)
        np.testing.assert_array_almost_equal(result["data"], original)

    def test_load_nonexistent_npz_raises(self):
        """Var olmayan NPZ dosyası yüklenirken hata fırlatmalı."""
        from src.utils.common import load_npz

        with pytest.raises(Exception):
            load_npz("nonexistent.npz")
