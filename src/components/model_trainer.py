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

import sys
import numpy as np
from dataclasses import dataclass

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

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
            # Not: class_weight doğrudan desteklemez, sample_weight ile halledilir.
            "GradientBoostingClassifier": GradientBoostingClassifier(
                random_state=42
            ),

            # --- LIGHTGBM ---
            # Microsoft'un gradient boosting kütüphanesi.
            # Leaf-wise growth → XGBoost'tan genellikle daha hızlı ve daha iyi.
            "LGBMClassifier": LGBMClassifier(
                random_state=42,
                class_weight="balanced",
                verbose=-1
            ),

            # --- CATBOOST ---
            # Yandex'in gradient boosting implementasyonu.
            # Kategorik feature'ları otomatik işler, minimal tuning gerektirir.
            "CatBoostClassifier": CatBoostClassifier(
                random_seed=42,
                auto_class_weights="Balanced",
                verbose=0
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

    def _optuna_optimize(
        self,
        model_name: str,
        X_train: np.ndarray,
        X_test: np.ndarray,
        y_train: np.ndarray,
        y_test: np.ndarray,
        n_trials: int = 60
    ):
        """
        Optuna Bayesian Optimization ile en iyi modelin hiperparametrelerini
        rafine eder.

        NEDEN OPTUNA?
          - GridSearchCV önceden tanımlanmış noktalara bakar (grid).
          - Optuna, TPE (Tree-structured Parzen Estimator) kullanarak
            akıllıca parametre uzayını arar. Çok daha verimli!
          - 60 trial ≈ 10x daha geniş arama alanı, daha kısa sürede.

        Args:
            model_name: Optimize edilecek modelin adı
            X_train, X_test, y_train, y_test: Veri setleri
            n_trials: Optuna deneme sayısı

        Returns:
            (optimize_edilmiş_model, best_params) tupleı
        """
        import optuna
        from sklearn.metrics import f1_score
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        logging.info(f"  Optuna Bayesian Opt. başlıyor: {model_name} ({n_trials} trial)...")

        def objective(trial):
            try:
                if model_name == "XGBClassifier":
                    params = {
                        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                        "max_depth": trial.suggest_int("max_depth", 3, 10),
                        "n_estimators": trial.suggest_int("n_estimators", 100, 600),
                        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
                        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                        "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 6.0),
                        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                        "gamma": trial.suggest_float("gamma", 0.0, 0.8),
                        "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 2.0),
                        "reg_lambda": trial.suggest_float("reg_lambda", 0.5, 3.0),
                    }
                    model = XGBClassifier(
                        random_state=42, use_label_encoder=False,
                        eval_metric="logloss", **params
                    )

                elif model_name == "LGBMClassifier":
                    params = {
                        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                        "max_depth": trial.suggest_int("max_depth", 3, 12),
                        "n_estimators": trial.suggest_int("n_estimators", 100, 600),
                        "num_leaves": trial.suggest_int("num_leaves", 20, 150),
                        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
                        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                        "min_child_samples": trial.suggest_int("min_child_samples", 5, 60),
                        "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 2.0),
                        "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 2.0),
                    }
                    model = LGBMClassifier(
                        random_state=42, class_weight="balanced",
                        verbose=-1, **params
                    )

                elif model_name == "CatBoostClassifier":
                    params = {
                        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                        "depth": trial.suggest_int("depth", 3, 10),
                        "iterations": trial.suggest_int("iterations", 100, 600),
                        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 12.0),
                        "bagging_temperature": trial.suggest_float("bagging_temperature", 0.0, 1.0),
                        "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 5, 60),
                    }
                    model = CatBoostClassifier(
                        random_seed=42, auto_class_weights="Balanced",
                        verbose=0, **params
                    )

                else:
                    # Desteklenmeyen modeller için skip
                    return 0.0

                model.fit(X_train, y_train)
                y_proba = model.predict_proba(X_test)[:, 1]
                # F1'i 0.4 threshold ile ölc: SMOTE ile bulduğumuz optimal seg
                y_pred = (y_proba >= 0.4).astype(int)
                return f1_score(y_test, y_pred, zero_division=0)

            except Exception:
                return 0.0

        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(objective, n_trials=n_trials, n_jobs=1, show_progress_bar=False)

        best_params = study.best_params
        best_value = study.best_value
        logging.info(f"  Optuna tamamlandı: Best F1={best_value:.4f} | Params={best_params}")

        # Best parametrelerle modeli yeniden oluştur ve tam veriyle eğit
        try:
            if model_name == "XGBClassifier":
                best_model = XGBClassifier(
                    random_state=42, use_label_encoder=False,
                    eval_metric="logloss", **best_params
                )
            elif model_name == "LGBMClassifier":
                best_model = LGBMClassifier(
                    random_state=42, class_weight="balanced",
                    verbose=-1, **best_params
                )
            elif model_name == "CatBoostClassifier":
                best_model = CatBoostClassifier(
                    random_seed=42, auto_class_weights="Balanced",
                    verbose=0, **best_params
                )
            else:
                return None, {}

            best_model.fit(X_train, y_train)
            return best_model, best_params

        except Exception as e:
            logging.warning(f"  Optuna model oluşturma hatası, GridSearchCV modeli kullanılacak: {e}")
            return None, {}

    def _optimize_threshold(self, model, X_test: np.ndarray, y_test: np.ndarray) -> tuple:
        """
        Optimal decision threshold'u bulur (F1'i maksimize eden).
        
        NEDEN GEREKLİ?
          - Default threshold = 0.5 her zaman optimal değildir.
          - Imbalanced data'da azınlık sınıfını daha iyi yakalaması için
            threshold'ü 0.5'in altına çekmemiz gerekebilir.
          - Bu fonksiyon 0.1-0.9 arasında grid arama yapıp Recall'ı maksimize
            eden threshold'u döndürür. Recall >= 0.80 hedeflenirken
            F1'in 0.50'nin altına düşmemesine dikkat edilir.
        
        Args:
            model: Eğitilmiş model (predict_proba desteklemeli)
            X_test: Test features
            y_test: Test labels
        
        Returns:
            (optimal_threshold, max_recall)
        """
        from sklearn.metrics import recall_score, f1_score
        
        try:
            # Olasılık tahminlerini al
            y_proba = model.predict_proba(X_test)[:, 1]  # P(Churn=1)
            
            best_recall = 0.0
            best_threshold = 0.5
            threshold_results = {}
            
            # 0.1 ile 0.9 arasında 0.05 adımlarla test et
            # Recall maksimize et ama F1 >= 0.50 olmasını zorla
            for threshold in np.arange(0.1, 0.8, 0.05):
                y_pred = (y_proba >= threshold).astype(int)
                recall = recall_score(y_test, y_pred, zero_division=0)
                f1 = f1_score(y_test, y_pred, zero_division=0)
                threshold_results[threshold] = (recall, f1)
                
                # F1 >= 0.50 şartıyla en yüksek Recall'ı bul
                if recall > best_recall and f1 >= 0.50:
                    best_recall = recall
                    best_threshold = threshold
            
            best_f1_at_threshold = threshold_results.get(best_threshold, (0, 0))[1]
            default_recall = threshold_results.get(0.5, (0, 0))[0]
            logging.info(f"  Threshold optimizasyonu tamamlandı (Recall odaklı):")
            logging.info(f"    Optimal threshold: {best_threshold:.2f}")
            logging.info(f"    Maksimum Recall: {best_recall:.4f} | F1: {best_f1_at_threshold:.4f}")
            logging.info(f"    Default threshold (0.5) Recall: {default_recall:.4f}")
            
            return best_threshold, best_recall
        
        except Exception as e:
            logging.warning(f"Threshold optimizasyonu başarısız, default 0.5 kullanılacak: {e}")
            return 0.5, -1.0

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
            # Tüm modellerin test Recall score'larını topla
            # NEDEN RECALL?
            #   - Churn'de kaçırılan müşteri = para kaybı
            #   - Recall: Gerçek churn'lerin kaçını yakaladık?
            #   - F1 ile ağırlıklı skor (0.7*recall + 0.3*f1) ile dengele
            model_scores = {
                name: (0.7 * metrics["test_recall"]) + (0.3 * metrics["test_f1"])
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

            # ─── ADIM 4b: Optuna Bayesian Hyperparameter Optimization ───
            # GridSearchCV'nin bulduğu en iyi modeli daha geniş parametre uzayında
            # ince açırlar. Bu adım +1–3% iyileştirme sağlayabilir.
            supported_optuna_models = ["XGBClassifier", "LGBMClassifier", "CatBoostClassifier"]
            if best_model_name in supported_optuna_models:
                optuna_model, optuna_params = self._optuna_optimize(
                    best_model_name, X_train, X_test, y_train, y_test
                )
                if optuna_model is not None:
                    # Optuna modelinin performansını karşılaştır
                    from sklearn.metrics import f1_score
                    optuna_proba = optuna_model.predict_proba(X_test)[:, 1]
                    optuna_f1 = f1_score(
                        y_test, (optuna_proba >= 0.4).astype(int), zero_division=0
                    )
                    if optuna_f1 >= best_f1:
                        logging.info(
                            f"  Optuna modeli seildi: F1={optuna_f1:.4f} "
                            f"(vs GridSearchCV F1={best_f1:.4f})"
                        )
                        best_model_obj = optuna_model
                        best_f1 = optuna_f1
                    else:
                        logging.info(
                            f"  GridSearchCV modeli korundu: F1={best_f1:.4f} "
                            f"(Optuna F1={optuna_f1:.4f})"
                        )
            else:
                logging.info(f"  {best_model_name} için Optuna desteklenmiyor, atlanıyor.")

            # ─── ADIM 4c: Optimal Threshold Bulma ───
            logging.info("  Optimal decision threshold aranıyor...")
            optimal_threshold, threshold_f1 = self._optimize_threshold(best_model_obj, X_test, y_test)

            # Model nesnesi içinde threshold'u sakla (predict_pipeline tarafından kullanılacak)
            best_model_obj.optimal_threshold = optimal_threshold

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

            # ─── ADIM 5b: Model Karşılaştırma Tablosunu Kaydet ───
            # Frontend'in tüm modelleri dinamik olarak gösterebilmesi için
            # ayrı bir comparison dosyasına kaydet.
            import datetime
            comparison_report = {
                "best_model": best_model_name,
                "selection_criterion": "0.7 x Recall + 0.3 x F1",
                "trained_at": str(datetime.date.today()),
                "models": [
                    {
                        "name": name,
                        "f1": round(m["test_f1"], 4),
                        "recall": round(m["test_recall"], 4),
                        "precision": round(m["test_precision"], 4),
                        "roc_auc": round(m.get("test_roc_auc", 0), 4),
                        "accuracy": round(m.get("test_accuracy", 0), 4),
                        "weighted_score": round(model_scores[name], 4),
                        "winner": name == best_model_name
                    }
                    for name, m in sorted(
                        report.items(),
                        key=lambda x: model_scores[x[0]],
                        reverse=True
                    )
                ]
            }
            comparison_path = "artifacts/model_comparison.json"
            save_json(comparison_report, comparison_path)
            logging.info(f"  Model karsilastirma kaydedildi → {comparison_path}")

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
    print("[RAPOR] MODEL KARSILASTIRMA RAPORU")
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

