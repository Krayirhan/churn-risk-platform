# ============================================================================
# app.py — FastAPI REST API Uygulaması
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Eğitilmiş modeli HTTP API olarak dışa açar. Herhangi bir frontend,
#   mobil uygulama veya başka bir servis bu API'yi çağırarak churn
#   tahmini yapabilir.
#
# ENDPOINT'LER:
#   GET  /              → Karşılama mesajı
#   GET  /health        → Servis sağlık kontrolü (model yüklü mü?)
#   GET  /model-info    → Aktif modelin metrikleri
#   POST /predict       → Tekil müşteri tahmini
#   POST /predict/batch → Toplu müşteri tahmini
#
# BAŞLATMA:
#   python main.py --serve
#   veya: uvicorn app:app --host 0.0.0.0 --port 8000
#   Docs: http://localhost:8000/docs (Swagger UI)
#
# NEDEN FASTAPI?
#   - Otomatik OpenAPI/Swagger dokümantasyonu
#   - Pydantic ile güçlü input validation
#   - Async desteği (yüksek eşzamanlılık)
#   - Tip güvenliği (type hints → doğrulama + kod tamamlama)
# ============================================================================

import os
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.logger import logging


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELLER — Input / Output Doğrulama Şemaları
# ─────────────────────────────────────────────────────────────────────────────

class CustomerInput(BaseModel):
    """
    Tekil müşteri tahmini için giriş şeması.

    NEDEN PYDANTIC?
      - Gelen JSON otomatik olarak doğrulanır (tip, aralık, zorunluluk).
      - Hatalı girdi 422 Unprocessable Entity ile reddedilir.
      - Swagger UI'da otomatik form oluşturulur.
      - Varsayılan değerler API'yi esnek tutar (sadece birkaç alan yeterli).

    ÖNEMLİ:
      - Field tanımlarındaki description'lar Swagger UI'da görünür.
      - ge/le (greater/less than or equal) ile sayısal sınırlar konur.
    """

    # ─── Sayısal alanlar ───
    tenure: int = Field(
        default=0, ge=0, le=72,
        description="Müşterinin kaç aydır abone olduğu (0-72)"
    )
    MonthlyCharges: float = Field(
        default=0.0, ge=0,
        description="Aylık fatura tutarı ($)"
    )
    TotalCharges: float = Field(
        default=0.0, ge=0,
        description="Toplam ödenen tutar ($)"
    )

    # ─── Demografik alanlar ───
    gender: str = Field(default="Male", description="Cinsiyet: Male / Female")
    SeniorCitizen: int = Field(
        default=0, ge=0, le=1,
        description="65 yaş üstü mü? (0=Hayır, 1=Evet)"
    )
    Partner: str = Field(default="No", description="Partneri var mı? Yes / No")
    Dependents: str = Field(default="No", description="Bakmakla yükümlü biri var mı? Yes / No")

    # ─── Hizmet alanları ───
    PhoneService: str = Field(default="Yes", description="Telefon hizmeti: Yes / No")
    MultipleLines: str = Field(
        default="No",
        description="Birden fazla hat: Yes / No / No phone service"
    )
    InternetService: str = Field(
        default="Fiber optic",
        description="İnternet tipi: DSL / Fiber optic / No"
    )
    OnlineSecurity: str = Field(default="No", description="Online güvenlik: Yes / No")
    OnlineBackup: str = Field(default="No", description="Online yedekleme: Yes / No")
    DeviceProtection: str = Field(default="No", description="Cihaz koruma: Yes / No")
    TechSupport: str = Field(default="No", description="Teknik destek: Yes / No")
    StreamingTV: str = Field(default="No", description="TV streaming: Yes / No")
    StreamingMovies: str = Field(default="No", description="Film streaming: Yes / No")

    # ─── Sözleşme ve ödeme ───
    Contract: str = Field(
        default="Month-to-month",
        description="Sözleşme tipi: Month-to-month / One year / Two year"
    )
    PaperlessBilling: str = Field(default="Yes", description="Kağıtsız fatura: Yes / No")
    PaymentMethod: str = Field(
        default="Electronic check",
        description="Ödeme yöntemi: Electronic check / Mailed check / Bank transfer / Credit card"
    )

    # ─── Kimlik (opsiyonel) ───
    customerID: Optional[str] = Field(
        default="API_USER",
        description="Müşteri kimliği (opsiyonel, izleme amaçlı)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tenure": 2,
                    "MonthlyCharges": 89.10,
                    "TotalCharges": 178.20,
                    "Contract": "Month-to-month",
                    "InternetService": "Fiber optic",
                    "OnlineSecurity": "No",
                    "TechSupport": "No",
                    "PaymentMethod": "Electronic check",
                    "PaperlessBilling": "Yes",
                }
            ]
        }
    }


