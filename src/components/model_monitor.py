# ============================================================================
# model_monitor.py — Model Performans İzleme Bileşeni
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Model production'a çıktıktan sonra performansı zamanla düşebilir
#   (model decay / concept drift). Bu modül:
#     1. Baseline metriklerle güncel durumu karşılaştırır
#     2. Drift analizi sonuçlarını birleştirir
#     3. Retrain kararı verir (gerekli mi, değil mi?)
#     4. Monitoring raporu üretir
#
# KAVRAM — MODEL DECAY:
#   Müşteri davranışı zamanla değişir. 2020'de eğitilen model 2026'da
#   artık geçersiz olabilir çünkü:
#     - Yeni tarifeler çıkmış (MonthlyCharges dağılımı değişmiş)
#     - Fiber optic artık varsayılan olmuş (InternetService dağılımı)
#     - Pandemi sonrası sözleşme tercihleri farklılaşmış
#
# ÇAĞRILIŞ:
#   monitor = ModelMonitor()
#   report = monitor.full_check()
#   print(report["needs_retrain"])  # True / False
# ============================================================================

import os
import sys
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from src.exception import CustomException
from src.logger import logging
from src.utils.common import load_yaml, load_json, save_json


# ─────────────────────────────────────────────────────────────────────────────
# KONFİGÜRASYON
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ModelMonitorConfig:
    """
    Performans izleme ayarları. monitoring.yaml'dan okunur.
    """
    _mon: dict = field(default=None, repr=False)

    def __post_init__(self):
        self._mon = load_yaml("configs/monitoring.yaml")
        perf_cfg = self._mon.get("performance", {})
        retrain_cfg = self._mon.get("retrain", {})

        self.enabled: bool = perf_cfg.get("enabled", True)
        self.baseline_path: str = perf_cfg.get(
            "baseline_metrics_path", "artifacts/metrics.json"
        )
        self.degradation_thresholds: dict = perf_cfg.get(
            "degradation_thresholds",
            {"f1": 0.10, "recall": 0.15, "precision": 0.10, "roc_auc": 0.05},
        )

        # Retrain ayarları
        self.auto_retrain: bool = retrain_cfg.get("auto_retrain", False)
        self.cooldown_hours: int = retrain_cfg.get("cooldown_hours", 24)
        self.history_path: str = retrain_cfg.get(
            "history_path", "logs/retrain_history.json"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ANA SINIF
# ─────────────────────────────────────────────────────────────────────────────

class ModelMonitor:
    """
    Model performansını izler, drift sonuçlarıyla birleştirir
    ve retrain gerekip gerekmediğine karar verir.

    KULLANIM:
        monitor = ModelMonitor()

        # Sadece performans kontrolü
        perf_report = monitor.check_performance(current_metrics)

        # Tam kontrol (performans + drift)
        full_report = monitor.full_check(current_metrics, drift_report)
    """

    def __init__(self, config: Optional[ModelMonitorConfig] = None):
        try:
            self.config = config or ModelMonitorConfig()
        except Exception as e:
            raise CustomException(e, sys)

    # ─────────────────────────────────────────────────────────────────
    # BASELINE METRİKLER
    # ─────────────────────────────────────────────────────────────────

    def get_baseline(self) -> dict:
        """
        Eğitim sonrası kaydedilen baseline metrikleri yükler.

        Returns:
            dict: {"accuracy": 0.79, "f1": 0.61, "recall": 0.52, ...}
        """
        try:
            if not os.path.exists(self.config.baseline_path):
                raise FileNotFoundError(
                    f"Baseline metrikleri bulunamadı: {self.config.baseline_path}"
                )
            data = load_json(self.config.baseline_path)
            return data.get("metrics", data)
        except Exception as e:
            raise CustomException(e, sys)

    # ─────────────────────────────────────────────────────────────────
    # PERFORMANS KONTROLÜ
    # ─────────────────────────────────────────────────────────────────

    def check_performance(self, current_metrics: dict) -> dict:
        """
        Güncel metrikleri baseline ile karşılaştırır.

        AKIŞ:
          1. Baseline metrikleri yükle (eğitim sonrası kaydedilmiş)
          2. Her metrik için: (baseline - current) / baseline > threshold?
          3. Degraded metrikleri listele
          4. Genel performance_ok kararı ver

        Args:
            current_metrics: Güncel model metrikleri
                {"f1": 0.55, "recall": 0.48, ...}

        Returns:
            dict: {
                "performance_ok": bool,
                "degraded_metrics": [...],
                "comparisons": {metrik: {baseline, current, drop, threshold}},
                "status": "healthy" | "degraded" | "critical"
            }
        """
        try:
            logging.info("📈 Performans kontrolü yapılıyor...")

            baseline = self.get_baseline()
            degraded = []
            comparisons = {}

            for metric, threshold in self.config.degradation_thresholds.items():
                base_val = baseline.get(metric)
                curr_val = current_metrics.get(metric)

                if base_val is None or curr_val is None:
                    continue

                # Yüzde düşüş hesapla
                drop = (base_val - curr_val) / base_val if base_val > 0 else 0.0
                is_degraded = drop > threshold

                comparisons[metric] = {
                    "baseline": round(base_val, 4),
                    "current": round(curr_val, 4),
                    "drop_pct": round(drop * 100, 2),
                    "threshold_pct": round(threshold * 100, 2),
                    "degraded": is_degraded,
                }

                if is_degraded:
                    degraded.append(metric)
                    logging.warning(
                        f"  ⚠ {metric}: {base_val:.4f} → {curr_val:.4f} "
                        f"(düşüş: %{drop*100:.1f}, eşik: %{threshold*100:.0f})"
                    )
                else:
                    logging.info(
                        f"  ✅ {metric}: {base_val:.4f} → {curr_val:.4f} "
                        f"(düşüş: %{drop*100:.1f})"
                    )

            # Genel durum
            if len(degraded) == 0:
                status = "healthy"
            elif len(degraded) <= 1:
                status = "degraded"
            else:
                status = "critical"

            result = {
                "performance_ok": len(degraded) == 0,
                "degraded_metrics": degraded,
                "total_checked": len(comparisons),
                "comparisons": comparisons,
                "status": status,
            }

            logging.info(
                f"  Performans durumu: {status} "
                f"({len(degraded)} metrik bozulmuş)"
            )

            return result

        except Exception as e:
            raise CustomException(e, sys)

    # ─────────────────────────────────────────────────────────────────
    # TAM KONTROL — Performans + Drift Birleştirme
    # ─────────────────────────────────────────────────────────────────

    def full_check(
        self,
        current_metrics: Optional[dict] = None,
        drift_report: Optional[dict] = None,
    ) -> dict:
        """
        Performans ve drift sonuçlarını birleştirerek retrain kararı verir.

        KARAR MATRİSİ:
          - Drift YOK + Performans OK     → ✅ "stable" (retrain gereksiz)
          - Drift YOK + Performans DÜŞTÜ  → ⚠ "degraded" (izle)
          - Drift VAR + Performans OK     → ⚠ "drift_warning" (izle)
          - Drift VAR + Performans DÜŞTÜ  → 🚨 "retrain_needed" (acil)

        Args:
            current_metrics: Güncel model metrikleri (opsiyonel)
            drift_report: DriftDetector.analyze() çıktısı (opsiyonel)

        Returns:
            dict: Birleşik monitoring raporu
        """
        try:
            logging.info("🔎 Tam monitoring kontrolü başlatılıyor...")

            report = {
                "timestamp": datetime.now().isoformat(),
                "needs_retrain": False,
                "retrain_reason": [],
                "overall_status": "stable",
                "performance": None,
                "drift": None,
            }

            # ─── Performans kontrolü ───
            has_perf_issue = False
            if current_metrics:
                perf_result = self.check_performance(current_metrics)
                report["performance"] = perf_result
                if not perf_result["performance_ok"]:
                    has_perf_issue = True
                    report["retrain_reason"].append("performance_degraded")

            # ─── Drift kontrolü ───
            has_drift = False
            if drift_report:
                report["drift"] = {
                    "drift_detected": drift_report.get("drift_detected", False),
                    "drift_ratio": drift_report.get("drift_ratio", 0),
                    "drifted_features": drift_report.get("drifted_features", []),
                    "alert_level": drift_report.get("alert_level", "none"),
                }
                if drift_report.get("drift_detected", False):
                    has_drift = True
                    report["retrain_reason"].append("drift_detected")

            # ─── Genel karar ───
            if has_drift and has_perf_issue:
                report["overall_status"] = "retrain_needed"
                report["needs_retrain"] = True
            elif has_perf_issue:
                report["overall_status"] = "degraded"
                report["needs_retrain"] = True
            elif has_drift:
                report["overall_status"] = "drift_warning"
                # Drift var ama performans düşmemiş → hemen retrain gerekmez
                report["needs_retrain"] = False
            else:
                report["overall_status"] = "stable"

            status_emoji = {
                "stable": "✅",
                "degraded": "⚠️",
                "drift_warning": "🔄",
                "retrain_needed": "🚨",
            }
            logging.info(
                f"  {status_emoji.get(report['overall_status'], '❓')} "
                f"Genel durum: {report['overall_status']} | "
                f"Retrain: {'EVET' if report['needs_retrain'] else 'HAYIR'}"
            )

            return report

        except Exception as e:
            raise CustomException(e, sys)

    # ─────────────────────────────────────────────────────────────────
    # RETRAİN GEÇMİŞİ
    # ─────────────────────────────────────────────────────────────────

    def log_retrain_event(self, reason: str, result: dict) -> None:
        """
        Retrain olayını geçmiş dosyasına kaydeder.

        Args:
            reason: Retrain nedeni ("drift_detected", "performance_degraded", "manual")
            result: TrainPipeline.run() çıktısı
        """
        try:
            history = []
            if os.path.exists(self.config.history_path):
                history = load_json(self.config.history_path)
                if not isinstance(history, list):
                    history = []

            event = {
                "timestamp": datetime.now().isoformat(),
                "reason": reason,
                "best_model": result.get("best_model", "unknown"),
                "best_f1": result.get("best_f1", 0),
                "total_time": result.get("total_time", "N/A"),
            }
            history.append(event)

            save_json(history, self.config.history_path)
            logging.info(f"📝 Retrain olayı kaydedildi: {reason}")

        except Exception as e:
            logging.error(f"Retrain geçmişi kayıt hatası: {e}")

    def get_retrain_history(self) -> list:
        """
        Retrain geçmişini döndürür.

        Returns:
            list: Retrain olaylarının listesi
        """
        try:
            if not os.path.exists(self.config.history_path):
                return []
            data = load_json(self.config.history_path)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def can_retrain(self) -> bool:
        """
        Cooldown süresi geçmiş mi kontrol eder.

        Son retrain'den bu yana yeterli süre (cooldown_hours) geçmediyse
        yeni retrain engellenebilir (çok sık eğitim önlenir).

        Returns:
            bool: True → retrain yapılabilir
        """
        try:
            history = self.get_retrain_history()
            if not history:
                return True

            last_event = history[-1]
            last_time = datetime.fromisoformat(last_event["timestamp"])
            hours_since = (datetime.now() - last_time).total_seconds() / 3600

            can = hours_since >= self.config.cooldown_hours
            if not can:
                logging.info(
                    f"  ⏳ Cooldown aktif: Son retrain {hours_since:.1f}h önce "
                    f"(minimum {self.config.cooldown_hours}h)"
                )
            return can

        except Exception:
            return True
