# ============================================================================
# predict_pipeline.py — Tekil Müşteri Tahmin Boru Hattı
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Eğitim tamamlandıktan sonra yeni bir müşterinin churn olasılığını
#   tahmin etmek için kullanılır. Web API (app.py) ve CLI (main.py)
#   bu dosyayı çağırır.
#
# AKIŞ:
#   Kullanıcı JSON gönderir → CustomData ile doğrulanır →
#   preprocessor.pkl ile dönüştürülür → model.pkl ile tahmin yapılır →
#   {churn_probability, risk_level, prediction} döner
#
# ÖNEMLİ KAVRAM — TRAIN vs PREDICT PREPROCESSOR:
#   Eğitimde fit_transform() yapıldı → istatistikler (mean, std, encoding haritası)
#   preprocessor.pkl'ye kaydedildi. Tahmin zamanında SADECE transform() yapılır.
#   Bu sayede "data leakage" (veri sızıntısı) önlenmiş olur.
#
# ÇAĞRILIŞ ŞEKLİ:
#   pipeline = PredictPipeline()
#   result = pipeline.predict(customer_data_dict)
#   # → {"prediction": 1, "churn_probability": 0.82, "risk_level": "Yüksek"}
# ============================================================================

import os
import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import Optional

from src.exception import CustomException
from src.logger import logging
from src.utils.common import load_object, load_yaml


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM DATA — Müşteri Verisi Doğrulama ve Dönüştürme
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CustomData:
    """
    API veya CLI'dan gelen müşteri verisini doğrulayan ve DataFrame'e
    dönüştüren veri sınıfı.

    NEDEN @dataclass?
      - Her alanın tipi ve varsayılan değeri açıkça tanımlıdır.
      - Gelen JSON otomatik olarak bu alanlara map'lenir.
      - Eksik veya hatalı alan kolayca tespit edilir.

    NEDEN VARSAYILAN DEĞERLER?
      - API'den gelen veride bazı alanlar eksik olabilir.
      - Eksik alanlara mantıklı varsayılan atanır (preprocessor zaten impute edecek).
      - Bu sayede API esnek kalır — zorunlu alanlar minimum tutulur.

    Kullanım:
        data = CustomData(tenure=24, MonthlyCharges=79.85, Contract="Month-to-month")
        df = data.to_dataframe()
    """

    # ─── ZORUNLU ALANLAR (varsayılanı olmayan) ───
    # Bu üç alan churn tahmini için en kritik olanlardır
    tenure: int = 0
    MonthlyCharges: float = 0.0
    TotalCharges: float = 0.0

    # ─── KATEGORİK ALANLAR ───
    gender: str = "Male"
    SeniorCitizen: int = 0
    Partner: str = "No"
    Dependents: str = "No"
    PhoneService: str = "Yes"
    MultipleLines: str = "No"
    InternetService: str = "Fiber optic"
    OnlineSecurity: str = "No"
    OnlineBackup: str = "No"
    DeviceProtection: str = "No"
    TechSupport: str = "No"
    StreamingTV: str = "No"
    StreamingMovies: str = "No"
    Contract: str = "Month-to-month"
    PaperlessBilling: str = "Yes"
    PaymentMethod: str = "Electronic check"

    # ─── KİMLİK (modele girmez ama trace için tutulur) ───
    customerID: str = "PREDICT_USER"

    def to_dataframe(self) -> pd.DataFrame:
        """
        CustomData'yı tek satırlık pandas DataFrame'e dönüştürür.

        NEDEN DataFrame?
          - preprocessor.pkl bir ColumnTransformer → DataFrame bekler.
          - Tek müşteri bile olsa (1, N) şeklinde matris olmalı.

        Returns:
            pd.DataFrame: (1, ~20) boyutunda tek satırlık DataFrame
        """
        data_dict = asdict(self)
        return pd.DataFrame([data_dict])

    @classmethod
    def from_dict(cls, data: dict) -> "CustomData":
        """
        Dict'ten CustomData oluşturur. Bilinmeyen key'leri sessizce yok sayar.

        NEDEN BU METOD?
          - API'den gelen JSON'da fazladan alanlar olabilir (örn: timestamp).
          - @dataclass bunları kabul etmez ve hata fırlatır.
          - Bu metod sadece tanımlı alanları alır, kalanını yok sayar.

        Args:
            data: Müşteri bilgilerini içeren dict (API body)

        Returns:
            CustomData nesnesi
        """
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


