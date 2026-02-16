# ============================================================================
# common.py — Proje Genelinde Kullanılan Yardımcı Fonksiyonlar
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Tekrar eden işlemler (dosya kaydetme/yükleme, config okuma, model
#   değerlendirme) tek bir yerde toplanır. Böylece her component DRY
#   (Don't Repeat Yourself) prensibine uyar.
#
# KULLANIM ÖRNEKLERİ:
#   from src.utils.common import load_yaml, save_object, evaluate_models
#   cfg = load_yaml("configs/config.yaml")
#   save_object("artifacts/model.pkl", trained_model)
# ============================================================================

import os
import sys
import json
import pickle
import yaml
import numpy as np

from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.metrics import (
    f1_score, recall_score, precision_score, 
    roc_auc_score, accuracy_score
)

from src.exception import CustomException
from src.logger import logging


# ─────────────────────────────────────────────────────────────────────────────
# 1) PICKLE İŞLEMLERİ — Model ve Preprocessor Kaydetme / Yükleme
# ─────────────────────────────────────────────────────────────────────────────

def save_object(file_path: str, obj) -> None:
    """
    Python nesnesini (Model, Preprocessor vb.) diske .pkl olarak kaydeder.
    
    NEDEN PICKLE?
      - Eğitilmiş model bellekte bir Python nesnesidir.
      - pickle.dump() bu nesneyi binary formatta diske yazar.
      - Daha sonra pickle.load() ile aynı nesneyi geri yükleyebilirsin.
      - Bu sayede modeli her seferinde yeniden eğitmek gerekmez.
    
    Args:
        file_path: Dosyanın kaydedileceği yol (örn: 'artifacts/model.pkl')
        obj: Kaydedilecek Python nesnesi (eğitilmiş model, pipeline vb.)
    """
    try:
        # Hedef klasör yoksa oluştur (artifacts/ gibi)
        dir_path = os.path.dirname(file_path)
        os.makedirs(dir_path, exist_ok=True)

        # Binary yazma modu (wb) — ML nesneleri metin değil, byte dizisidir
        with open(file_path, "wb") as f:
            pickle.dump(obj, f)

        logging.info(f"Nesne kaydedildi → {file_path}")

    except Exception as e:
        raise CustomException(e, sys)


def load_object(file_path: str):
    """
    Diske kaydedilmiş .pkl nesnesini geri yükler.
    
    NEDEN GEREKLİ?
      - predict_pipeline.py modeli ve preprocessor'ı yüklemek için kullanır.
      - Eğitim 1 kere yapılır, tahmin binlerce kez → her seferinde yükle.
    
    Args:
        file_path: .pkl dosyasının yolu
    
    Returns:
        Kaydedilmiş Python nesnesi (model, preprocessor vb.)
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

        with open(file_path, "rb") as f:
            obj = pickle.load(f)

        logging.info(f"Nesne yüklendi ← {file_path}")
        return obj

    except Exception as e:
        raise CustomException(e, sys)


# ─────────────────────────────────────────────────────────────────────────────
# 2) YAML İŞLEMLERİ — Config Dosyalarını Okuma
# ─────────────────────────────────────────────────────────────────────────────

def load_yaml(file_path: str) -> dict:
    """
    YAML dosyasını okuyup Python dict olarak döndürür.
    
    NEDEN YAML?
      - JSON'dan daha okunabilir (yorum satırı destekler).
      - Config dosyaları için endüstri standardı.
      - config.yaml, model_params.yaml, processing.yaml hepsi bununla okunur.
    
    Args:
        file_path: YAML dosyasının yolu
    
    Returns:
        dict: YAML içeriği Python sözlüğü olarak
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Config dosyası bulunamadı: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        logging.info(f"YAML yüklendi ← {file_path}")
        return data if data is not None else {}

    except Exception as e:
        raise CustomException(e, sys)


# ─────────────────────────────────────────────────────────────────────────────
# 3) JSON İŞLEMLERİ — Metrik ve Metadata Kaydetme / Yükleme
# ─────────────────────────────────────────────────────────────────────────────

def save_json(data: dict, file_path: str) -> None:
    """
    Python dict'ini JSON dosyası olarak kaydeder.
    
    NEDEN JSON?
      - Metrikler (F1, AUC vb.) ve confusion matrix JSON olarak saklanır.
      - JSON hem Python hem JavaScript okuyabilir → Dashboard entegrasyonu.
      - ensure_ascii=False: Türkçe karakterler bozulmasın.
    
    Args:
        data: Kaydedilecek sözlük
        file_path: Hedef dosya yolu
    """
    try:
        dir_path = os.path.dirname(file_path)
        os.makedirs(dir_path, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logging.info(f"JSON kaydedildi → {file_path}")

    except Exception as e:
        raise CustomException(e, sys)


def load_json(file_path: str) -> dict:
    """
    JSON dosyasını okuyup Python dict olarak döndürür.
    
    Args:
        file_path: JSON dosyasının yolu
    
    Returns:
        dict: JSON içeriği
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"JSON dosyası bulunamadı: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logging.info(f"JSON yüklendi ← {file_path}")
        return data

    except Exception as e:
        raise CustomException(e, sys)


# ─────────────────────────────────────────────────────────────────────────────
# 4) NUMPY NPZ İŞLEMLERİ — Notebook Artifact'larını Yükleme
# ─────────────────────────────────────────────────────────────────────────────

def load_npz(file_path: str) -> dict:
    """
    Notebook'un export ettiği .npz dosyasını yükler.
    
    NEDEN NPZ?
      - Notebook Section 11'de X_mat, y, X_pca_95 tek dosyada kaydedildi.
      - np.savez_compressed() ile sıkıştırılmış numpy array'ler saklanır.
      - Bu fonksiyon .npz'yi açıp key-value dict olarak döndürür.
    
    NOTEBOOK ÇIKTISI:
      - X_mat: (7043, N) → Preprocessing sonrası tam feature matrisi
      - y: (7043,) → Hedef değişken (0/1)
      - X_pca_95: (7043, k95) → PCA ile %95 varyans koruyan küçültülmüş matris
    
    Args:
        file_path: .npz dosyasının yolu
    
    Returns:
        dict: {"X_mat": ndarray, "y": ndarray, "X_pca_95": ndarray, ...}
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"NPZ dosyası bulunamadı: {file_path}")

        # np.load ile .npz'yi aç — allow_pickle=False güvenlik için
        npz_data = np.load(file_path, allow_pickle=False)

        # NpzFile nesnesini normal dict'e çevir
        result = {key: npz_data[key] for key in npz_data.files}

        logging.info(
            f"NPZ yüklendi ← {file_path} | "
            f"Key'ler: {list(result.keys())} | "
            f"Şekiller: {[v.shape for v in result.values()]}"
        )
        return result

    except Exception as e:
        raise CustomException(e, sys)


# ─────────────────────────────────────────────────────────────────────────────
# 5) MODEL DEĞERLENDİRME — GridSearchCV ile Toplu Model Karşılaştırma
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_models(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    models: dict,
    params: dict,
    cv: int = 5,
    scoring: str = "f1"
) -> dict:
    """
    Birden fazla modeli GridSearchCV ile eğitip test seti üzerinde değerlendirir.
    
    NEDEN BU FONKSİYON?
      - Model seçimi DS'in en kritik adımlarından biri.
      - Her modeli tek tek eğitmek yerine bu fonksiyon hepsini otomatik dener.
      - GridSearchCV: Verilen parametre grid'indeki tüm kombinasyonları dener.
      - StratifiedKFold: Churn dengesizliğini her fold'da korur.
    
    AKIŞ:
      1. Her model için model_params.yaml'dan parametreleri al
      2. GridSearchCV ile en iyi parametre kombinasyonunu bul
      3. Best model ile test setinde tahmin yap
      4. F1, Recall, Precision, AUC hesapla
    
    Args:
        X_train: Eğitim feature matrisi
        y_train: Eğitim hedef vektörü
        X_test: Test feature matrisi
        y_test: Test hedef vektörü
        models: {"model_adı": model_nesnesi, ...}
        params: {"model_adı": {param_grid}, ...}
        cv: Cross-validation fold sayısı (varsayılan 5)
        scoring: Optimizasyon metriği (varsayılan "f1")
    
    Returns:
        dict: {
            "model_adı": {
                "test_f1": float,
                "test_recall": float, 
                "test_precision": float,
                "test_accuracy": float,
                "test_roc_auc": float,
                "best_params": dict,
                "cv_best_score": float
            }, ...
        }
    """
    try:
        report = {}

        # StratifiedKFold: Her fold'da churn oranını koruyan CV stratejisi
        # NEDEN STRATİFİED?
        #   Normal KFold'da bazı fold'larda churn oranı %5, bazılarında %40 olabilir.
        #   Bu metriği yanıltır. Stratified her fold'da orijinal oranı (~%27) korur.
        skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)

        for model_name, model in models.items():
            logging.info(f"┌─── Model eğitimi başlıyor: {model_name} ───")

            # Bu model için parametre grid'ini al
            # Eğer model_params.yaml'da tanımlı değilse, varsayılan parametrelerle eğit
            param_grid = params.get(model_name, {})

            if param_grid:
                # GridSearchCV: Tüm parametre kombinasyonlarını dener
                # refit=True: En iyi kombinasyonla modeli yeniden eğitir
                # n_jobs=-1: Tüm CPU çekirdeklerini kullan (paralel eğitim)
                gs = GridSearchCV(
                    estimator=model,
                    param_grid=param_grid,
                    cv=skf,
                    scoring=scoring,
                    n_jobs=-1,
                    verbose=0,
                    refit=True
                )
                gs.fit(X_train, y_train)
                best_model = gs.best_estimator_
                best_params = gs.best_params_
                cv_best_score = gs.best_score_

                logging.info(f"│  Best params: {best_params}")
                logging.info(f"│  CV {scoring}: {cv_best_score:.4f}")
            else:
                # Parametre grid'i yoksa direkt fit et
                model.fit(X_train, y_train)
                best_model = model
                best_params = {}
                cv_best_score = None
                logging.info(f"│  Parametre grid'i yok, varsayılan ile eğitildi")

            # Test seti üzerinde tahmin yap
            y_pred = best_model.predict(X_test)

            # Olasılık tahmini (ROC-AUC için gerekli)
            # Bazı modeller predict_proba desteklemeyebilir → try/except
            try:
                y_proba = best_model.predict_proba(X_test)[:, 1]
                roc_auc = roc_auc_score(y_test, y_proba)
            except (AttributeError, IndexError):
                roc_auc = None
                logging.info(f"│  ⚠ {model_name} predict_proba desteklemiyor, AUC hesaplanamadı")

            # Metrikleri hesapla
            test_f1 = f1_score(y_test, y_pred)
            test_recall = recall_score(y_test, y_pred)
            test_precision = precision_score(y_test, y_pred)
            test_accuracy = accuracy_score(y_test, y_pred)

            report[model_name] = {
                "test_f1": round(test_f1, 4),
                "test_recall": round(test_recall, 4),
                "test_precision": round(test_precision, 4),
                "test_accuracy": round(test_accuracy, 4),
                "test_roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
                "best_params": best_params,
                "cv_best_score": round(cv_best_score, 4) if cv_best_score is not None else None,
            }

            auc_str = f"{roc_auc:.4f}" if roc_auc else "N/A"
            logging.info(
                f"│  Test → F1: {test_f1:.4f} | Recall: {test_recall:.4f} | "
                f"Precision: {test_precision:.4f} | AUC: {auc_str}"
            )
            logging.info(f"└─── {model_name} tamamlandı ───")

        return report

    except Exception as e:
        raise CustomException(e, sys)
