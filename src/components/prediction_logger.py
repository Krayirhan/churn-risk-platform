# ============================================================================
# prediction_logger.py — Tahmin Loglama Bileşeni
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Her API tahminini JSONL (JSON Lines) dosyasına loglar.
#   Bu loglar:
#     1. Data drift analizinin veri kaynağı
#     2. Model performans izlemenin ground-truth karşılaştırma noktası
#     3. Audit trail (denetim izi) — hangi müşteriye ne tahmin yapıldı?
#     4. A/B test ve retrain kararlarının dayanağı
#
# FORMAT: JSON Lines (.jsonl)
#   Her satır bağımsız bir JSON nesnesi → satır satır okunabilir,
#   büyük dosyalar belleğe sığmasa bile stream edilebilir.
#
# KULLANIM:
#   logger = PredictionLogger()
#   logger.log(input_features, prediction_result)
#   recent = logger.get_recent(n=100)  # Son 100 tahmini oku
# ============================================================================

import os
import sys
import json
import glob
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional

from src.exception import CustomException
from src.logger import logging
from src.utils.common import load_yaml


# ─────────────────────────────────────────────────────────────────────────────
# KONFİGÜRASYON
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PredictionLoggerConfig:
    """
    Tahmin loglama ayarları. monitoring.yaml'dan okunur.
    """
    _mon: dict = field(default=None, repr=False)

    def __post_init__(self):
        self._mon = load_yaml("configs/monitoring.yaml")
        log_cfg = self._mon.get("prediction_log", {})

        self.enabled: bool = log_cfg.get("enabled", True)
        self.log_dir: str = log_cfg.get("log_dir", "logs/predictions")
        self.file_prefix: str = log_cfg.get("file_prefix", "predictions")
        self.rotation: str = log_cfg.get("rotation", "daily")
        self.max_retention_days: int = log_cfg.get("max_retention_days", 90)


# ─────────────────────────────────────────────────────────────────────────────
# ANA SINIF
# ─────────────────────────────────────────────────────────────────────────────

