# ============================================================================
# data_transformation.py — Veri Dönüştürme ve Feature Engineering Bileşeni
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Ham CSV verisini modele girebilecek hale getirir. Üç ana sorumluluğu var:
#
#   1) DATA CLEANING: TotalCharges temizliği, NaN handling (business logic)
#   2) FEATURE ENGINEERING: 10 yeni feature üretimi (notebook'tan alınmış)
#   3) PREPROCESSING: ColumnTransformer ile scaling + encoding → matris
#
# NOTEBOOK İLE İLİŞKİ:
#   Bu dosyadaki TelcoCleaner ve TelcoFeatureEngineer sınıfları, notebook'taki
#   Section 5 (Deep Cleaning) ve Section 6 (Feature Engineering) kodlarının
#   birebir production versiyonlarıdır. Kurallar processing.yaml'dan okunur.
#
# NE ZAMAN ÇALIŞIR?
#   - DataIngestion Mod 2 (Raw CSV) döndürdüğünde → tam pipeline çalışır
#   - DataIngestion Mod 1 (NPZ) döndürdüğünde → bu dosya SKIP edilir
#     (çünkü notebook zaten tüm dönüşümleri yapmış)
#
# ÇAĞRILIŞ ŞEKLİ:
#   train_pipeline.py → DataTransformation().initiate(train_df, test_df)
# ============================================================================

import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.exception import CustomException
from src.logger import logging
from src.utils.common import load_yaml, save_object


# ─────────────────────────────────────────────────────────────────────────────
# KONFİGÜRASYON
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DataTransformationConfig:
    """
    Dönüşüm sürecinin ayarları. Tüm kolon tanımları processing.yaml'dan gelir.
    """
    _cfg: dict = None
    _proc: dict = None

    def __post_init__(self):
        self._cfg = load_yaml("configs/config.yaml")
        self._proc = load_yaml("configs/processing.yaml")

        # Preprocessor'ın kaydedileceği yol (predict pipeline bunu yükleyecek)
        self.preprocessor_path: str = self._cfg.get("artifacts", {}).get(
            "preprocessor_path", "artifacts/preprocessor.pkl"
        )

        # Hedef ve kimlik sütunları
        self.target_col: str = self._cfg.get("target_col", "Churn")
        self.id_col: str = self._cfg.get("id_col", "customerID")

        # Kolon tanımları (processing.yaml'dan)
        cols = self._proc.get("columns", {})
        self.numeric_cols: list = cols.get("numeric", [])
        self.categorical_cols: list = cols.get("categorical", [])
        self.drop_cols: list = cols.get("drop", [])

        # Add-on servis sütunları (TotalAddOnServices hesabı için)
        self.addon_service_cols: list = self._proc.get("addon_service_cols", [])

        # Tenure bucket tanımları
        self.tenure_bins: list = self._proc.get("tenure_bins", [-1, 6, 12, 24, 48, 72, 1000000000])
        self.tenure_labels: list = self._proc.get("tenure_labels", [
            "0-6", "7-12", "13-24", "25-48", "49-72", "72+"
        ])

        # Preprocessing ayarları
        pp = self._proc.get("preprocessing", {})
        self.num_impute_strategy: str = pp.get("numeric_impute_strategy", "median")
        self.cat_impute_strategy: str = pp.get("categorical_impute_strategy", "most_frequent")
        self.handle_unknown: str = pp.get("handle_unknown", "ignore")


# ─────────────────────────────────────────────────────────────────────────────
# VERİ TEMİZLİK SINIFI (Notebook Section 5'in Production Versiyonu)
# ─────────────────────────────────────────────────────────────────────────────

