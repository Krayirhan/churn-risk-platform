# ============================================================================
# model_trainer.py — Model Eğitimi ve Seçimi Bileşeni
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Birden fazla ML modelini eğitip karşılaştırır ve en iyisini seçer.
#   model_params.yaml'daki hiperparametre grid'ini okur,
#   GridSearchCV ile optimum parametreleri bulur.
#
# CHURN PROBLEMİNDE MODEL SEÇİMİ:
#   - Accuracy YANILTICI! (%73 "hiç kimse churn etmez" desen bile %73 accuracy)
#   - F1-score: Precision ve Recall'ın harmonik ortalaması → dengeli metrik
#   - Recall: Churn edeni yakalamak iş için daha kritik (kaçırmak = müşteri kaybı)
#   - Bu yüzden model seçiminde F1 temel alınır, Recall da raporlanır.
#
# DESTEKLENEN MODELLER:
#   1. LogisticRegression — Baseline, yorumlanabilir
#   2. RandomForestClassifier — Ensemble, feature importance
#   3. XGBClassifier — Gradient Boosting, genellikle en iyi performans
#   4. GradientBoostingClassifier — sklearn Boosting alternatifi
#
# ÇAĞRILIŞ ŞEKLİ:
#   train_pipeline.py → ModelTrainer().initiate(X_train, X_test, y_train, y_test)
# ============================================================================

import os
import sys
import numpy as np
from dataclasses import dataclass

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier

from src.exception import CustomException
from src.logger import logging
from src.utils.common import load_yaml, save_object, save_json, evaluate_models


# ─────────────────────────────────────────────────────────────────────────────
# KONFİGÜRASYON
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ModelTrainerConfig:
    """
    Model eğitim sürecinin ayarları.
    Hangi modeller denenecek, en iyi model nereye kaydedilecek — hepsi burada.
    """
    _cfg: dict = None

    def __post_init__(self):
        self._cfg = load_yaml("configs/config.yaml")

        artifacts = self._cfg.get("artifacts", {})
        cv_cfg = self._cfg.get("cv", {})

        # En iyi modelin kaydedileceği yol
        self.model_path: str = artifacts.get("model_path", "artifacts/model.pkl")

        # Karşılaştırma metriklerinin kaydedileceği yol
        self.metrics_path: str = artifacts.get("metrics_path", "artifacts/metrics.json")

        # Cross-validation ayarları
        self.n_folds: int = cv_cfg.get("n_folds", 5)
        self.scoring: str = cv_cfg.get("scoring", "f1")

        # En iyi model kabul eşiği
        # F1 < 0.5 ise model işe yaramaz (rastgele tahminden kötü olabilir)
        self.min_acceptable_f1: float = 0.5


# ─────────────────────────────────────────────────────────────────────────────
# ANA SINIF
# ─────────────────────────────────────────────────────────────────────────────

