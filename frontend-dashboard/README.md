# Frontend Dashboard - Kullanım Kılavuzu

## 📋 Genel Bakış

Basit, anlaşılır ve kullanıcı dostu müşteri churn tahmin dashboard'u. Çalışanların kolayca kullanabileceği şekilde tasarlanmıştır.

## 🏗️ Dosya Yapısı

```
frontend-dashboard/
├── index.html          # Ana sayfa
├── css/
│   └── style.css      # Tüm stiller
└── js/
    └── app.js         # JavaScript mantığı
```

## 🚀 Nasıl Çalıştırılır?

### Yöntem 1: Live Server (Önerilen)

1. VS Code'da **Live Server** eklentisini kurun
2. `index.html` dosyasına sağ tıklayın
3. "Open with Live Server" seçin
4. Tarayıcıda otomatik açılacaktır: `http://localhost:5500`

### Yöntem 2: Python HTTP Server

```bash
cd frontend-dashboard
python -m http.server 5500
```

Tarayıcıda açın: `http://localhost:5500`

### Yöntem 3: Direkt Dosya

`index.html` dosyasını çift tıklayarak açabilirsiniz (ancak API bağlantısı için sunucu gereklidir).

## 🎯 Kullanım

### 1. Sistem Durumunu Kontrol Edin

Dashboard açıldığında üstteki 4 kart sistem durumunu gösterir:
- ✅ **Model Durumu**: Model hazır mı?
- 📊 **Model Doğruluğu**: Modelin başarı oranı
- ⚠️ **Drift Durumu**: Veri kalitesi takibi
- 👥 **Bugün Tahmin**: Yapılan tahmin sayısı

### 2. Müşteri Bilgilerini Girin

Formdaki tüm alanları doldurun:

**Kişisel Bilgiler**:
- Cinsiyet
- Yaşlı Vatandaş (65+ yaş)
- Partner durumu
- Bakmakla yükümlü olduğu kişi var mı?

**Hizmet Bilgileri**:
- Müşteri süresi (kaç aydır müşteri)
- Telefon hizmeti
- İnternet hizmeti türü
- Ek hizmetler (güvenlik, yedekleme, TV, film vb.)

**Finansal Bilgiler**:
- Aylık ücret (TL)
- Toplam ödenen tutar (TL)
- Sözleşme türü (aylık, yıllık)
- Ödeme yöntemi

### 3. Tahmin Yapın

"Tahmin Yap" butonuna tıklayın. Sistem:
1. Verileri C# backend'e gönderir
2. C# backend Python API'yi çağırır
3. Model tahmini yapar
4. Sonucu güzel bir şekilde gösterir

### 4. Sonuçları Değerlendirin

Sonuç 3 renkte gösterilir:

🟢 **Yeşil (Düşük Risk)**: Müşteri sadık, kayıp ihtimali düşük
🟠 **Turuncu (Orta Risk)**: Dikkat! Önleyici aksiyonlar düşünün
🔴 **Kırmızı (Yüksek Risk)**: Acil önlem alın!

Detaylar:
- **Kayıp Olasılığı**: %0-100 arası skor
- **Risk Seviyesi**: Düşük / Orta / Yüksek
- **Güven Skoru**: Modelin ne kadar emin olduğu
- **Model Versiyonu**: Kullanılan model sürümü

## 🎨 Görsel Özellikler

### Renkler
- 🔵 **Mavi**: Ana tema rengi (butonlar, başlıklar)
- 🟢 **Yeşil**: Başarı, düşük risk
- 🟠 **Turuncu**: Uyarı, dikkat
- 🔴 **Kırmızı**: Tehlike, yüksek risk
- 🟣 **Mor**: İstatistikler

### İkonlar
Font Awesome ikonu kullanılır - anlaşılır ve profesyonel

### Responsive Tasarım
Mobil, tablet ve masaüstünde düzgün görünür

## ⚙️ Ayarlar

### API Adresi Değiştirme

`js/app.js` dosyasında runtime override desteklenir:

```javascript
// Varsayılan ayarlar — runtime'da override edilebilir
const API_CONFIG = {
    BASE_URL: window.CHURN_API_BASE_URL || 'http://localhost:5001/api/churn',
    TIMEOUT: 30000,
    API_KEY: window.CHURN_API_KEY || ''
};
```

Override için `index.html`'de script tag'inden önce:

```html
<script>
  window.CHURN_API_BASE_URL = 'https://api.example.com/api/churn';
  window.CHURN_API_KEY = 'your-secret-key';
</script>
```

### Otomatik Güncelleme Süresi

Varsayılan olarak her 30 saniyede bir sistem durumu güncellenir:

```javascript
// 30000 = 30 saniye
setInterval(checkSystemHealth, 30000);
```

## 🐛 Sorun Giderme

### Problem: "Sistem bağlantı hatası"

**Nedenler**:
1. Python backend çalışmıyor
2. C# backend çalışmıyor
3. CORS sorunu

**Çözüm**:
```bash
# 1. Python backend'i başlat
cd churn-risk-platform
python main.py --serve

# 2. C# backend'i başlat
cd backend-csharp
dotnet run

# 3. Frontend'i başlat
cd frontend-dashboard
# Live Server ile aç
```

### Problem: Formda hata

**Çözüm**: Tüm alanların doldurulduğundan emin olun. Kırmızı kenarlıklı alanlar zorunludur.

### Problem: Sayfa yüklenmiyor

**Çözüm**: Tarayıcı konsolunu açın (F12) ve hataları kontrol edin.

## 📱 Tarayıcı Desteği

- ✅ Chrome (önerilen)
- ✅ Firefox
- ✅ Edge
- ✅ Safari

## 🎓 Kullanıcı Eğitimi

### Yeni Çalışanlar İçin

1. **İlk Giriş**: Üstteki durumu kartlarını kontrol edin
2. **Tek Müşteri Test**: Bir örnek müşteri girin
3. **Sonuçları Anla**: Renk kodlarını öğrenin
4. **Aksiyonlar**: Risk seviyesine göre ne yapacağınızı belirleyin

### Örnek Senaryo

**Durum**: Müşteri 3 aydır müşterimiz, aylık 100 TL ödüyor, hiçbir ek hizmet almıyor, aylık sözleşmesi var.

**Tahmin**: Muhtemelen YÜKSEK RİSK çıkacak

**Aksiyon**: 
- Özel kampanya sunun
- 1-2 yıllık sözleşmeye geçiş öner
- Ek hizmet paketleri tanıtın
- Müşteri temsilcisi arasın

## 📞 Destek

Dashboard ile ilgili sorunlar için:
- Tarayıcı konsolunu kontrol edin (F12)
- Backend servislerin çalıştığını doğrulayın
- Network sekmesinden API isteklerini inceleyin