# ─────────────────────────────────────────────────────────────────────────────
# RİSK SEVİYESİ SINIFLANDIRMA
# ─────────────────────────────────────────────────────────────────────────────

def classify_risk(probability: float) -> str:
    """
    Churn olasılığını iş dünyası için anlamlı risk kategorisine çevirir.

    EŞİKLER:
      - < 0.3  → Düşük   : Müşteri muhtemelen kalacak, önlem gerekmez
      - < 0.6  → Orta    : Dikkat! Proaktif kampanya düşünülebilir
      - ≥ 0.6  → Yüksek  : Acil aksiyon! Retention ekibine yönlendir

    NEDEN BU EŞİKLER?
      - Telco verisinde churn oranı ~%27. Modelin kalibrasyonuna göre
        0.5 eşiği çoğu zaman fazla agresif olabilir.
      - 3 seviyeli risk sistemi iş birimlerinin (CRM, pazarlama) anlayacağı
        dilde sonuç üretir.

    Args:
        probability: Model çıktısı churn olasılığı (0.0–1.0)

    Returns:
        str: "Düşük", "Orta" veya "Yüksek"
    """
    if probability < 0.3:
        return "Düşük"
    elif probability < 0.6:
        return "Orta"
    else:
        return "Yüksek"


# ─────────────────────────────────────────────────────────────────────────────
# ANA TAHMİN PIPELINE'I
# ─────────────────────────────────────────────────────────────────────────────