class TelcoCleaner:
    """
    Telco verisine özgü temizlik işlemleri.
    
    NEDEN AYRI SINIF?
      - Single Responsibility: Her sınıf tek bir iş yapmalı.
      - Temizlik kuralları iş mantığına (business logic) bağlı.
      - Notebook'ta prototype edildi, burada production-grade hale getirildi.
    """

    @staticmethod
    def clean_total_charges(df: pd.DataFrame) -> pd.DataFrame:
        """
        TotalCharges sütununu temizler.
        
        PROBLEM:
          Telco CSV'sinde TotalCharges bazen " " (boş string) olarak gelir.
          pd.to_numeric() bunu NaN yapar. Ama NaN'i körlemesine median ile
          doldurmak iş mantığını bozar.
        
        BUSINESS LOGIC:
          - tenure == 0 ise → müşteri yeni, TotalCharges = 0 mantıklı
          - Diğer NaN'ler → TotalCharges ≈ MonthlyCharges × tenure (yaklaşık)
          - Bu yaklaşım da NaN üretirse → median fallback
        """
        out = df.copy()

        if "TotalCharges" not in out.columns:
            return out

        # Boşlukları NaN'a çevir, sonra sayısala zorla
        out["TotalCharges"] = out["TotalCharges"].replace(" ", np.nan)
        out["TotalCharges"] = pd.to_numeric(out["TotalCharges"], errors="coerce")

        # tenure veya MonthlyCharges yoksa klasik median imputing
        if "tenure" not in out.columns or "MonthlyCharges" not in out.columns:
            out["TotalCharges"] = out["TotalCharges"].fillna(out["TotalCharges"].median())
            return out

        tenure = pd.to_numeric(out["tenure"], errors="coerce")
        monthly = pd.to_numeric(out["MonthlyCharges"], errors="coerce")

        # Kural 1: tenure == 0 olan yeni müşteriler → TotalCharges = 0
        mask_new_customer = (tenure.fillna(0) == 0) & (out["TotalCharges"].isna())
        out.loc[mask_new_customer, "TotalCharges"] = 0.0

        # Kural 2: Kalan NaN'leri tenure × MonthlyCharges ile tahmin et
        mask_nan = out["TotalCharges"].isna()
        approx = (monthly * tenure).astype(float)

        # Kural 3: approx da NaN üretiyorsa → median fallback
        fallback = out["TotalCharges"].median()
        out.loc[mask_nan, "TotalCharges"] = approx.loc[mask_nan].fillna(fallback)

        return out

    @staticmethod
    def basic_impute(df: pd.DataFrame) -> pd.DataFrame:
        """
        Kritik temizlikleri yapar. Geri kalan eksiklikler sklearn
        SimpleImputer tarafından pipeline içinde halledilir.
        """
        out = df.copy()
        out = TelcoCleaner.clean_total_charges(out)
        return out


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE ENGINEERING SINIFI (Notebook Section 6'nın Production Versiyonu)
# ─────────────────────────────────────────────────────────────────────────────

class TelcoFeatureEngineer:
    """
    Telco verisine 10 yeni feature ekleyen sınıf.
    
    NEDEN YENİ FEATURE'LAR?
      - Ham kolonlar (tenure, MonthlyCharges) tek başına yetmez.
      - Domain knowledge ile üretilen feature'lar modelin churn sinyallerini
        daha iyi yakalamasını sağlar.
      - Notebook'ta istatistiksel testlerle (Chi-Square, Welch T-Test)
        bu feature'ların anlamlı olduğu doğrulanmıştır.
    """

    def __init__(self, config: DataTransformationConfig):
        self.config = config

    @staticmethod
    def _yes_no_to_int(series: pd.Series) -> pd.Series:
        """
        Yes/No sütunlarını 1/0'a çevirir. Farklı formatlar için güvenli dönüşüm.
        
        NEDEN GEREKLİ?
          - Bazı sütunlar "Yes"/"No", bazıları 1/0, bazıları "yes"/"no" olabilir.
          - Bu fonksiyon hepsini tutarlı hale getirir.
        """
        if series.dtype != "object":
            return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)
        return series.fillna("No").map(
            lambda x: 1 if str(x).strip().lower() == "yes" else 0
        ).astype(int)

    def add_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        10 yeni feature üretir. Her biri aşağıda açıklanmıştır.
        
        Returns:
            DataFrame: Orijinal + 10 yeni sütun eklenmiş veri
        """
        out = df.copy()

        # Sayısal sütunları güvenli dönüştür (object → numeric)
        for col in ["tenure", "MonthlyCharges", "TotalCharges"]:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce")

        # ─── FEATURE 1: LoyaltyIndex ─────────────────────────
        # log1p(tenure) → Logaritmik sadakat indeksi
        # NEDEN LOG? tenure 0-72 arasında, dağılımı sağa çarpık.
        # log1p ile dağılımı normalize ederiz. +1 ile log(0) hatasını önleriz.
        if "tenure" in out.columns:
            out["LoyaltyIndex"] = np.log1p(out["tenure"].fillna(0))

        # ─── FEATURE 2: TotalAddOnServices ───────────────────
        # Müşterinin aldığı ek hizmet sayısı (0-6 arası)
        # NEDEN? Çok hizmet alan müşteri daha "bağlı" → düşük churn.
        existing_addons = [c for c in self.config.addon_service_cols if c in out.columns]
        if existing_addons:
            addon_sum = sum(self._yes_no_to_int(out[c]) for c in existing_addons)
            out["TotalAddOnServices"] = addon_sum.astype(int)
        else:
            out["TotalAddOnServices"] = 0

        # ─── FEATURE 3: UnitCost ─────────────────────────────
        # MonthlyCharges / (TotalAddOnServices + 1)
        # NEDEN? Hizmet başına düşen maliyet. Yüksek = değer algısı düşük → churn.
        if "MonthlyCharges" in out.columns:
            out["UnitCost"] = (
                out["MonthlyCharges"].fillna(out["MonthlyCharges"].median())
                / (out["TotalAddOnServices"] + 1)
            )

        # ─── FEATURE 4: AvgPaidPerMonth ──────────────────────
        # TotalCharges / (tenure + 1)
        # NEDEN? Gerçek aylık ortalama ödeme. MonthlyCharges'tan farklı olabilir
        # (kampanyalar, fiyat değişiklikleri yüzünden).
        if "TotalCharges" in out.columns and "tenure" in out.columns:
            out["AvgPaidPerMonth"] = out["TotalCharges"] / (out["tenure"].fillna(0) + 1)

            # ─── FEATURE 5: ChargeGap ────────────────────────
            # |MonthlyCharges - AvgPaidPerMonth|
            # NEDEN? Fark büyükse fiyat tutarsızlığı var → müşteri memnuniyetsiz → churn.
            if "MonthlyCharges" in out.columns:
                out["ChargeGap"] = (out["MonthlyCharges"] - out["AvgPaidPerMonth"]).abs()

        # ─── FEATURE 6: RiskScope_Fiber_NoSupport_NoSec ──────
        # Fiber internet VAR ama TechSupport ve OnlineSecurity YOK
        # NEDEN? Bu kombinasyon notebook'taki chi-square testinde en yüksek
        # churn korelasyonunu göstermiş. Fiber pahalı → destek yok → kızgın müşteri.
        risk_cols = ["InternetService", "TechSupport", "OnlineSecurity"]
        if all(c in out.columns for c in risk_cols):
            is_fiber = out["InternetService"].fillna("").astype(str).str.lower().str.contains("fiber")
            no_support = out["TechSupport"].fillna("No").astype(str).str.lower().eq("no")
            no_sec = out["OnlineSecurity"].fillna("No").astype(str).str.lower().eq("no")
            out["RiskScope_Fiber_NoSupport_NoSec"] = (is_fiber & no_support & no_sec).astype(int)
        else:
            out["RiskScope_Fiber_NoSupport_NoSec"] = 0

        # ─── FEATURE 7: IsMonthToMonth ──────────────────────
        # Sözleşme tipi month-to-month mı?
        # NEDEN? Aylık sözleşme = istediği zaman çıkabilir → en yüksek churn grubu.
        if "Contract" in out.columns:
            out["IsMonthToMonth"] = (
                out["Contract"].fillna("").astype(str).str.lower().str.contains("month").astype(int)
            )
        else:
            out["IsMonthToMonth"] = 0

        # ─── FEATURE 8: IsPaperless ─────────────────────────
        # Kağıtsız fatura kullanıyor mu?
        # NEDEN? Dijital müşteri profili → daha az sadık olabilir (dijital çağ).
        if "PaperlessBilling" in out.columns:
            out["IsPaperless"] = self._yes_no_to_int(out["PaperlessBilling"])
        else:
            out["IsPaperless"] = 0

        # ─── FEATURE 9: IsElectronicCheck ────────────────────
        # Electronic check ile mi ödüyor?
        # NEDEN? Notebook'taki chi-square testinde electronic check ödeyenlerde
        # churn oranı diğer ödeme yöntemlerinden belirgin şekilde yüksek çıkmış.
        if "PaymentMethod" in out.columns:
            out["IsElectronicCheck"] = (
                out["PaymentMethod"].fillna("").astype(str).str.lower()
                .str.contains("electronic").astype(int)
            )
        else:
            out["IsElectronicCheck"] = 0

        # ─── FEATURE 10: TenureBucket ───────────────────────
        # tenure'u segmentlere ayır: 0-6, 7-12, 13-24, 25-48, 49-72, 72+
        # NEDEN? Sürekli değişken yerine kategorik segment → non-linear ilişkileri
        # yakalar. Özellikle ağaç modelleri için faydalı olmasa da 
        # lojistik regresyon için çok yararlı.
        if "tenure" in out.columns:
            out["TenureBucket"] = pd.cut(
                out["tenure"].fillna(0),
                bins=self.config.tenure_bins,
                labels=self.config.tenure_labels
            ).astype(str)

        return out


# ─────────────────────────────────────────────────────────────────────────────
# ANA DÖNÜŞÜM SINIFI
# ─────────────────────────────────────────────────────────────────────────────

class DataTransformation:
    """
    Tam dönüşüm pipeline'ını yöneten ana sınıf.
    Cleaning → Feature Engineering → Preprocessing (ColumnTransformer)
    
    ÇIKTI:
      - train_arr: Eğitim matrisi (numpy array) — modele girmeye hazır
      - test_arr: Test matrisi (numpy array)
      - preprocessor.pkl: Fit edilmiş ColumnTransformer (canlı sistemde kullanılacak)
    """

    def __init__(self):
        self.config = DataTransformationConfig()

    def _build_preprocessor(self, df: pd.DataFrame) -> ColumnTransformer:
        """
        Preprocessing pipeline'ını oluşturur.
        
        NEDEN ColumnTransformer?
          - Farklı sütun tiplerine farklı işlemler uygular.
          - Sayısal: Imputer(median) → StandardScaler
          - Kategorik: Imputer(most_frequent) → OneHotEncoder
          - Tek bir .fit_transform() çağrısı ile tüm dönüşümler yapılır.
          - Sonra .pkl olarak kaydedilir → canlı sistemde aynı dönüşüm uygulanır.
        
        Args:
            df: Feature engineering sonrası DataFrame (hangi sütunlar var diye bakılır)
        
        Returns:
            ColumnTransformer nesnesi (henüz fit EDİLMEMİŞ)
        """
        try:
            # Feature engineering sonrası mevcut sütunları belirle
            # Config'deki kolon listeleri + engineered features'ın kesişimi
            available_cols = set(df.columns)

            # Sayısal sütunlar: config'dekiler + engineered numerics
            engineered_numerics = [
                "LoyaltyIndex", "TotalAddOnServices", "UnitCost",
                "AvgPaidPerMonth", "ChargeGap", "RiskScope_Fiber_NoSupport_NoSec",
                "IsMonthToMonth", "IsPaperless", "IsElectronicCheck"
            ]
            num_cols = [
                c for c in (self.config.numeric_cols + engineered_numerics)
                if c in available_cols
            ]

            # Kategorik sütunlar: config'dekiler + TenureBucket
            engineered_categoricals = ["TenureBucket"]
            cat_cols = [
                c for c in (self.config.categorical_cols + engineered_categoricals)
                if c in available_cols
            ]

            # Drop edilmesi gerekenler (target, id) çıkar
            exclude = set(self.config.drop_cols + [self.config.target_col, self.config.id_col])
            num_cols = [c for c in num_cols if c not in exclude]
            cat_cols = [c for c in cat_cols if c not in exclude]

            logging.info(f"  Sayısal sütunlar ({len(num_cols)}): {num_cols}")
            logging.info(f"  Kategorik sütunlar ({len(cat_cols)}): {cat_cols}")

            # --- SAYISAL PIPELINE ---
            # 1. SimpleImputer(median): Eksik değerleri medyan ile doldur
            #    NEDEN MEDYAN? Ortalama aykırı değerlere hassas, medyan dayanıklı.
            # 2. StandardScaler: Z-score normalizasyonu (mean=0, std=1)
            #    NEDEN? LogReg ve SVM mesafe bazlı → ölçek farkı bias yaratır.
            num_pipeline = Pipeline(steps=[
                ("imputer", SimpleImputer(strategy=self.config.num_impute_strategy)),
                ("scaler", StandardScaler())
            ])

            # --- KATEGORİK PIPELINE ---
            # 1. SimpleImputer(most_frequent): Eksik değeri en sık görülen ile doldur
            # 2. OneHotEncoder: Kategorikleri binary vektöre çevir
            #    handle_unknown="ignore": Eğitimde görülmeyen kategori gelirse → sıfır vektör
            #    NEDEN? Canlı sistemde yeni bir PaymentMethod gelebilir → hata vermesin.
            # 3. StandardScaler(with_mean=False): Seyrek (sparse) matriste ortalama
            #    çıkarma yapılamaz, bu yüzden with_mean=False.
            cat_pipeline = Pipeline(steps=[
                ("imputer", SimpleImputer(strategy=self.config.cat_impute_strategy)),
                ("onehot", OneHotEncoder(handle_unknown=self.config.handle_unknown)),
                ("scaler", StandardScaler(with_mean=False))
            ])

            # --- BİRLEŞTİRME ---
            # ColumnTransformer her pipeline'ı ilgili sütunlara uygular
            # remainder="drop": Tanımlanmayan sütunları (customerID vb.) at
            preprocessor = ColumnTransformer(
                transformers=[
                    ("num", num_pipeline, num_cols),
                    ("cat", cat_pipeline, cat_cols)
                ],
                remainder="drop"
            )

            return preprocessor

        except Exception as e:
            raise CustomException(e, sys)

    def initiate(self, train_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple:
        """
        Tam dönüşüm pipeline'ını çalıştırır.
        
        AKIŞ:
          1. TelcoCleaner.basic_impute() → TotalCharges temizliği
          2. TelcoFeatureEngineer.add_features() → 10 yeni feature
          3. ColumnTransformer.fit_transform(train) → Eğitim matrisini oluştur
          4. ColumnTransformer.transform(test) → Test matrisini oluştur
             ⚠ DİKKAT: Test verisine SADECE transform! Asla fit yapılmaz!
          5. preprocessor.pkl kaydet
        
        Args:
            train_df: Eğitim DataFrame'i (data_ingestion'dan gelir)
            test_df: Test DataFrame'i
        
        Returns:
            (train_arr, test_arr, preprocessor_path) tuple'ı
        """
        try:
            logging.info("=" * 60)
            logging.info("DATA TRANSFORMATION başlatılıyor...")
            logging.info("=" * 60)

            # ─── ADIM 1: Temizlik ───
            logging.info("Adım 1/4: Veri temizliği (TelcoCleaner)...")
            train_df = TelcoCleaner.basic_impute(train_df)
            test_df = TelcoCleaner.basic_impute(test_df)

            # ─── ADIM 2: Feature Engineering ───
            logging.info("Adım 2/4: Feature Engineering (10 yeni feature)...")
            fe = TelcoFeatureEngineer(self.config)
            train_df = fe.add_features(train_df)
            test_df = fe.add_features(test_df)
            logging.info(f"  FE sonrası sütun sayısı: {train_df.shape[1]}")

            # ─── ADIM 3: X/y ayırımı ───
            logging.info("Adım 3/4: Girdi (X) ve Hedef (y) ayrımı...")

            # Hedef değişkeni ayır
            y_train = train_df[self.config.target_col].values
            y_test = test_df[self.config.target_col].values

            # Drop edilecek sütunları çıkar (target + id)
            cols_to_drop = [
                c for c in [self.config.target_col, self.config.id_col]
                if c in train_df.columns
            ]
            X_train_df = train_df.drop(columns=cols_to_drop)
            X_test_df = test_df.drop(columns=cols_to_drop)

            # ─── ADIM 4: Preprocessing (ColumnTransformer) ───
            logging.info("Adım 4/4: Preprocessing (Scaling + Encoding)...")
            preprocessor = self._build_preprocessor(X_train_df)

            # ⚠ KRİTİK KURAL:
            # fit_transform → SADECE train verisine (model train'den öğrenir)
            # transform → test verisine (train'den öğrenilmiş kuralları uygular)
            # Bu ayrım "data leakage" (veri sızıntısı) önlemenin en temel kuralıdır!
            X_train_arr = preprocessor.fit_transform(X_train_df)
            X_test_arr = preprocessor.transform(X_test_df)

            # Sparse matrix ise dense'e çevir (bazı modeller sparse desteklemez)
            if hasattr(X_train_arr, "toarray"):
                X_train_arr = X_train_arr.toarray()
            if hasattr(X_test_arr, "toarray"):
                X_test_arr = X_test_arr.toarray()

            logging.info(f"  Train matris: {X_train_arr.shape} | Test matris: {X_test_arr.shape}")

            # ─── Preprocessor'ı Kaydet ───
            # Bu .pkl dosyası canlı sistemde yeni gelen veriyi aynı şekilde
            # dönüştürmek için kullanılacak (predict_pipeline.py).
            save_object(self.config.preprocessor_path, preprocessor)

            logging.info("DATA TRANSFORMATION tamamlandı.")
            logging.info("=" * 60)

            return X_train_arr, X_test_arr, y_train, y_test, self.config.preprocessor_path

        except Exception as e:
            raise CustomException(e, sys)

