# C# Backend API - Kullanım Kılavuzu

## 📋 Genel Bakış

Bu C# .NET 8.0 backend, Python FastAPI servisi ile frontend dashboard arasında köprü görevi görür. Basit ve anlaşılır bir yapıya sahiptir.

## 🏗️ Proje Yapısı

```
backend-csharp/
├── Controllers/
│   └── ChurnController.cs      # API endpoint'leri
├── Models/
│   ├── CustomerRequest.cs      # Müşteri veri modeli
│   └── PredictionResponse.cs   # Tahmin sonuç modeli
├── Services/
│   └── PythonApiService.cs     # Python API iletişim servisi
├── Program.cs                   # Uygulama giriş noktası
├── appsettings.json            # Konfigürasyon
└── ChurnRiskAPI.csproj         # Proje dosyası
```

## 🚀 Kurulum

### Gereksinimler

- .NET 8.0 SDK
- Visual Studio 2022 veya VS Code

### Adım 1: Projeyi Derle

```bash
cd backend-csharp
dotnet restore
dotnet build
```

### Adım 2: Çalıştır

```bash
dotnet run
```

Backend **http://localhost:5001** adresinde başlayacaktır.

## 📡 API Endpoint'leri

### 1. Karşılama Mesajı
```
GET /api/churn
```

### 2. Müşteri Tahmin
```
POST /api/churn/predict
Content-Type: application/json

{
  "gender": "Female",
  "seniorCitizen": 0,
  "partner": "Yes",
  "dependents": "No",
  "tenure": 12,
  "phoneService": "Yes",
  "multipleLines": "No",
  "internetService": "Fiber optic",
  "onlineSecurity": "No",
  "onlineBackup": "Yes",
  "deviceProtection": "No",
  "techSupport": "No",
  "streamingTV": "Yes",
  "streamingMovies": "No",
  "contract": "Month-to-month",
  "paperlessBilling": "Yes",
  "paymentMethod": "Electronic check",
  "monthlyCharges": 70.35,
  "totalCharges": 1397.48
}
```

### 3. Model Bilgileri
```
GET /api/churn/model-info
```

### 4. Sağlık Kontrolü
```
GET /api/churn/health
```

### 5. Drift Durumu
```
GET /api/churn/drift
```

## ⚙️ Konfigürasyon

`appsettings.json` dosyasından Python API adresini değiştirebilirsiniz:

```json
{
  "PythonAPI": {
    "BaseUrl": "http://localhost:8000",
    "TimeoutSeconds": 30
  }
}
```

## 🔧 Geliştirme

### Yeni Endpoint Ekleme

1. `Controllers/ChurnController.cs` dosyasına yeni method ekleyin:

```csharp
[HttpGet("yeni-endpoint")]
public async Task<IActionResult> YeniEndpoint()
{
    // İşlemler
    return Ok(result);
}
```

### Yeni Servis Ekleme

1. `Services/` klasörüne yeni servis sınıfı oluşturun
2. `Program.cs` içinde servisi kaydedin:

```csharp
builder.Services.AddScoped<YeniServis>();
```

## 🐛 Sorun Giderme

### Problem: CORS Hatası

**Çözüm**: `Program.cs` içinde CORS policy'ye frontend URL'inizi ekleyin:

```csharp
policy.WithOrigins("http://localhost:3000", "http://localhost:5500")
```

### Problem: Python API'ye Bağlanamıyor

**Çözüm**: 
1. Python backend'in çalıştığından emin olun (`python main.py --serve`)
2. `appsettings.json` içindeki URL'i kontrol edin

## 📚 Swagger Dokümantasyonu

Backend çalıştığında Swagger UI'a şuradan erişebilirsiniz:
```
http://localhost:5001/swagger
```

## 🎯 Örnek Kullanım

### PowerShell ile Test

```powershell
# Model bilgisi al
Invoke-RestMethod -Uri "http://localhost:5001/api/churn/model-info" -Method GET

# Tahmin yap
$body = @{
    gender = "Female"
    seniorCitizen = 0
    tenure = 12
    # ... diğer alanlar
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5001/api/churn/predict" `
    -Method POST -Body $body -ContentType "application/json"
```

## 📞 Destek

Sorun yaşarsanız:
- Logları kontrol edin (konsol çıktısı)
- Python backend'in çalıştığından emin olun
- CORS ayarlarını kontrol edin
