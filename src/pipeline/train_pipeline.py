# ============================================================================
# train_pipeline.py — Uçtan Uca Eğitim Boru Hattı
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Tüm bileşenleri (Ingestion → Transformation → Training → Evaluation)
#   tek bir run() çağrısıyla zincirler. Tekil bileşenler birbirinden
#   bağımsız çalışabilir ama production'da pipeline olarak çalışır.
#
# VERİ AKIŞI:
#   ┌────────────┐   ┌──────────────────┐   ┌──────────────┐   ┌────────────────┐
#   │ Ingestion  │──▶│ Transformation   │──▶│   Trainer    │──▶│  Evaluation    │
#   │ (NPZ/CSV)  │   │ (Clean+FE+Scale) │   │ (GridSearch) │   │ (Metrik+Rapor) │
#   └────────────┘   └──────────────────┘   └──────────────┘   └────────────────┘
#        ↓ Mod1→numpy     ↓ numpy             ↓ model.pkl       ↓ metrics.json
#        ↓ Mod2→DataFrame ↓ numpy             ↓ best_f1         ↓ confusion_matrix.json
#
# ÇAĞRILIŞ ŞEKLİ:
#   python main.py --train
#   veya: from src.pipeline.train_pipeline import TrainPipeline; TrainPipeline().run()
# ============================================================================

import sys
import time
import numpy as np

from src.exception import CustomException
from src.logger import logging