class PredictPipeline:
    """
    Eğitilmiş modeli kullanarak tekil müşteri tahmini yapan sınıf.

    SORUMLULUKLARI:
      1. preprocessor.pkl ve model.pkl'yi diskten yükle
      2. Gelen veriyi preprocessor ile dönüştür (transform — fit DEĞİL!)
      3. Model ile tahmin yap (predict + predict_proba)
      4. Sonucu iş diline çevir (risk seviyesi)

    Kullanım:
        pipeline = PredictPipeline()
        result = pipeline.predict({"tenure": 24, "MonthlyCharges": 79.85, ...})
    """

    def __init__(self):
        self._cfg = load_yaml("configs/config.yaml")
        artifacts = self._cfg.get("artifacts", {})

        self.preprocessor_path: str = artifacts.get(
            "preprocessor_path", "artifacts/preprocessor.pkl"
        )
        self.model_path: str = artifacts.get(
            "model_path", "artifacts/model.pkl"
        )

        # Lazy loading: ilk predict çağrısında yüklenir
        self._preprocessor = None
        self._model = None

    def _load_artifacts(self) -> None:
        """
        Model ve preprocessor'ı diskten yükler (ilk çağrıda).

        NEDEN LAZY LOADING?
          - Pipeline nesnesi oluşturulduğunda artifact'lar henüz
            gerekmeyebilir (örn: health check endpoint).
          - İlk predict() çağrısında yüklenir, sonrakiler bellekten gelir.
          - Bu sayede API başlatma süresi kısalır.
        """
        if self._preprocessor is None:
            if not os.path.exists(self.preprocessor_path):
                raise FileNotFoundError(
                    f"Preprocessor bulunamadı: {self.preprocessor_path}\n"
                    f"Önce 'python main.py --train' ile eğitim yapın."
                )
            self._preprocessor = load_object(self.preprocessor_path)

        if self._model is None:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(
                    f"Model bulunamadı: {self.model_path}\n"
                    f"Önce 'python main.py --train' ile eğitim yapın."
                )
            self._model = load_object(self.model_path)

    def predict(self, input_data: dict) -> dict:
        """
        Tek bir müşteri için churn tahmini yapar.

        AKIŞ:
          1. input_data → CustomData → DataFrame (doğrulama + dönüştürme)
          2. TelcoCleaner + TelcoFeatureEngineer (CSV modunda eğitildiyse)
          3. preprocessor.transform(df) → numpy array
          4. model.predict() → 0/1 sınıf tahmini
          5. model.predict_proba() → churn olasılığı
          6. classify_risk() → "Düşük" / "Orta" / "Yüksek"

        ÖNEMLİ: NPZ modunda eğitim yapıldıysa (Mod 1), notebook'un
        preprocessor'ı kullanıldığı için burada FE adımı atlanır.
        CSV modunda eğitildiyse (Mod 2), FE burada da yapılmalıdır.

        Args:
            input_data: Müşteri bilgilerini içeren dict

        Returns:
            dict: {
                "prediction": 0 veya 1,
                "churn_probability": float (0.0–1.0),
                "risk_level": "Düşük" | "Orta" | "Yüksek",
                "customerID": str
            }
        """
        try:
            logging.info("🔮 Tahmin pipeline başlatılıyor...")

            # ─── 1. Artifact'ları yükle ───
            self._load_artifacts()

            # ─── 2. Girdi verisini hazırla ───
            customer = CustomData.from_dict(input_data)
            df = customer.to_dataframe()
            customer_id = df["customerID"].iloc[0]

            logging.info(f"  Müşteri: {customer_id}")
            logging.info(f"  Gelen alanlar: {list(input_data.keys())}")

            # ─── 3. Feature Engineering (CSV modunda eğitildiyse gerekli) ───
            # Preprocessor CSV modunda eğitildiyse, FE sütunları bekliyor olabilir.
            # Bu durumda TelcoCleaner ve TelcoFeatureEngineer'ı çalıştırıyoruz.
            # NPZ modunda eğitildiyse preprocessor zaten ham numpy bekler,
            # ama FE yine de zararsız (fazla sütunlar remainder="drop" ile atılır).
            try:
                from src.components.data_transformation import (
                    TelcoCleaner,
                    TelcoFeatureEngineer,
                    DataTransformationConfig,
                )

                df = TelcoCleaner.basic_impute(df)
                fe_config = DataTransformationConfig()
                fe = TelcoFeatureEngineer(fe_config)
                df = fe.add_features(df)
                logging.info(f"  FE sonrası sütun sayısı: {df.shape[1]}")
            except Exception as fe_err:
                logging.warning(
                    f"  ⚠ Feature Engineering atlandı (NPZ modu olabilir): {fe_err}"
                )

            # ─── 4. customerID ve Churn sütunlarını çıkar ───
            # Preprocessor bu sütunları tanımaz (remainder="drop" ile atılmıştı)
            cols_to_drop = [c for c in ["customerID", "Churn"] if c in df.columns]
            df_input = df.drop(columns=cols_to_drop)

            # ─── 5. Preprocessor ile dönüştür ───
            # ⚠ SADECE transform()! Asla fit() yapma — train'den öğrenilen
            # istatistikler (mean, std, encoding) zaten pkl'de kayıtlı.
            X = self._preprocessor.transform(df_input)

            # Sparse → dense dönüşümü (eğer gerekli ise)
            if hasattr(X, "toarray"):
                X = X.toarray()

            # ─── 6. Model ile tahmin ───
            prediction = int(self._model.predict(X)[0])

            # Olasılık tahmini (model destekliyorsa)
            churn_proba = 0.0
            try:
                proba_arr = self._model.predict_proba(X)
                churn_proba = float(proba_arr[0][1])  # P(Churn=1)
            except (AttributeError, IndexError):
                logging.warning("  ⚠ Model predict_proba desteklemiyor")
                churn_proba = float(prediction)  # Fallback: 0.0 veya 1.0

            # ─── 7. Risk seviyesi ───
            risk = classify_risk(churn_proba)

            result = {
                "prediction": prediction,
                "churn_probability": round(churn_proba, 4),
                "risk_level": risk,
                "customerID": customer_id,
            }

            logging.info(
                f"  ✅ Tahmin: {'CHURN' if prediction == 1 else 'KALACAK'} "
                f"(olasılık: {churn_proba:.2%}, risk: {risk})"
            )

            return result

        except Exception as e:
            raise CustomException(e, sys)

    def predict_batch(self, data_list: list[dict]) -> list[dict]:
        """
        Birden fazla müşteri için toplu tahmin yapar.

        NEDEN BATCH?
          - API'ye tek seferde 100 müşteri gönderilebilir.
          - Model ve preprocessor bir kere yüklenir, N kere tahmin yapılır.
          - Tek tek predict() çağırmaktan daha verimli.

        Args:
            data_list: Müşteri dict'lerinin listesi

        Returns:
            list[dict]: Her müşteri için tahmin sonucu
        """
        try:
            logging.info(f"🔮 Toplu tahmin başlatılıyor ({len(data_list)} müşteri)...")
            self._load_artifacts()

            results = []
            for i, customer_data in enumerate(data_list):
                result = self.predict(customer_data)
                results.append(result)

            churn_count = sum(1 for r in results if r["prediction"] == 1)
            logging.info(
                f"  ✅ Toplu tahmin tamamlandı: "
                f"{churn_count}/{len(results)} churn (%{100*churn_count/len(results):.1f})"
            )

            return results

        except Exception as e:
            raise CustomException(e, sys)
