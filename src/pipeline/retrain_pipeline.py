# ============================================================================
# retrain_pipeline.py — Otomatik Yeniden Eğitim Pipeline'ı
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Drift algılandığında veya performans düştüğünde modeli otomatik
#   olarak yeniden eğitir. İş akışı:
#     1. Monitoring kontrolü → retrain gerekli mi?
#     2. Cooldown kontrolü → çok sık eğitim engellenir
#     3. TrainPipeline.run() → yeni model eğitilir
#     4. Referans istatistikler güncellenir
#     5. Retrain geçmişi loglanır
#
# TETİKLEYİCİLER (monitoring.yaml):
#   - drift_detected: Data drift algılandı
#   - performance_degraded: Metrikler düştü
#   - manual: API veya CLI'dan tetikleme
#   - scheduled: Zamanlı (her 30 günde bir)
#
# ÇAĞRILIŞ:
#   # Otomatik (monitoring sonrası)
#   pipeline = RetrainPipeline()
#   result = pipeline.run(reason="drift_detected", monitoring_report=report)
#
#   # Manuel
#   result = pipeline.run(reason="manual", force=True)
# ============================================================================

import sys
import time
from datetime import datetime
from typing import Optional

from src.exception import CustomException
from src.logger import logging
from src.utils.common import load_yaml


class RetrainPipeline:
    """
    Monitoring sonuçlarına göre modeli yeniden eğiten pipeline.

    AKIŞ:
      1. Retrain gerekli mi kontrol et (force=True ise atla)
      2. Cooldown aktif mi kontrol et
      3. TrainPipeline.run() çağır
      4. Yeni referans istatistiklerini kaydet
      5. Retrain olayını logla

    NEDEN AYRI BİR PIPELINE?
      TrainPipeline saf eğitim yapar. RetrainPipeline ise:
        - Monitoring bağlamını bilir (neden retrain?)
        - Cooldown kontrolü yapar (çok sık retrain engeli)
        - Retrain geçmişi tutar
        - Referans istatistikleri günceller
    """

    def __init__(self):
        try:
            self._mon_cfg = load_yaml("configs/monitoring.yaml")
            retrain_cfg = self._mon_cfg.get("retrain", {})
            self.auto_retrain: bool = retrain_cfg.get("auto_retrain", False)
            self.enabled: bool = retrain_cfg.get("enabled", True)
        except Exception as e:
            raise CustomException(e, sys)

    def run(
        self,
        reason: str = "manual",
        monitoring_report: Optional[dict] = None,
        force: bool = False,
    ) -> dict:
        """
        Yeniden eğitim pipeline'ını çalıştırır.

        KARAR AĞACI:
          1. force=True → direkt eğit (tüm kontrolleri atla)
          2. enabled=False → iptal
          3. auto_retrain=False ve reason!="manual" → iptal
          4. Cooldown aktif → iptal
          5. monitoring_report varsa ve needs_retrain=False → iptal
          6. Tüm kontrollerden geçti → eğit!

        Args:
            reason: Retrain nedeni (drift_detected, performance_degraded, manual, scheduled)
            monitoring_report: ModelMonitor.full_check() çıktısı
            force: True ise tüm kontrolleri atla

        Returns:
            dict: {
                "retrained": bool,
                "reason": str,
                "result": train_result veya None,
                "message": str,
                "timestamp": str
            }
        """
        try:
            logging.info(f"🔄 Retrain pipeline başlatılıyor (neden: {reason})...")
            t0 = time.time()

            # ─── Ön kontroller ───
            if not force:
                # Retrain devre dışı mı?
                if not self.enabled:
                    msg = "Retrain devre dışı (monitoring.yaml: retrain.enabled=false)"
                    logging.info(f"  ⏭ {msg}")
                    return self._result(False, reason, None, msg)

                # Auto-retrain kapalı ve manuel değilse
                if not self.auto_retrain and reason != "manual":
                    msg = (
                        f"Auto-retrain kapalı, neden '{reason}' manuel değil. "
                        f"monitoring.yaml: retrain.auto_retrain=true yaparak aktifleştirin."
                    )
                    logging.info(f"  ⏭ {msg}")
                    return self._result(False, reason, None, msg)

                # Monitoring raporu var ve retrain gerekmiyorsa
                if monitoring_report and not monitoring_report.get("needs_retrain", True):
                    msg = "Monitoring raporu retrain gerektirmiyor"
                    logging.info(f"  ⏭ {msg}")
                    return self._result(False, reason, None, msg)

                # Cooldown kontrolü
                from src.components.model_monitor import ModelMonitor

                monitor = ModelMonitor()
                if not monitor.can_retrain():
                    msg = "Cooldown aktif — henüz çok erken"
                    logging.info(f"  ⏭ {msg}")
                    return self._result(False, reason, None, msg)

            # ─── EĞİTİM ───
            logging.info("  🎯 Eğitim başlatılıyor...")
            from src.pipeline.train_pipeline import TrainPipeline

            train_pipeline = TrainPipeline()
            train_result = train_pipeline.run()

            # ─── REFERANS İSTATİSTİKLERİ GÜNCELLE ───
            self._update_reference_stats()

            # ─── RETRAİN GEÇMİŞİNE KAYDET ───
            from src.components.model_monitor import ModelMonitor

            monitor = ModelMonitor()
            monitor.log_retrain_event(reason, train_result)

            elapsed = round(time.time() - t0, 2)
            msg = (
                f"Retrain tamamlandı! Model: {train_result.get('best_model')}, "
                f"F1: {train_result.get('best_f1', 0):.4f}, Süre: {elapsed}s"
            )
            logging.info(f"  ✅ {msg}")

            return self._result(True, reason, train_result, msg)

        except Exception as e:
            raise CustomException(e, sys)

    def _update_reference_stats(self) -> None:
        """
        Eğitim sonrası referans istatistiklerini günceller.

        NEDEN GEREKLİ?
          Yeni model yeni veriye göre eğitildi. Drift referansı da
          yeni eğitim verisine göre güncellenmelidir.
        """
        try:
            from src.components.data_ingestion import DataIngestion
            from src.components.drift_detector import DriftDetector
            import pandas as pd
            import numpy as np

            logging.info("  📊 Referans istatistikler güncelleniyor...")

            # Eğitim verisini yükle
            ingestion = DataIngestion()
            result = ingestion.initiate()

            # Mod kontrolü: tuple uzunluğuna göre
            if len(result) == 4:
                # NPZ modu → numpy array, DataFrame'e dönüştüremeyiz
                # Referans güncelleme atla
                logging.info(
                    "  ℹ NPZ modu — referans istatistikler "
                    "sayısal özetle güncellenemedi (atlanıyor)"
                )
                return

            # CSV modu → DataFrame
            train_df, _ = result
            if isinstance(train_df, pd.DataFrame):
                detector = DriftDetector()
                detector.save_reference_stats(train_df)

        except Exception as e:
            logging.warning(f"  ⚠ Referans güncelleme başarısız: {e}")

    @staticmethod
    def _result(retrained: bool, reason: str, result: dict, message: str) -> dict:
        """Standart sonuç dict'i oluşturur."""
        return {
            "retrained": retrained,
            "reason": reason,
            "result": result,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
