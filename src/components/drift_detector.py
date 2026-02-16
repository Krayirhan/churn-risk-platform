# ============================================================================
# drift_detector.py — Veri Drift Algılama Bileşeni
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Modelin eğitildiği veri dağılımı ile production'daki gelen verilerin
#   dağılımı zamanla farklılaşabilir (data drift). Bu modül:
#     1. Eğitim verisi istatistiklerini referans olarak kaydeder
#     2. Production tahminlerini toplu analiz eder
#     3. İstatistiksel testlerle drift olup olmadığını tespit eder
#
# YÖNTEMLER:
#   - Sayısal features → Kolmogorov-Smirnov testi (dağılım karşılaştırma)
#   - Kategorik features → Population Stability Index (PSI)
#
# KAVRAM — NEDEN DRIFT ÖNEMLİ?
#   Eğitim verisi 2020'den, production verisi 2026'dan olabilir.
#   Müşteri profili değişmiş olabilir (yeni tarifeler, pandemi etkisi vb.).
#   Model eski dağılıma göre öğrenmiş → yeni dağılımda performansı düşer.
#   Drift tespit edilirse → retrain tetiklenir.
#
# ÇAĞRILIŞ:
#   from src.components.drift_detector import DriftDetector
#   detector = DriftDetector()
#   report = detector.analyze(production_df)
# ============================================================================

import os
import sys
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

from scipy import stats

from src.exception import CustomException
from src.logger import logging
from src.utils.common import load_yaml, load_json, save_json


# ─────────────────────────────────────────────────────────────────────────────
# KONFİGÜRASYON
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DriftDetectorConfig:
    """
    Drift algılama ayarları. monitoring.yaml'dan okunur.
    """
    _mon: dict = field(default=None, repr=False)

    def __post_init__(self):
        self._mon = load_yaml("configs/monitoring.yaml")
        drift_cfg = self._mon.get("drift", {})

        self.enabled: bool = drift_cfg.get("enabled", True)
        self.reference_data_path: str = drift_cfg.get(
            "reference_data_path", "artifacts/reference_stats.json"
        )
        self.min_sample_size: int = drift_cfg.get("min_sample_size", 50)

        # Sayısal feature drift ayarları
        num_cfg = drift_cfg.get("numerical", {})
        self.num_method: str = num_cfg.get("method", "ks_test")
        self.num_p_threshold: float = num_cfg.get("p_value_threshold", 0.05)
        self.num_features: list = num_cfg.get(
            "features", ["tenure", "MonthlyCharges", "TotalCharges"]
        )

        # Kategorik feature drift ayarları
        cat_cfg = drift_cfg.get("categorical", {})
        self.cat_method: str = cat_cfg.get("method", "psi")
        self.cat_psi_threshold: float = cat_cfg.get("psi_threshold", 0.2)
        self.cat_features: list = cat_cfg.get(
            "features", ["Contract", "InternetService", "PaymentMethod"]
        )

        # Genel alert eşiği
        self.alert_threshold: float = drift_cfg.get("alert_threshold", 0.3)


# ─────────────────────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────────────────────────

def compute_psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """
    Population Stability Index (PSI) hesaplar.

    PSI NEDİR?
      İki dağılımın ne kadar farklılaştığını ölçen bir metrik.
      Kredi riski ve churn modellerinde yaygın kullanılır.

    YORUM:
      PSI < 0.1   → Değişiklik yok (stabil)
      PSI 0.1-0.2 → Hafif kayma (izle)
      PSI > 0.2   → Ciddi kayma (retrain gerekebilir)

    FORMÜL:
      PSI = Σ (P_i - Q_i) × ln(P_i / Q_i)
      P_i = referans dağılımın i. bin oranı
      Q_i = güncel dağılımın i. bin oranı

    Args:
        reference: Eğitim verisinin değerleri
        current: Production verisinin değerleri
        bins: Histogram bin sayısı

    Returns:
        float: PSI değeri (0 = aynı dağılım, yüksek = farklı)
    """
    # Her iki dağılımı aynı bin'lere böl
    ref_float = reference.astype(float)
    cur_float = current.astype(float)

    # Bin sınırlarını referans verisinden belirle
    min_val = min(ref_float.min(), cur_float.min())
    max_val = max(ref_float.max(), cur_float.max())
    bin_edges = np.linspace(min_val, max_val, bins + 1)

    # Histogram frekanslarını hesapla ve normalize et
    ref_hist, _ = np.histogram(ref_float, bins=bin_edges)
    cur_hist, _ = np.histogram(cur_float, bins=bin_edges)

    # Sıfır bölmesi önleme (Laplace smoothing)
    ref_pct = (ref_hist + 1) / (ref_hist.sum() + bins)
    cur_pct = (cur_hist + 1) / (cur_hist.sum() + bins)

    # PSI formülü
    psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(round(psi, 6))