class PredictionOutput(BaseModel):
    """
    Tahmin sonucu çıkış şeması.

    API'nin döndüğü JSON yapısı Swagger UI'da belgelenir.
    """
    prediction: int = Field(description="Tahmin: 0=Kalacak, 1=Churn")
    churn_probability: float = Field(description="Churn olasılığı (0.0–1.0)")
    risk_level: str = Field(description="Risk seviyesi: Düşük / Orta / Yüksek")
    customerID: str = Field(description="Müşteri kimliği")


class BatchInput(BaseModel):
    """Toplu tahmin giriş şeması."""
    customers: list[CustomerInput] = Field(
        description="Müşteri listesi (en fazla 100)"
    )


class BatchOutput(BaseModel):
    """Toplu tahmin çıkış şeması."""
    predictions: list[PredictionOutput]
    total: int = Field(description="Toplam müşteri sayısı")
    churn_count: int = Field(description="Churn tahmin edilen sayısı")
    churn_rate: float = Field(description="Churn oranı (%)")


class HealthOutput(BaseModel):
    """Sağlık kontrolü çıkış şeması."""
    status: str
    model_loaded: bool
    preprocessor_loaded: bool
    artifacts_exist: bool


class ModelInfoOutput(BaseModel):
    """Model bilgisi çıkış şeması."""
    model_name: str
    accuracy: Optional[float] = None
    f1: Optional[float] = None
    recall: Optional[float] = None
    precision: Optional[float] = None
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE SINGLETON — Tekil Pipeline Nesnesi
# ─────────────────────────────────────────────────────────────────────────────
# NEDEN SINGLETON?
#   - Her istek için model ve preprocessor'ı diskten yüklemek pahalı.
#   - Uygulama başlatıldığında BİR KERE yüklenir, bellekte tutulur.
#   - Tüm istekler aynı pipeline nesnesini paylaşır.

_pipeline = None


def get_pipeline():
    """Lazy-loaded pipeline singleton döndürür."""
    global _pipeline
    if _pipeline is None:
        from src.pipeline.predict_pipeline import PredictPipeline
        _pipeline = PredictPipeline()
    return _pipeline