class ModelTrainer:
    """
    Tüm model eğitim, karşılaştırma ve seçim sürecini yöneten sınıf.
    
    Kullanım:
        trainer = ModelTrainer()
        best_f1, report = trainer.initiate(X_train, X_test, y_train, y_test)
    """

    def __init__(self):
        self.config = ModelTrainerConfig()

    def _get_models(self) -> dict:
        """
        Denenecek model nesnelerini döndürür.
        
        NEDEN SÖZLÜK?
          - Her modele ismiyle erişebiliriz.
          - model_params.yaml'daki key'ler bu isimlerle eşleşir.
          - evaluate_models() fonksiyonu bu sözlüğü alıp hepsini dener.
        
        Returns:
            {"model_adı": model_nesnesi, ...}
        """
        models = {
            # --- LOJİSTİK REGRESYON ---
            # En basit ve en hızlı model. Baseline olarak her zaman dahil et.
            # Avantaj: Katsayılar (coefficients) doğrudan yorumlanabilir.
            # class_weight="balanced" → churn sınıfına otomatik ağırlık verir.
            "LogisticRegression": LogisticRegression(
                random_state=42,
                class_weight="balanced"
            ),

            # --- RANDOM FOREST ---
            # Birçok karar ağacının oylaması (bagging ensemble).
            # Avantaj: Overfitting'e dayanıklı, feature_importances_ sağlar.
            # class_weight="balanced" → her ağaçta churn ağırlığı artırılır.
            "RandomForestClassifier": RandomForestClassifier(
                random_state=42,
                class_weight="balanced"
            ),

            # --- XGBOOST ---
            # Gradient Boosting'in optimize edilmiş versiyonu.
            # Genellikle tabular (tablo) verilerinde en iyi performansı verir.
            # scale_pos_weight: churn/no-churn oranı (≈2.77)
            # eval_metric="logloss": Binary cross-entropy kaybı
            # use_label_encoder=False: sklearn uyumluluğu için
            "XGBClassifier": XGBClassifier(
                random_state=42,
                use_label_encoder=False,
                eval_metric="logloss"
            ),

            # --- GRADIENT BOOSTING (sklearn) ---
            # sklearn'ın kendi gradient boosting implementasyonu.
            # XGBoost kadar hızlı değil ama daha stabil olabilir.
            # Not: class_weight doğrudan desteklemez, sample_weight ile halledilir.
            "GradientBoostingClassifier": GradientBoostingClassifier(
                random_state=42
            ),
        }

        return models

    def _get_param_grids(self) -> dict:
        """
        model_params.yaml'dan hiperparametre grid'lerini okur.
        
        NEDEN YAML'DAN?
          - Parametre değiştirmek için Python koduna dokunmak gerekmez.
          - Yeni parametre denemek → sadece YAML düzenle → yeniden çalıştır.
          - Bu, MLOps'un temel prensibi: "config-driven experimentation".
        
        Returns:
            {"model_adı": {"param_name": [value1, value2, ...], ...}, ...}
        """
        try:
            params_cfg = load_yaml("configs/model_params.yaml")
            param_grids = params_cfg.get("models", {})

            logging.info(f"Parametre grid'i yüklendi. Modeller: {list(param_grids.keys())}")
            return param_grids

        except Exception as e:
            logging.warning(f"model_params.yaml okunamadı, varsayılan parametrelerle devam ediliyor: {e}")
            return {}

    def initiate(
        self,
        X_train: np.ndarray,
        X_test: np.ndarray,
        y_train: np.ndarray,
        y_test: np.ndarray
    ) -> tuple:
        """
        Model eğitim ve seçim sürecini başlatır.
        
        AKIŞ:
          1. Model sözlüğünü ve parametre grid'lerini hazırla
          2. evaluate_models() ile tüm modelleri GridSearchCV'de eğit
          3. Test F1-score'a göre en iyi modeli seç
          4. En iyi modeli .pkl olarak kaydet
          5. Tüm metrikleri .json olarak kaydet
        
        Args:
            X_train: Eğitim feature matrisi (numpy array)
            X_test: Test feature matrisi
            y_train: Eğitim hedef vektörü (0/1)
            y_test: Test hedef vektörü
        
        Returns:
            (best_f1_score, full_report_dict)
        
        Raises:
            CustomException: F1 < min_acceptable_f1 ise
        """
        try:
            logging.info("=" * 60)
            logging.info("MODEL TRAINING başlatılıyor...")
            logging.info("=" * 60)

            logging.info(
                f"  Veri boyutları → "
                f"X_train: {X_train.shape} | X_test: {X_test.shape} | "
                f"y_train churn oranı: {y_train.mean():.4f}"
            )

            # ─── ADIM 1: Model ve Parametreleri Hazırla ───
            models = self._get_models()
            param_grids = self._get_param_grids()

            logging.info(f"  {len(models)} model denenecek: {list(models.keys())}")
            logging.info(f"  CV: {self.config.n_folds}-Fold | Scoring: {self.config.scoring}")

            # ─── ADIM 2: Tüm Modelleri Eğit ve Karşılaştır ───
            # evaluate_models() → common.py'deki fonksiyon
            # Her model için GridSearchCV yapar, test metriklerini döndürür
            report = evaluate_models(
                X_train=X_train,
                y_train=y_train,
                X_test=X_test,
                y_test=y_test,
                models=models,
                params=param_grids,
                cv=self.config.n_folds,
                scoring=self.config.scoring
            )

            # ─── ADIM 3: En İyi Modeli Seç ───
            # Tüm modellerin test F1 score'larını topla
            # NEDEN F1?
            #   - Accuracy: %73 "hep No de" bile %73 verir → yanıltıcı
            #   - F1: Precision ve Recall'ın harmonik ortalaması
            #   - Churn'de hem yakalama (recall) hem doğruluk (precision) önemli
            model_scores = {
                name: metrics["test_f1"]
                for name, metrics in report.items()
            }

            # En yüksek F1'e sahip modeli bul
            best_model_name = max(model_scores, key=model_scores.get)
            best_f1 = model_scores[best_model_name]
            best_metrics = report[best_model_name]

            logging.info("")
            logging.info("┌" + "─" * 50 + "┐")
            logging.info(f"│  🏆 EN İYİ MODEL: {best_model_name}")
            logging.info(f"│  F1: {best_f1:.4f} | Recall: {best_metrics['test_recall']:.4f} | "
                        f"Precision: {best_metrics['test_precision']:.4f}")
            logging.info(f"│  AUC: {best_metrics.get('test_roc_auc', 'N/A')}")
            logging.info(f"│  Best params: {best_metrics['best_params']}")
            logging.info("└" + "─" * 50 + "┘")

            # ─── KALİTE KONTROLÜ ───
            # F1 eşiğin altındaysa dur ve uyar
            if best_f1 < self.config.min_acceptable_f1:
                raise CustomException(
                    f"En iyi model F1={best_f1:.4f} < eşik={self.config.min_acceptable_f1}. "
                    f"Model yeterli performansa ulaşamadı. "
                    f"Olası çözümler: daha fazla feature, veri artırma, farklı modeller.",
                    sys
                )

            # ─── ADIM 4: En İyi Modeli Kaydet ───
            # GridSearchCV best_estimator_ zaten refit edilmiş (tüm train verisiyle)
            # Bu modeli doğrudan kaydetmek için modeli yeniden oluşturmamız gerekiyor
            best_model_obj = models[best_model_name]
            best_params = best_metrics["best_params"]

            # En iyi parametrelerle yeniden oluştur ve eğit
            best_model_obj.set_params(**best_params)
            best_model_obj.fit(X_train, y_train)

            save_object(self.config.model_path, best_model_obj)
            logging.info(f"  Model kaydedildi → {self.config.model_path}")

            # ─── ADIM 5: Metrikleri Kaydet ───
            # Tüm modellerin karşılaştırma raporu + en iyi model bilgisi
            full_report = {
                "best_model": best_model_name,
                "best_f1": best_f1,
                "all_models": report
            }
            save_json(full_report, self.config.metrics_path)
            logging.info(f"  Metrikler kaydedildi → {self.config.metrics_path}")

            logging.info("MODEL TRAINING tamamlandı.")
            logging.info("=" * 60)

            return best_f1, full_report

        except Exception as e:
            raise CustomException(e, sys)


