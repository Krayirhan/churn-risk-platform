# ============================================================================
# Makefile — Sık Kullanılan Komutlar için Kısayollar
# ============================================================================
# NEDEN BU DOSYA?
#   Tüm ekip aynı komutları kullanır. Yeni geliştiriciler projeye hızlı girer.
#   Windows'ta `make` yoksa: choco install make  veya  winget install GnuWin32.Make
#
# KULLANIM:
#   make help        → Tüm komutları listele
#   make install     → Bağımlılıkları kur
#   make test        → Testleri çalıştır
#   make lint        → Kod kalitesi kontrolü
#   make train       → Model eğitimi
#   make serve       → API sunucusunu başlat
#   make docker-up   → Docker ile başlat
#   make clean       → Geçici dosyaları temizle
# ============================================================================

.PHONY: help install install-dev test test-cov lint format train serve \
        docker-build docker-up docker-down docker-train clean

# Varsayılan hedef
.DEFAULT_GOAL := help

# ─── RENKLER ───
BLUE  := \033[36m
GREEN := \033[32m
RESET := \033[0m

# ──────────────────────────────────────────────────────────────
# HELP — Otomatik yardım menüsü
# ──────────────────────────────────────────────────────────────
help: ## 📋 Kullanılabilir komutları listele
	@echo ""
	@echo "$(BLUE)Churn Risk Platform — Komutlar$(RESET)"
	@echo "────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-16s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ──────────────────────────────────────────────────────────────
# INSTALL — Bağımlılık kurulumu
# ──────────────────────────────────────────────────────────────
install: ## 📦 Production bağımlılıklarını kur
	pip install --upgrade pip
	pip install -r requirements.txt

install-dev: ## 📦 Dev bağımlılıklarını kur (test, lint, format)
	pip install --upgrade pip
	pip install -r requirements-dev.txt
	pre-commit install

# ──────────────────────────────────────────────────────────────
# TEST — Testler
# ──────────────────────────────────────────────────────────────
test: ## 🧪 Tüm testleri çalıştır
	pytest tests/ -v --tb=short

test-cov: ## 🧪 Testleri coverage ile çalıştır
	pytest tests/ -v --tb=short \
		--cov=src --cov=app \
		--cov-report=term-missing \
		--cov-report=html:htmlcov

test-unit: ## 🧪 Sadece unit testleri çalıştır
	pytest tests/unit/ -v --tb=short

test-integration: ## 🧪 Sadece integration testleri çalıştır
	pytest tests/integration/ -v --tb=short

# ──────────────────────────────────────────────────────────────
# LINT & FORMAT — Kod kalitesi
# ──────────────────────────────────────────────────────────────
lint: ## 🧹 flake8 ile lint kontrolü
	flake8 src/ app.py main.py \
		--max-line-length=120 \
		--extend-ignore=E501,W503,E203,W291,W293,W391 \
		--statistics --count

format: ## 🎨 black + isort ile otomatik formatlama
	isort src/ tests/ app.py main.py
	black src/ tests/ app.py main.py --line-length 120

format-check: ## 🎨 Format uyumluluğunu kontrol et (değiştirme)
	isort --check-only src/ tests/ app.py main.py
	black --check src/ tests/ app.py main.py --line-length 120

# ──────────────────────────────────────────────────────────────
# ML — Eğitim ve tahmin
# ──────────────────────────────────────────────────────────────
train: ## 🎯 Model eğitimini başlat
	python main.py --train

serve: ## 🚀 FastAPI sunucusunu başlat (localhost:8000)
	python main.py --serve

info: ## ℹ️  Aktif model bilgilerini göster
	python main.py --info

# ──────────────────────────────────────────────────────────────
# DOCKER — Konteyner işlemleri
# ──────────────────────────────────────────────────────────────
docker-build: ## 🐳 Docker image build et
	docker build -t churn-risk-platform:latest .

docker-up: ## 🐳 Docker Compose ile API'yi başlat
	docker-compose up --build -d

docker-down: ## 🐳 Docker Compose servislerini durdur
	docker-compose down

docker-train: ## 🐳 Docker içinde model eğitimi
	docker-compose run --rm python-backend python main.py --train

docker-logs: ## 🐳 Container loglarını göster
	docker-compose logs -f python-backend

# ──────────────────────────────────────────────────────────────
# CLEAN — Temizlik (Linux/macOS + Windows uyumlu)
# ──────────────────────────────────────────────────────────────
clean: ## 🧹 Geçici dosyaları temizle
ifeq ($(OS),Windows_NT)
	powershell -NoProfile -Command "Get-ChildItem -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	powershell -NoProfile -Command "Get-ChildItem -Recurse -Directory -Filter '.pytest_cache' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	powershell -NoProfile -Command "Get-ChildItem -Recurse -Directory -Filter '*.egg-info' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	powershell -NoProfile -Command "Remove-Item -Recurse -Force -ErrorAction SilentlyContinue htmlcov,.coverage,coverage.xml,test-results.xml,dist,build"
else
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage coverage.xml test-results.xml dist build
endif
	@echo "✅ Temizlik tamamlandı"