# ─────────────────────────────────────────────────────────────────────────────
# LIFESPAN — Uygulama Yaşam Döngüsü Yönetimi
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Uygulama başlatılırken pipeline'ı önceden yükler (warm-up).

    NEDEN LIFESPAN?
      - İlk isteğin yavaş olmasını önler (cold start problemi).
      - Startup'ta model/preprocessor yoksa erken uyarı verir.
      - Shutdown'da temizlik yapılabilir (gelecekte log flush vb.).
    """
    logging.info("🚀 FastAPI uygulaması başlatılıyor...")

    # Model ve preprocessor'ı önceden yüklemeyi dene
    try:
        pipeline = get_pipeline()
        pipeline._load_artifacts()
        logging.info("  ✅ Model ve preprocessor başarıyla yüklendi (warm-up)")
    except FileNotFoundError as e:
        logging.warning(f"  ⚠ Artifact bulunamadı (eğitim yapılmamış olabilir): {e}")
    except Exception as e:
        logging.warning(f"  ⚠ Warm-up sırasında hata: {e}")

    yield  # Uygulama burada çalışır

    logging.info("🛑 FastAPI uygulaması kapatılıyor...")


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI UYGULAMASI
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Telco Churn Risk Platform API",
    description=(
        "Telco müşterilerinin churn (ayrılma) riskini tahmin eden REST API.\n\n"
        "**Özellikler:**\n"
        "- Tekil ve toplu müşteri tahmini\n"
        "- Risk seviyesi sınıflandırma (Düşük / Orta / Yüksek)\n"
        "- Model performans metrikleri sorgulama\n"
        "- Sağlık kontrolü endpoint'i"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS Middleware ───
# NEDEN CORS?
#   - Frontend (React, Vue vb.) farklı port'tan API'ye istek atar.
#   - CORS olmadan tarayıcı bu istekleri engeller.
#   - allow_origins=["*"] → tüm origin'lere izin (prod'da kısıtlanmalı!).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Production'da spesifik domain'ler yazılmalı
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT'LER
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Genel"])
async def root():
    """
    Karşılama mesajı. API'nin çalıştığını doğrulamak için.
    """
    return {
        "message": "Telco Churn Risk Platform API 🚀",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthOutput, tags=["Genel"])
async def health_check():
    """
    Servis sağlık kontrolü.

    Model ve preprocessor dosyalarının varlığını kontrol eder.
    Kubernetes veya load balancer'lar bu endpoint'i kullanır.
    """
    cfg_path = "configs/config.yaml"
    model_exists = os.path.exists("artifacts/model.pkl")
    pp_exists = os.path.exists("artifacts/preprocessor.pkl")

    return HealthOutput(
        status="healthy" if (model_exists and pp_exists) else "degraded",
        model_loaded=model_exists,
        preprocessor_loaded=pp_exists,
        artifacts_exist=model_exists and pp_exists,
    )


@app.get("/model-info", response_model=ModelInfoOutput, tags=["Model"])
async def model_info():
    """
    Aktif modelin performans metriklerini döndürür.

    artifacts/metrics.json dosyasından okur.
    """
    metrics_path = "artifacts/metrics.json"
    if not os.path.exists(metrics_path):
        raise HTTPException(
            status_code=404,
            detail="Henüz eğitilmiş model bulunamadı. Önce eğitim yapın.",
        )

    from src.utils.common import load_json

    data = load_json(metrics_path)
    m = data.get("metrics", {})

    return ModelInfoOutput(
        model_name=data.get("model_name", "unknown"),
        accuracy=m.get("accuracy"),
        f1=m.get("f1"),
        recall=m.get("recall"),
        precision=m.get("precision"),
        roc_auc=m.get("roc_auc"),
        pr_auc=m.get("pr_auc"),
    )


@app.post("/predict", response_model=PredictionOutput, tags=["Tahmin"])
async def predict_single(customer: CustomerInput):
    """
    Tekil müşteri için churn tahmini yapar.

    **Giriş:** Müşteri bilgileri (JSON body)
    **Çıkış:** Tahmin sonucu, olasılık ve risk seviyesi

    Tüm alanların varsayılan değerleri vardır — sadece bildiğiniz alanları
    göndermeniz yeterlidir. Minimum: tenure, MonthlyCharges, Contract.
    """
    try:
        pipeline = get_pipeline()
        result = pipeline.predict(customer.model_dump())
        return PredictionOutput(**result)

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Model henüz yüklenmedi. Önce eğitim yapın: {str(e)}",
        )
    except Exception as e:
        logging.error(f"Tahmin hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Tahmin hatası: {str(e)}")


@app.post("/predict/batch", response_model=BatchOutput, tags=["Tahmin"])
async def predict_batch(batch: BatchInput):
    """
    Birden fazla müşteri için toplu churn tahmini yapar.

    **Giriş:** Müşteri listesi (max 100)
    **Çıkış:** Her müşteri için tahmin + özet istatistikler

    Toplu tahmin tekil çağrılardan daha verimlidir çünkü model ve
    preprocessor sadece bir kere yüklenir.
    """
    if len(batch.customers) > 100:
        raise HTTPException(
            status_code=400,
            detail="Tek seferde en fazla 100 müşteri gönderilebilir.",
        )

    try:
        pipeline = get_pipeline()
        data_list = [c.model_dump() for c in batch.customers]
        results = pipeline.predict_batch(data_list)

        predictions = [PredictionOutput(**r) for r in results]
        churn_count = sum(1 for r in results if r["prediction"] == 1)

        return BatchOutput(
            predictions=predictions,
            total=len(results),
            churn_count=churn_count,
            churn_rate=round(100 * churn_count / len(results), 2) if results else 0.0,
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Model henüz yüklenmedi: {str(e)}",
        )
    except Exception as e:
        logging.error(f"Toplu tahmin hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Tahmin hatası: {str(e)}")
