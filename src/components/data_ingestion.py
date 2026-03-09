# ============================================================================
# data_ingestion.py — Veri Alma ve Train/Test Bölme Bileşeni
# ============================================================================
# NEDEN BU DOSYA VAR?
#   ML pipeline'ının ilk adımı: veriyi al ve train/test olarak böl.
#   İki farklı modda çalışır:
#
#   MOD 1 — NOTEBOOK BRIDGE (Varsayılan):
#     Notebook Section 11'de export edilen telco_prepared_dataset.npz'yi yükler.
#     Bu dosyada X_mat (preprocessed matris), y (hedef), X_pca_95 (PCA küçültülmüş)
#     zaten hazır durumda. Notebook tüm cleaning + FE + preprocessing'i yapmış.
#
#   MOD 2 — RAW CSV FALLBACK:
#     Notebook çalıştırılmamışsa veya .npz yoksa, ham CSV'den okur.
#     Bu durumda data_transformation.py'nin işi artar (cleaning + FE yapması gerekir).
#
# ÇAĞRILIŞ ŞEKLİ:
#   train_pipeline.py → DataIngestion().initiate() → (X_train, X_test, y_train, y_test)
# ============================================================================

import os
import sys
import pandas as pd
from dataclasses import dataclass
from sklearn.model_selection import train_test_split

from src.exception import CustomException
from src.logger import logging
from src.utils.common import load_yaml, load_npz


# ─────────────────────────────────────────────────────────────────────────────
# KONFİGÜRASYON SINIFI
# ─────────────────────────────────────────────────────────────────────────────
# @dataclass: __init__ yazmaya gerek kalmaz, sadece alan tanımla.
# Tüm yollar config.yaml'dan okunur → hardcoded yol SIFIR.

@dataclass
class DataIngestionConfig:
    """
    Veri alma sürecinin tüm ayarları.
    __init__ içinde config.yaml okunur ve yollar buradan çekilir.
    """
    # Config dosyasını oku
    _cfg: dict = None

    def __post_init__(self):
        """
        @dataclass'ın __init__ sonrasında otomatik çalışan hook'u.
        Config.yaml'ı yükleyip dosya yollarını ayarlar.
        """
        self._cfg = load_yaml("configs/config.yaml")

        data_cfg = self._cfg.get("data", {})
        artifacts_cfg = self._cfg.get("artifacts", {})
        split_cfg = self._cfg.get("split", {})

        # --- Notebook artifact yolları ---
        # Notebook'un export ettiği .npz dosyasının tam yolu
        self.notebook_artifacts_dir: str = data_cfg.get("notebook_artifacts_dir", "notebooks/artifacts")
        self.npz_filename: str = data_cfg.get("npz_filename", "telco_prepared_dataset.npz")
        self.npz_path: str = os.path.join(self.notebook_artifacts_dir, self.npz_filename)

        # --- Ham veri yolu (fallback) ---
        self.raw_data_path: str = data_cfg.get("raw_path", "data/raw/churn.csv")

        # --- Artifacts çıktı yolları ---
        self.artifacts_dir: str = artifacts_cfg.get("base_dir", "artifacts")

        # --- Split parametreleri ---
        self.test_size: float = split_cfg.get("test_size", 0.2)
        self.random_state: int = split_cfg.get("random_state", 42)
        self.stratify: bool = split_cfg.get("stratify", True)

        # --- Hedef sütun adı (raw CSV modu için) ---
        self.target_col: str = self._cfg.get("target_col", "Churn")
        self.id_col: str = self._cfg.get("id_col", "customerID")


# ─────────────────────────────────────────────────────────────────────────────
# ANA SINIF
# ─────────────────────────────────────────────────────────────────────────────