def compute_categorical_psi(
    ref_counts: dict, cur_series: pd.Series
) -> float:
    """
    Kategorik feature için PSI hesaplar.

    Kategorik veride histogram yerine frekans oranları kullanılır.

    Args:
        ref_counts: Referans frekans oranları {"Month-to-month": 0.55, ...}
        cur_series: Production verisindeki kategorik sütun

    Returns:
        float: PSI değeri
    """
    cur_counts = cur_series.value_counts(normalize=True).to_dict()

    # Tüm kategorileri birleştir
    all_categories = set(ref_counts.keys()) | set(cur_counts.keys())

    psi = 0.0
    eps = 1e-6  # Sıfır bölme koruma
    for cat in all_categories:
        ref_pct = ref_counts.get(cat, eps)
        cur_pct = cur_counts.get(cat, eps)
        # Sıfıra çok yakın değerleri düzelt
        ref_pct = max(ref_pct, eps)
        cur_pct = max(cur_pct, eps)
        psi += (cur_pct - ref_pct) * np.log(cur_pct / ref_pct)

    return float(round(abs(psi), 6))


# ─────────────────────────────────────────────────────────────────────────────
# ANA SINIF
# ─────────────────────────────────────────────────────────────────────────────

class DriftDetector:
    """
    Eğitim verisinin dağılımıyla production verisini karşılaştırarak
    data drift olup olmadığını tespit eder.

    KULLANIM:
        detector = DriftDetector()
        # 1) Eğitim sonrası referans istatistikleri kaydet
        detector.save_reference_stats(train_df)
        # 2) Production verisi ile drift kontrolü
        report = detector.analyze(production_df)
        print(report["drift_detected"])  # True/False
    """

    def __init__(self, config: Optional[DriftDetectorConfig] = None):
        try:
            self.config = config or DriftDetectorConfig()
        except Exception as e:
            raise CustomException(e, sys)

    # ─────────────────────────────────────────────────────────────────
    # REFERANS İSTATİSTİKLER — Eğitim Verisini Kaydet
    # ─────────────────────────────────────────────────────────────────

    def save_reference_stats(self, df: pd.DataFrame) -> str:
        """
        Eğitim verisinin istatistiklerini referans olarak kaydeder.

        NEDEN KAYDET?
          Production'da drift kontrolü yaparken "neye göre" karşılaştıracağız?
          Eğitim verisinin dağılımı referans noktamız. Bu metod eğitim
          sonrasında bir kere çağrılır ve referans istatistikleri JSON'a yazar.

        KAYDEDILEN İSTATİSTİKLER:
          - Sayısal: mean, std, min, max, median, quantiles, ham değerler (sample)
          - Kategorik: frekans oranları, unique değerler

        Args:
            df: Eğitim verisi DataFrame'i

        Returns:
            str: Kaydedilen dosya yolu
        """
        try:
            logging.info("📊 Referans istatistikler hesaplanıyor...")
            ref_stats = {"numerical": {}, "categorical": {}}

            # ─── Sayısal Feature İstatistikleri ───
            for col in self.config.num_features:
                if col in df.columns:
                    values = df[col].dropna().astype(float)
                    ref_stats["numerical"][col] = {
                        "mean": float(values.mean()),
                        "std": float(values.std()),
                        "min": float(values.min()),
                        "max": float(values.max()),
                        "median": float(values.median()),
                        "q25": float(values.quantile(0.25)),
                        "q75": float(values.quantile(0.75)),
                        "count": int(len(values)),
                        # Referans dağılım sample'ı (KS testi için)
                        # Bellek tasarrufu: en fazla 1000 örnek
                        "sample": values.sample(
                            min(1000, len(values)), random_state=42
                        ).tolist(),
                    }
                    logging.info(
                        f"  {col}: mean={values.mean():.2f}, "
                        f"std={values.std():.2f}, n={len(values)}"
                    )

            # ─── Kategorik Feature İstatistikleri ───
            for col in self.config.cat_features:
                if col in df.columns:
                    freq = df[col].value_counts(normalize=True)
                    ref_stats["categorical"][col] = {
                        "frequencies": freq.to_dict(),
                        "unique_values": df[col].unique().tolist(),
                        "count": int(len(df[col].dropna())),
                    }
                    logging.info(
                        f"  {col}: {len(freq)} kategori, "
                        f"en sık={freq.index[0]} (%{freq.iloc[0]*100:.1f})"
                    )

            # Kaydet
            save_json(ref_stats, self.config.reference_data_path)
            logging.info(
                f"✅ Referans istatistikler kaydedildi → "
                f"{self.config.reference_data_path}"
            )
            return self.config.reference_data_path

        except Exception as e:
            raise CustomException(e, sys)

    # ─────────────────────────────────────────────────────────────────
    # DRIFT ANALİZİ — Production Verisini Kontrol Et
    # ─────────────────────────────────────────────────────────────────

    def analyze(self, current_df: pd.DataFrame) -> dict:
        """
        Production verisini referans ile karşılaştırarak drift raporu üretir.

        AKIŞ:
          1. Referans istatistikleri yükle (eğitim zamanında kaydedilmiş)
          2. Her sayısal feature için KS testi uygula
          3. Her kategorik feature için PSI hesapla
          4. Drift olan feature sayısını hesapla
          5. Genel alert kararı ver

        Args:
            current_df: Production verisinden toplanan DataFrame

        Returns:
            dict: {
                "drift_detected": bool,
                "drifted_features": [...],
                "total_features_checked": int,
                "drift_ratio": float,
                "numerical_results": {...},
                "categorical_results": {...},
                "alert_level": "none" | "warning" | "critical"
            }
        """
        try:
            logging.info("🔍 Drift analizi başlatılıyor...")

            # ─── Ön kontroller ───
            if not self.config.enabled:
                logging.info("  Drift algılama devre dışı (monitoring.yaml)")
                return {"drift_detected": False, "message": "Drift algılama devre dışı"}

            if len(current_df) < self.config.min_sample_size:
                logging.warning(
                    f"  Yetersiz örnek: {len(current_df)} < "
                    f"{self.config.min_sample_size} (minimum)"
                )
                return {
                    "drift_detected": False,
                    "message": f"Yetersiz örnek sayısı ({len(current_df)})",
                }

            # ─── Referans istatistikleri yükle ───
            if not os.path.exists(self.config.reference_data_path):
                raise FileNotFoundError(
                    f"Referans istatistik dosyası bulunamadı: "
                    f"{self.config.reference_data_path}\n"
                    f"Önce save_reference_stats() çağrılmalı."
                )
            ref_stats = load_json(self.config.reference_data_path)

            drifted_features = []
            numerical_results = {}
            categorical_results = {}

            # ─── SAYISAL DRIFT: KS Testi ───
            num_ref = ref_stats.get("numerical", {})
            for col in self.config.num_features:
                if col not in current_df.columns or col not in num_ref:
                    continue

                ref_sample = np.array(num_ref[col]["sample"])
                cur_values = current_df[col].dropna().astype(float).values

                # KS Testi: İki örneklemin aynı dağılımdan gelip gelmediğini test eder
                ks_stat, p_value = stats.ks_2samp(ref_sample, cur_values)
                is_drifted = p_value < self.config.num_p_threshold

                numerical_results[col] = {
                    "ks_statistic": round(ks_stat, 6),
                    "p_value": round(p_value, 6),
                    "drift_detected": is_drifted,
                    "ref_mean": num_ref[col]["mean"],
                    "cur_mean": float(np.mean(cur_values)),
                    "ref_std": num_ref[col]["std"],
                    "cur_std": float(np.std(cur_values)),
                }

                if is_drifted:
                    drifted_features.append(col)
                    logging.warning(
                        f"  ⚠ DRIFT: {col} — KS={ks_stat:.4f}, "
                        f"p={p_value:.4f} < {self.config.num_p_threshold}"
                    )
                else:
                    logging.info(
                        f"  ✅ {col} — KS={ks_stat:.4f}, p={p_value:.4f} (stabil)"
                    )

            # ─── KATEGORİK DRIFT: PSI ───
            cat_ref = ref_stats.get("categorical", {})
            for col in self.config.cat_features:
                if col not in current_df.columns or col not in cat_ref:
                    continue

                ref_freq = cat_ref[col]["frequencies"]
                psi_val = compute_categorical_psi(ref_freq, current_df[col])
                is_drifted = psi_val > self.config.cat_psi_threshold

                categorical_results[col] = {
                    "psi": psi_val,
                    "drift_detected": is_drifted,
                    "threshold": self.config.cat_psi_threshold,
                    "ref_distribution": ref_freq,
                    "cur_distribution": current_df[col]
                    .value_counts(normalize=True)
                    .to_dict(),
                }

                if is_drifted:
                    drifted_features.append(col)
                    logging.warning(
                        f"  ⚠ DRIFT: {col} — PSI={psi_val:.4f} > "
                        f"{self.config.cat_psi_threshold}"
                    )
                else:
                    logging.info(f"  ✅ {col} — PSI={psi_val:.4f} (stabil)")

            # ─── GENEL KARAR ───
            total_checked = len(numerical_results) + len(categorical_results)
            drift_ratio = (
                len(drifted_features) / total_checked if total_checked > 0 else 0.0
            )
            drift_detected = drift_ratio >= self.config.alert_threshold

            # Alert seviyesi
            if drift_ratio == 0:
                alert_level = "none"
            elif drift_ratio < self.config.alert_threshold:
                alert_level = "warning"
            else:
                alert_level = "critical"

            report = {
                "drift_detected": drift_detected,
                "drifted_features": drifted_features,
                "total_features_checked": total_checked,
                "drift_ratio": round(drift_ratio, 4),
                "alert_level": alert_level,
                "numerical_results": numerical_results,
                "categorical_results": categorical_results,
                "sample_size": len(current_df),
                "threshold": self.config.alert_threshold,
            }

            level_emoji = {"none": "✅", "warning": "⚠️", "critical": "🚨"}
            logging.info(
                f"  {level_emoji.get(alert_level, '❓')} Drift raporu: "
                f"{len(drifted_features)}/{total_checked} feature drift "
                f"(oran: {drift_ratio:.1%}, alert: {alert_level})"
            )

            return report

        except Exception as e:
            raise CustomException(e, sys)