class PredictionLogger:
    """
    Her tahmin sonucunu JSONL dosyasına loglar.

    NEDEN JSONL?
      - CSV'ye göre avantajı: iç içe dict'ler desteklenir (input_features).
      - Her satır bağımsız parse edilir → büyük dosyalarda bellek dostu.
      - Günlük rotasyon: predictions_2026-02-16.jsonl, predictions_2026-02-17.jsonl

    KULLANIM:
        logger = PredictionLogger()
        logger.log(
            input_features={"tenure": 24, "MonthlyCharges": 79.85, ...},
            prediction=1,
            churn_probability=0.82,
            risk_level="Yüksek",
            customer_id="CUST_001"
        )
    """

    def __init__(self, config: Optional[PredictionLoggerConfig] = None):
        try:
            self.config = config or PredictionLoggerConfig()
            os.makedirs(self.config.log_dir, exist_ok=True)
        except Exception as e:
            raise CustomException(e, sys)

    # ─────────────────────────────────────────────────────────────────
    # LOG DOSYA YOLU
    # ─────────────────────────────────────────────────────────────────

    def _get_log_path(self, date: Optional[datetime] = None) -> str:
        """
        Günün tarihine göre log dosya yolunu döndürür.

        ROTASYON:
          daily  → predictions_2026-02-16.jsonl
          Eski dosyalar birikerek drift analizi için veri deposu oluşturur.

        Args:
            date: Opsiyonel tarih (None → bugün)

        Returns:
            str: Log dosya yolu
        """
        d = date or datetime.now()
        filename = f"{self.config.file_prefix}_{d.strftime('%Y-%m-%d')}.jsonl"
        return os.path.join(self.config.log_dir, filename)

    # ─────────────────────────────────────────────────────────────────
    # TAHMİN LOGLA
    # ─────────────────────────────────────────────────────────────────

    def log(
        self,
        input_features: dict,
        prediction: int,
        churn_probability: float,
        risk_level: str,
        customer_id: str = "unknown",
        model_version: str = "v1",
        extra: Optional[dict] = None,
    ) -> str:
        """
        Tek bir tahmin sonucunu JSONL dosyasına yazar.

        Her çağrıda dosya açılıp tek satır eklenir (append mode).
        Bu sayede:
          - Eşzamanlı istekler dosyayı bozamaz (satır bazlı yazma)
          - Sunucu çökse bile önceki loglar kaybolmaz

        Args:
            input_features: Müşterinin orijinal feature'ları
            prediction: Model tahmini (0 veya 1)
            churn_probability: Churn olasılığı (0.0-1.0)
            risk_level: Risk seviyesi ("Düşük", "Orta", "Yüksek")
            customer_id: Müşteri kimliği
            model_version: Model versiyonu
            extra: Ek metadata (opsiyonel)

        Returns:
            str: Yazılan log dosyasının yolu
        """
        try:
            if not self.config.enabled:
                return ""

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "customerID": customer_id,
                "prediction": prediction,
                "churn_probability": round(churn_probability, 4),
                "risk_level": risk_level,
                "model_version": model_version,
                "input_features": input_features,
            }

            if extra:
                log_entry["extra"] = extra

            log_path = self._get_log_path()
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            return log_path

        except Exception as e:
            # Loglama hatası tahmin akışını kesmemeli
            logging.error(f"Tahmin loglama hatası: {e}")
            return ""

    # ─────────────────────────────────────────────────────────────────
    # SON TAHMİNLERİ OKU
    # ─────────────────────────────────────────────────────────────────

    def get_recent(self, n: int = 100, days: int = 7) -> pd.DataFrame:
        """
        Son N günün tahmin loglarını DataFrame olarak döndürür.

        NEDEN DATAFRAME?
          Drift analizi ve performans izleme pd.DataFrame bekler.
          JSONL'dan satır satır okuyup DataFrame'e çeviririz.

        Args:
            n: Maksimum satır sayısı
            days: Kaç gün geriye git

        Returns:
            pd.DataFrame: Tahmin logları
        """
        try:
            all_entries = []

            for day_offset in range(days):
                date = datetime.now() - timedelta(days=day_offset)
                log_path = self._get_log_path(date)

                if not os.path.exists(log_path):
                    continue

                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                all_entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

            if not all_entries:
                return pd.DataFrame()

            # En son loglar önce gelsin
            all_entries.reverse()
            entries = all_entries[:n]

            df = pd.DataFrame(entries)
            logging.info(f"📋 {len(df)} tahmin logu okundu (son {days} gün)")
            return df

        except Exception as e:
            logging.error(f"Log okuma hatası: {e}")
            return pd.DataFrame()

    # ─────────────────────────────────────────────────────────────────
    # FEATURE DATAFRAME — Drift Analizi İçin
    # ─────────────────────────────────────────────────────────────────

    def get_features_df(self, n: int = 500, days: int = 7) -> pd.DataFrame:
        """
        Tahmin loglarından input_features sütunlarını ayrıştırıp
        düz DataFrame olarak döndürür.

        Drift analizi doğrudan bu DataFrame'i kullanır:
          detector.analyze(logger.get_features_df())

        Args:
            n: Maksimum satır sayısı
            days: Kaç gün geriye git

        Returns:
            pd.DataFrame: Her satır bir müşterinin feature'ları
        """
        try:
            recent = self.get_recent(n=n, days=days)
            if recent.empty or "input_features" not in recent.columns:
                return pd.DataFrame()

            features = pd.json_normalize(recent["input_features"])
            logging.info(
                f"📊 Feature DataFrame: {features.shape[0]} satır, "
                f"{features.shape[1]} sütun"
            )
            return features

        except Exception as e:
            logging.error(f"Feature extraction hatası: {e}")
            return pd.DataFrame()

    # ─────────────────────────────────────────────────────────────────
    # ESKİ LOGLARI TEMİZLE
    # ─────────────────────────────────────────────────────────────────

    def cleanup_old_logs(self) -> int:
        """
        max_retention_days'den eski log dosyalarını siler.

        NEDEN OTOMATİK TEMİZLİK?
          Günlük JSONL dosyaları birikir. 90 günlük retention ile
          disk dolmasını önleriz.

        Returns:
            int: Silinen dosya sayısı
        """
        try:
            cutoff = datetime.now() - timedelta(days=self.config.max_retention_days)
            pattern = os.path.join(
                self.config.log_dir, f"{self.config.file_prefix}_*.jsonl"
            )
            deleted = 0

            for filepath in glob.glob(pattern):
                filename = os.path.basename(filepath)
                # Dosya adından tarihi parse et: predictions_2026-02-16.jsonl
                try:
                    date_str = filename.replace(
                        f"{self.config.file_prefix}_", ""
                    ).replace(".jsonl", "")
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if file_date < cutoff:
                        os.remove(filepath)
                        deleted += 1
                except (ValueError, OSError):
                    continue

            if deleted > 0:
                logging.info(f"🧹 {deleted} eski log dosyası silindi")
            return deleted

        except Exception as e:
            logging.error(f"Log temizleme hatası: {e}")
            return 0

    # ─────────────────────────────────────────────────────────────────
    # İSTATİSTİK ÖZETİ
    # ─────────────────────────────────────────────────────────────────

    def get_stats(self, days: int = 7) -> dict:
        """
        Son N günün tahmin istatistiklerini döndürür.

        API /monitor/stats endpoint'i bu metodu çağırır.

        Returns:
            dict: {total_predictions, churn_count, churn_rate, avg_probability, ...}
        """
        try:
            recent = self.get_recent(n=10000, days=days)
            if recent.empty:
                return {
                    "total_predictions": 0,
                    "period_days": days,
                    "message": "Henüz tahmin logu yok",
                }

            total = len(recent)
            churn_count = int((recent["prediction"] == 1).sum())
            churn_rate = round(churn_count / total * 100, 2) if total > 0 else 0.0

            stats = {
                "total_predictions": total,
                "period_days": days,
                "churn_count": churn_count,
                "non_churn_count": total - churn_count,
                "churn_rate": churn_rate,
                "avg_churn_probability": round(
                    float(recent["churn_probability"].mean()), 4
                ),
                "risk_distribution": recent["risk_level"]
                .value_counts()
                .to_dict(),
            }

            return stats

        except Exception as e:
            logging.error(f"İstatistik hesaplama hatası: {e}")
            return {"error": str(e)}