class TrainPipeline:
    """
    Uçtan uca model eğitim boru hattını yöneten sınıf.

    Neden ayrı bir pipeline sınıfı?
      - Bileşenler (Ingestion, Transformation, Trainer, Evaluation) kendi başlarına
        unit-test edilebilir (loose coupling).
      - Pipeline bunları doğru sırada çağırır ve hata yönetimini merkezileştirir.
      - Her adımın süresini ölçer ve hangi adımda kırıldığını raporlar.

    Kullanım:
        pipeline = TrainPipeline()
        result = pipeline.run()
        print(result["best_f1"])        # → 0.6123
        print(result["best_model"])     # → "XGBClassifier"
        print(result["timings"])        # → {"ingestion": 1.2, "transformation": 3.5, ...}
    """

    def __init__(self):
        # Bileşenleri lazy-import ediyoruz (import döngüsü riskini önler)
        # __init__'te sadece boş state tutuyoruz; run() içinde oluşturulacak
        self.timings: dict = {}

    # ─────────────────────────────────────────────────────────────────────
    # ADIM 1: Veri Alma (Data Ingestion)
    # ─────────────────────────────────────────────────────────────────────

    def _step_ingestion(self) -> tuple:
        """
        DataIngestion bileşenini çalıştırır.

        İki farklı sonuç döner:
          - Mod 1 (NPZ): (X_train, X_test, y_train, y_test) → numpy
          - Mod 2 (CSV): (train_df, test_df) → pandas DataFrame

        Returns:
            tuple: Ingestion sonucu (mod'a göre farklı tiplerde)
        """
        from src.components.data_ingestion import DataIngestion

        logging.info("🔷 ADIM 1/4 — DATA INGESTION")
        t0 = time.time()

        ingestion = DataIngestion()
        result = ingestion.initiate()

        elapsed = round(time.time() - t0, 2)
        self.timings["ingestion"] = elapsed
        logging.info(f"  ⏱ Ingestion süresi: {elapsed}s")

        return result

    # ─────────────────────────────────────────────────────────────────────
    # ADIM 2: Veri Dönüştürme (Data Transformation) — Sadece CSV modunda
    # ─────────────────────────────────────────────────────────────────────

    def _step_transformation(self, train_df, test_df) -> tuple:
        """
        DataTransformation bileşenini çalıştırır.

        SADECE CSV MODUNDA ÇAĞRILIR!
        NPZ modunda notebook zaten tüm dönüşümleri yapmış → bu adım atlanır.

        Args:
            train_df: Eğitim DataFrame'i
            test_df: Test DataFrame'i

        Returns:
            (X_train, X_test, y_train, y_test, preprocessor_path)
        """
        from src.components.data_transformation import DataTransformation

        logging.info("🔷 ADIM 2/4 — DATA TRANSFORMATION")
        t0 = time.time()

        transformation = DataTransformation()
        X_train, X_test, y_train, y_test, pp_path = transformation.initiate(
            train_df, test_df
        )

        elapsed = round(time.time() - t0, 2)
        self.timings["transformation"] = elapsed
        logging.info(f"  ⏱ Transformation süresi: {elapsed}s")
        logging.info(f"  📦 Preprocessor kaydedildi → {pp_path}")

        return X_train, X_test, y_train, y_test

    # ─────────────────────────────────────────────────────────────────────
    # ADIM 3: Model Eğitimi (Model Training)
    # ─────────────────────────────────────────────────────────────────────

    def _step_training(
        self,
        X_train: np.ndarray,
        X_test: np.ndarray,
        y_train: np.ndarray,
        y_test: np.ndarray,
    ) -> tuple:
        """
        ModelTrainer bileşenini çalıştırır.

        4 modeli GridSearchCV ile eğitir, F1 bazında en iyisini seçer ve kaydeder.

        Returns:
            (best_f1, full_report)
        """
        from src.components.model_trainer import ModelTrainer

        logging.info("🔷 ADIM 3/4 — MODEL TRAINING")
        t0 = time.time()

        trainer = ModelTrainer()
        best_f1, report = trainer.initiate(X_train, X_test, y_train, y_test)

        elapsed = round(time.time() - t0, 2)
        self.timings["training"] = elapsed
        logging.info(f"  ⏱ Training süresi: {elapsed}s")

        return best_f1, report

    # ─────────────────────────────────────────────────────────────────────
    # ADIM 4: Model Değerlendirme (Model Evaluation)
    # ─────────────────────────────────────────────────────────────────────

    def _step_evaluation(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        model_name: str,
    ) -> dict:
        """
        ModelEvaluation bileşenini çalıştırır.

        Confusion matrix, ROC-AUC, PR-AUC hesaplar ve JSON olarak kaydeder.

        Returns:
            dict: Detaylı değerlendirme raporu
        """
        from src.components.model_evaluation import ModelEvaluation

        logging.info("🔷 ADIM 4/4 — MODEL EVALUATION")
        t0 = time.time()

        evaluator = ModelEvaluation()
        eval_result = evaluator.initiate(
            model=None,  # artifacts/model.pkl'den otomatik yükler
            X_test=X_test,
            y_test=y_test,
            model_name=model_name,
        )

        elapsed = round(time.time() - t0, 2)
        self.timings["evaluation"] = elapsed
        logging.info(f"  ⏱ Evaluation süresi: {elapsed}s")

        return eval_result

    # ─────────────────────────────────────────────────────────────────────
    # ANA ÇALIŞTIRICI
    # ─────────────────────────────────────────────────────────────────────

    def run(self) -> dict:
        """
        Tüm pipeline'ı sırasıyla çalıştırır.

        AKIŞ:
          1. Ingestion  → Veriyi al (NPZ veya CSV)
          2. Transform  → Sadece CSV modundaysa çalışır
          3. Training   → GridSearchCV ile en iyi modeli bul
          4. Evaluation → Detaylı rapor üret

        Returns:
            dict: {
                "best_model": str,
                "best_f1": float,
                "eval_result": dict,
                "training_report": dict,
                "timings": dict,
                "mode": "npz" | "csv",
                "total_time": float
            }

        Raises:
            CustomException: Herhangi bir adımda hata olursa,
                             hatanın hangi adımda oluştuğu belirtilir.
        """
        pipeline_start = time.time()
        current_step = "başlatma"

        try:
            logging.info("╔" + "═" * 58 + "╗")
            logging.info("║        TRAIN PIPELINE BAŞLATILIYOR                       ║")
            logging.info("╚" + "═" * 58 + "╝")

            # ─── ADIM 1: Ingestion ───
            current_step = "ingestion"
            ingestion_result = self._step_ingestion()

            # ─── MOD TESPİTİ ───
            # Ingestion'ın döndüğü ilk elemanın tipine göre mod belirlenir:
            #   numpy.ndarray → Mod 1 (NPZ): Zaten preprocessed, transformation atlanır
            #   pd.DataFrame  → Mod 2 (CSV): Ham veri, transformation gerekli
            if isinstance(ingestion_result[0], np.ndarray):
                mode = "npz"
                X_train, X_test, y_train, y_test = ingestion_result
                self.timings["transformation"] = 0.0  # NPZ'de atlandı
                logging.info("  📌 Mod 1 (NPZ) tespit edildi → Transformation atlanıyor")
            else:
                mode = "csv"
                train_df, test_df = ingestion_result

                # ─── ADIM 2: Transformation (sadece CSV modunda) ───
                current_step = "transformation"
                X_train, X_test, y_train, y_test = self._step_transformation(
                    train_df, test_df
                )

            # ─── ADIM 3: Training ───
            current_step = "training"
            best_f1, training_report = self._step_training(
                X_train, X_test, y_train, y_test
            )

            best_model_name = training_report.get("best_model", "unknown")

            # ─── ADIM 4: Evaluation ───
            current_step = "evaluation"
            eval_result = self._step_evaluation(
                X_test, y_test, best_model_name
            )

            # ─── SONUÇ ÖZETİ ───
            total_time = round(time.time() - pipeline_start, 2)
            self.timings["total"] = total_time

            logging.info("")
            logging.info("╔" + "═" * 58 + "╗")
            logging.info("║        TRAIN PIPELINE TAMAMLANDI ✅                      ║")
            logging.info("╚" + "═" * 58 + "╝")
            logging.info(f"  Mod            : {mode.upper()}")
            logging.info(f"  En iyi model   : {best_model_name}")
            logging.info(f"  Best F1        : {best_f1:.4f}")
            logging.info(f"  Toplam süre    : {total_time}s")
            logging.info(f"  Adım süreleri  : {self.timings}")

            result = {
                "best_model": best_model_name,
                "best_f1": best_f1,
                "eval_result": eval_result,
                "training_report": training_report,
                "timings": self.timings,
                "mode": mode,
                "total_time": total_time,
            }

            return result

        except Exception as e:
            total_time = round(time.time() - pipeline_start, 2)
            logging.error(
                f"❌ Pipeline '{current_step}' adımında başarısız oldu! ({total_time}s)"
            )
            raise CustomException(e, sys)
