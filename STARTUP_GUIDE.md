# 🚀 Sistem Başlatma Kılavuzu

## Tüm Servisleri Başlatma

Churn Risk Platform 3 ana bileşenden oluşur:
1. **Python FastAPI Backend** (ML modeli)
2. **C# .NET Backend** (API katmanı)
3. **Frontend Dashboard** (Kullanıcı arayüzü)

---

## 📋 Adım Adım Başlatma

### 1️⃣ Python Backend'i Başlat

```bash
# Terminal 1
cd D:\churn-risk-platform

# Virtual environment'ı aktifleştir
.venv\Scripts\Activate.ps1

# Servisi başlat
python main.py --serve
```

✅ **Kontrol**: http://localhost:8000/health
✅ **Swagger**: http://localhost:8000/docs

---

### 2️⃣ C# Backend'i Başlat

```bash
# Terminal 2
cd D:\churn-risk-platform\backend-csharp

# Çalıştır
dotnet run
```

✅ **Kontrol**: http://localhost:5001/api/churn
✅ **Swagger**: http://localhost:5001/swagger

---

### 3️⃣ Frontend Dashboard'u Başlat

**Yöntem A: Live Server (VS Code)**
1. VS Code'da `frontend-dashboard/index.html` dosyasını açın
2. Sağ tıklayın → "Open with Live Server"

**Yöntem B: Python HTTP Server**
```bash
# Terminal 3
cd D:\churn-risk-platform\frontend-dashboard
python -m http.server 5500
```

✅ **Kontrol**: http://localhost:5500

---

## 🎯 Hızlı Test

### Sistem Durumu Kontrolü

```powershell
# Python API
Invoke-RestMethod http://localhost:8000/health

# C# API
Invoke-RestMethod http://localhost:5001/api/churn/health
```

### Örnek Tahmin

```powershell
$customer = @{
    gender = "Female"
    seniorCitizen = 0
    partner = "Yes"
    dependents = "No"
    tenure = 12
    phoneService = "Yes"
    multipleLines = "No"
    internetService = "Fiber optic"
    onlineSecurity = "No"
    onlineBackup = "Yes"
    deviceProtection = "No"
    techSupport = "No"
    streamingTV = "Yes"
    streamingMovies = "No"
    contract = "Month-to-month"
    paperlessBilling = "Yes"
    paymentMethod = "Electronic check"
    monthlyCharges = 70.35
    totalCharges = 1397.48
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5001/api/churn/predict" `
    -Method POST -Body $customer -ContentType "application/json"
```

---

## 🔄 Mimari Akış

```
┌─────────────────┐
│   FRONTEND      │
│   Dashboard     │  http://localhost:5500
│  (HTML/CSS/JS)  │
└────────┬────────┘
         │
         │ HTTP Request
         ▼
┌─────────────────┐
│   C# BACKEND    │
│   .NET API      │  http://localhost:5001
│  (API Gateway)  │
└────────┬────────┘
         │
         │ HTTP Request
         ▼
┌─────────────────┐
│  PYTHON BACKEND │
│   FastAPI       │  http://localhost:8000
│  (ML Model)     │
└─────────────────┘
```

---

## 🐛 Sorun Giderme

### Python Backend Hatası

```bash
# Model yoksa önce eğitin
python main.py --train

# Tekrar başlatın
python main.py --serve
```

### C# Backend Hatası

```bash
# Dependency'leri restore edin
cd backend-csharp
dotnet restore
dotnet build
dotnet run
```

### Frontend CORS Hatası

`backend-csharp/Program.cs` içinde frontend URL'i eklenmiş mi kontrol edin:
```csharp
policy.WithOrigins("http://localhost:5500")
```

---

## 📊 Port Listesi

| Servis | Port | URL |
|--------|------|-----|
| Python API | 8000 | http://localhost:8000 |
| C# API | 5001 | http://localhost:5001 |
| Frontend | 5500 | http://localhost:5500 |

---

## 🎬 Demo Video (Opsiyonel)

1. Tüm servisleri başlatın
2. Frontend'i açın: http://localhost:5500
3. Üstteki durumu kartlarını kontrol edin (hepsi yeşil olmalı)
4. Örnek bir müşteri bilgisi girin
5. "Tahmin Yap" butonuna tıklayın
6. Sonucu görüntüleyin

---

## 🛑 Servisleri Durdurma

Tüm terminal pencerelerinde:
- **Windows**: `Ctrl + C`
- **Linux/Mac**: `Ctrl + C`

---

## 📝 Notlar

- İlk kullanımda model eğitimini yapın: `python main.py --train`
- Her servis kendi terminalinde çalışmalıdır
- Frontend'in API'lere erişebilmesi için backend'ler çalışır olmalıdır
- CORS sorunu yaşarsanız C# backend ayarlarını kontrol edin

---

## 🎉 Başarılı Kurulum

Eğer:
- ✅ http://localhost:8000/health → "healthy"
- ✅ http://localhost:5001/api/churn → JSON mesaj
- ✅ http://localhost:5500 → Dashboard açılıyor
- ✅ Dashboard'da tahmin yapabiliyorsunuz

Tebrikler! Sistem tam çalışır durumda! 🚀