class DataIngestion:
    """
    Veri alma ve train/test bölme işlemlerini yürüten ana sınıf.
    
    Kullanım:
        ingestion = DataIngestion()
        X_train, X_test, y_train, y_test = ingestion.initiate()
    """

    def __init__(self):
        self.config = DataIngestionConfig()

    def _load_from_notebook_npz(self) -> tuple:
        """
        MOD 1: Notebook'un ürettiği .npz dosyasından veri yükler.
        
        NEDEN BU MOD ÖNCELİKLİ?
          - Notebook zaten şunları yapmış:
            1. TotalCharges temizliği (business logic ile)
            2. 10 yeni feature üretimi (LoyaltyIndex, RiskScope vb.)
            3. ColumnTransformer ile preprocessing (scaling + encoding)
            4. PCA analizi
          - Yani X_mat = tam hazır, modele direkt girebilecek matris.
          - Bu, tekrarlanabilirliği artırır ve processing süresini azaltır.
        
        Returns:
            (X_train, X_test, y_train, y_test) tuple'ı
        """
        logging.info(f"📦 Notebook artifact'ından veri yükleniyor: {self.config.npz_path}")

        # .npz dosyasını yükle — içinde X_mat, y, X_pca_95 var
        npz_data = load_npz(self.config.npz_path)

        # Notebook'un export ettiği key'leri kontrol et
        required_keys = ["X", "y"]
        for key in required_keys:
            if key not in npz_data:
                raise KeyError(
                    f"NPZ dosyasında '{key}' key'i bulunamadı. "
                    f"Mevcut key'ler: {list(npz_data.keys())}"
                )

        X = npz_data["X"]   # (7043, N) — preprocessed feature matrisi
        y = npz_data["y"]   # (7043,) — hedef vektörü (0/1)

        logging.info(f"  X shape: {X.shape} | y shape: {y.shape}")
        logging.info(f"  Churn oranı: {y.mean():.4f} ({y.sum():.0f}/{len(y)})")

        # Train / Test bölmesi
        # NEDEN STRATİFY?
        #   Churn dengesiz (~%27). Stratify olmadan test setinde churn oranı
        #   %15 veya %40 olabilir → metrikler yanıltıcı olur.
        #   stratify=y ile her iki sette de ~%27 oranı korunur.
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=y if self.config.stratify else None
        )

        logging.info(
            f"  Train/Test bölündü → "
            f"Train: {X_train.shape[0]} satır | Test: {X_test.shape[0]} satır"
        )

        return X_train, X_test, y_train, y_test

    def _load_from_raw_csv(self) -> tuple:
        """
        MOD 2: Ham CSV'den okur. Notebook çalıştırılmamışsa fallback.
        
        DİKKAT:
          - Bu modda veri HAM haliyle gelir (cleaning/FE yapılmamış).
          - data_transformation.py'nin tüm işleri üstlenmesi gerekir.
          - Bu mod DataFrame döndürür (numpy array değil).
        
        Returns:
            (train_df, test_df) tuple'ı — pandas DataFrame
        """
        logging.info(f"📂 Ham CSV'den veri yükleniyor: {self.config.raw_data_path}")

        if not os.path.exists(self.config.raw_data_path):
            raise FileNotFoundError(
                f"Ham veri dosyası bulunamadı: {self.config.raw_data_path}\n"
                f"Lütfen data/raw/ klasörüne churn.csv dosyasını yerleştirin."
            )

        df = pd.read_csv(self.config.raw_data_path)
        logging.info(f"  Veri seti okundu: {df.shape[0]} satır × {df.shape[1]} sütun")

        # Hedef değişkeni 0/1'e çevir (Yes/No → 1/0)
        if self.config.target_col in df.columns:
            if df[self.config.target_col].dtype == "object":
                df[self.config.target_col] = df[self.config.target_col].map(
                    {"Yes": 1, "No": 0}
                ).astype(int)
                logging.info(f"  '{self.config.target_col}' sütunu Yes/No → 1/0 olarak dönüştürüldü")

        # Train / Test bölmesi
        train_df, test_df = train_test_split(
            df,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=df[self.config.target_col] if self.config.stratify else None
        )

        logging.info(
            f"  Train/Test bölündü → "
            f"Train: {train_df.shape[0]} satır | Test: {test_df.shape[0]} satır"
        )

        return train_df, test_df

    def initiate(self) -> tuple:
        """
        Veri alma sürecini başlatır. Önce notebook artifact'ını dener,
        yoksa ham CSV'ye düşer.
        
        KARAR MANTIĞI:
          1. notebooks/artifacts/telco_prepared_dataset.npz var mı? → Mod 1
          2. Yoksa → data/raw/churn.csv'den oku → Mod 2
        
        Returns:
            MOD 1: (X_train, X_test, y_train, y_test) — numpy array'ler
            MOD 2: (train_df, test_df) — pandas DataFrame'ler
        """
        try:
            logging.info("=" * 60)
            logging.info("DATA INGESTION başlatılıyor...")
            logging.info("=" * 60)

            # Artifacts klasörünü oluştur (yoksa)
            os.makedirs(self.config.artifacts_dir, exist_ok=True)

            # Karar: NPZ var mı?
            if os.path.exists(self.config.npz_path):
                logging.info("✅ Notebook artifact bulundu → Mod 1 (NPZ Bridge)")
                result = self._load_from_notebook_npz()
                mode = "npz"
            else:
                logging.info("⚠ Notebook artifact bulunamadı → Mod 2 (Raw CSV Fallback)")
                result = self._load_from_raw_csv()
                mode = "csv"

            logging.info(f"DATA INGESTION tamamlandı (mod: {mode})")
            logging.info("=" * 60)

            return result

        except Exception as e:
            raise CustomException(e, sys)

