# ============================================================================
# Dockerfile — Çok Aşamalı (Multi-Stage) Production Build
# ============================================================================
# NEDEN MULTI-STAGE?
#   1. builder  → Bağımlılıkları derler, test çalıştırır.
#   2. runtime  → Sadece çalışma-zamanı dosyalarını kopyalar.
#   Sonuç: ~400 MB yerine ~250 MB imaj, saldırı yüzeyi küçülür.
#
# BUILD:
#   docker build -t churn-risk-platform:latest .
#
# RUN:
#   docker run -p 8000:8000 churn-risk-platform:latest
#   docker run churn-risk-platform:latest python main.py --train
#
# COMPOSE:
#   docker-compose up --build
# ============================================================================

# ──────────────────────────────────────────────────────────────
# STAGE 1: Builder — bağımlılık kurulumu ve wheel derleme
# ──────────────────────────────────────────────────────────────
FROM python:3.10-slim AS builder

# Sistem bağımlılıkları (derleme için gerekli C kütüphaneleri)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Önce sadece requirements.txt kopyala → Docker cache'ten faydalanır
COPY requirements.txt .

# pip wheel ile derlenmiş paketleri /wheels dizinine topla
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ──────────────────────────────────────────────────────────────
# STAGE 2: Runtime — minimal production imajı
# ──────────────────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

# Meta bilgiler
LABEL maintainer="DS Team <dev@churn-risk-platform.com>"
LABEL description="Telco Customer Churn Risk Platform — FastAPI Serving"
LABEL version="0.1.0"

# Güvenlik: root olmayan kullanıcı
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --create-home appuser

WORKDIR /app

# Builder'dan derlenmiş wheel'ları kur
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels requirements.txt

# Proje dosyalarını kopyala (sırayla — cache dostu)
COPY configs/ ./configs/
COPY src/ ./src/
COPY app.py main.py setup.py ./

# Paketi editable modda kur (src/ import'ları çalışsın)
RUN pip install --no-cache-dir -e .

# Artifact ve data dizinlerini oluştur (volume mount noktaları)
RUN mkdir -p artifacts data/raw logs models && \
    chown -R appuser:appuser /app

# Root olmayan kullanıcıya geç
USER appuser

# Health-check: /health endpoint'i 200 dönmeli
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# FastAPI sunucusu
EXPOSE 8000

# Varsayılan komut: serve modu
# Override: docker run <image> python main.py --train
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