# ─────────────────────────────────────────────────────────────────────────────
# YARDIMCI: Model Karşılaştırma Tablosu Yazdırma
# ─────────────────────────────────────────────────────────────────────────────

def print_model_comparison(report: dict) -> None:
    """
    Tüm modellerin metriklerini tablo formatında ekrana yazdırır.
    
    Kullanım:
        _, report = trainer.initiate(...)
        print_model_comparison(report)
    """
    print("\n" + "=" * 80)
    print("📊 MODEL KARŞILAŞTIRMA RAPORU")
    print("=" * 80)
    print(f"{'Model':<30} {'F1':>8} {'Recall':>8} {'Precision':>10} {'AUC':>8} {'Accuracy':>10}")
    print("-" * 80)

    all_models = report.get("all_models", report)
    for name, metrics in all_models.items():
        marker = " 🏆" if name == report.get("best_model", "") else ""
        print(
            f"{name:<30} "
            f"{metrics['test_f1']:>8.4f} "
            f"{metrics['test_recall']:>8.4f} "
            f"{metrics['test_precision']:>10.4f} "
            f"{str(metrics.get('test_roc_auc', 'N/A')):>8} "
            f"{metrics['test_accuracy']:>10.4f}"
            f"{marker}"
        )

    print("=" * 80)
    print(f"🏆 Seçilen model: {report.get('best_model', 'N/A')} (F1: {report.get('best_f1', 'N/A')})")
    print()

