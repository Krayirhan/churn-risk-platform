// ============================================================================
// app.js — Dashboard JavaScript Mantığı
// ============================================================================
// AMAÇ: C# API ile iletişim ve kullanıcı etkileşimleri
// ============================================================================

// ─────────────────────────────────────────────────────────────────────────────
// API AYARLARI
// ─────────────────────────────────────────────────────────────────────────────
const API_CONFIG = {
    // Runtime override: set window.CHURN_API_BASE_URL before loading this script
    // or pass via Docker env → template substitution in index.html
    BASE_URL: window.CHURN_API_BASE_URL || 'http://localhost:5001/api/churn',
    TIMEOUT: 30000,
    // Runtime override: set window.CHURN_API_KEY for authenticated requests
    API_KEY: window.CHURN_API_KEY || ''
};

/**
 * Build common headers for API requests.
 * Includes X-API-Key if configured.
 */
function getHeaders(contentType) {
    const headers = {};
    if (contentType) headers['Content-Type'] = contentType;
    if (API_CONFIG.API_KEY) headers['X-API-Key'] = API_CONFIG.API_KEY;
    return headers;
}

// ─────────────────────────────────────────────────────────────────────────────
// SAYFA YÜKLENİNCE ÇALIŞACAKLAR
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Churn Risk Dashboard Yüklendi');
    
    // Sistem durumunu kontrol et
    checkSystemHealth();
    
    // Form submit olayını dinle
    const form = document.getElementById('predictionForm');
    form.addEventListener('submit', handlePrediction);
    
    // Rastgele örnek butonu
    const randomBtn = document.getElementById('randomExampleBtn');
    if (randomBtn) {
        randomBtn.addEventListener('click', generateRandomExample);
    }
    
    // Her 30 saniyede bir sistem durumunu güncelle
    setInterval(checkSystemHealth, 30000);
});

// ─────────────────────────────────────────────────────────────────────────────
// SİSTEM SAĞLIK KONTROLÜ
// ─────────────────────────────────────────────────────────────────────────────
async function checkSystemHealth() {
    try {
        // Model durumunu kontrol et
        const healthResponse = await fetch(`${API_CONFIG.BASE_URL}/health`, { headers: getHeaders() });
        const healthData = await healthResponse.json();
        
        updateHealthStatus(healthData);
        
        // Model bilgilerini al
        const modelResponse = await fetch(`${API_CONFIG.BASE_URL}/model-info`, { headers: getHeaders() });
        const modelData = await modelResponse.json();
        
        updateModelInfo(modelData);
        
        // Drift durumunu kontrol et (opsiyonel)
        try {
            const driftResponse = await fetch(`${API_CONFIG.BASE_URL}/drift`, { headers: getHeaders() });
            const driftData = await driftResponse.json();
            updateDriftStatus(driftData);
        } catch (error) {
            console.log('Drift verisi alınamadı:', error.message);
        }
        
    } catch (error) {
        console.error('Sistem durumu kontrol hatası:', error);
        showError('Sistem bağlantı hatası. Lütfen backend servislerin çalıştığından emin olun.');
        
        // Hata durumunda UI'ı güncelle
        document.getElementById('modelStatus').innerHTML = 
            '<span style="color: var(--danger-color);">❌ Bağlantı Yok</span>';
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// SAĞLIK DURUMU GÜNCELLEMESİ
// ─────────────────────────────────────────────────────────────────────────────
function updateHealthStatus(data) {
    const statusElement = document.getElementById('modelStatus');
    const updateElement = document.getElementById('lastUpdate');
    
    if (data.status === 'healthy' || data.modelLoaded) {
        statusElement.innerHTML = '✅ Aktif ve Hazır';
        statusElement.style.color = 'var(--success-color)';
    } else {
        statusElement.innerHTML = '⚠️ Model Yüklenmedi';
        statusElement.style.color = 'var(--warning-color)';
    }
    
    const now = new Date();
    updateElement.textContent = now.toLocaleTimeString('tr-TR');
}

// ─────────────────────────────────────────────────────────────────────────────
// MODEL BİLGİLERİ GÜNCELLEMESİ
// ─────────────────────────────────────────────────────────────────────────────
function updateModelInfo(data) {
    const accuracyValue = data?.metrics?.accuracy ?? data?.accuracy;
    if (typeof accuracyValue === 'number') {
        const accuracy = (accuracyValue * 100).toFixed(2);
        document.getElementById('modelAccuracy').textContent = `%${accuracy}`;
    }
    // Model adını dinamik güncelle
    const modelName = data?.model_name ?? data?.modelName ?? data?.metrics?.model_name;
    if (modelName) {
        document.getElementById('activeModelName').textContent = modelName;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// DRIFT DURUMU GÜNCELLEMESİ
// ─────────────────────────────────────────────────────────────────────────────
function updateDriftStatus(data) {
    const driftElement = document.getElementById('driftStatus');

    const driftDetected = data?.driftDetected ?? data?.drift_detected;
    if (driftDetected) {
        driftElement.innerHTML = '⚠️ Drift Tespit Edildi';
        driftElement.style.color = 'var(--warning-color)';
    } else {
        driftElement.innerHTML = '✅ Normal';
        driftElement.style.color = 'var(--success-color)';
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// TAHMİN İŞLEMİ
// ─────────────────────────────────────────────────────────────────────────────
async function handlePrediction(event) {
    event.preventDefault();
    
    // Sonuç alanını göster ve loading durumuna getir
    showLoadingResult();
    
    try {
        // Form verilerini topla
        const customerData = getFormData();
        
        console.log('📤 Tahmin isteği gönderiliyor:', customerData);
        
        // API'ye istek gönder
        const response = await fetch(`${API_CONFIG.BASE_URL}/predict`, {
            method: 'POST',
            headers: getHeaders('application/json'),
            body: JSON.stringify(customerData)
        });
        
        if (!response.ok) {
            throw new Error(`API Hatası: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('📥 Tahmin sonucu:', result);
        
        // Sonucu göster
        displayResult(result);
        
        // Bugünkü tahmin sayısını artır
        incrementTodayPredictions();
        
    } catch (error) {
        console.error('Tahmin hatası:', error);
        showError('Tahmin yapılırken bir hata oluştu: ' + error.message);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// FORM VERİLERİNİ TOPLA
// ─────────────────────────────────────────────────────────────────────────────
function getFormData() {
    return {
        gender: document.getElementById('gender').value,
        seniorCitizen: parseInt(document.getElementById('seniorCitizen').value),
        partner: document.getElementById('partner').value,
        dependents: document.getElementById('dependents').value,
        tenure: parseInt(document.getElementById('tenure').value),
        phoneService: document.getElementById('phoneService').value,
        multipleLines: document.getElementById('multipleLines').value,
        internetService: document.getElementById('internetService').value,
        onlineSecurity: document.getElementById('onlineSecurity').value,
        onlineBackup: document.getElementById('onlineBackup').value,
        deviceProtection: document.getElementById('deviceProtection').value,
        techSupport: document.getElementById('techSupport').value,
        streamingTV: document.getElementById('streamingTV').value,
        streamingMovies: document.getElementById('streamingMovies').value,
        contract: document.getElementById('contract').value,
        paperlessBilling: document.getElementById('paperlessBilling').value,
        paymentMethod: document.getElementById('paymentMethod').value,
        monthlyCharges: parseFloat(document.getElementById('monthlyCharges').value),
        totalCharges: parseFloat(document.getElementById('totalCharges').value)
    };
}

// ─────────────────────────────────────────────────────────────────────────────
// LOADING DURUMUNU GÖSTER
// ─────────────────────────────────────────────────────────────────────────────
function showLoadingResult() {
    const resultSection = document.getElementById('resultSection');
    const resultMain = document.querySelector('.result-main');
    const resultIcon = document.getElementById('resultIcon');
    const resultTitle = document.getElementById('resultTitle');
    const resultDescription = document.getElementById('resultDescription');
    
    resultSection.style.display = 'block';
    resultMain.className = 'result-main';
    resultIcon.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    resultTitle.textContent = 'Tahmin Yapılıyor...';
    resultDescription.textContent = 'Model çalışıyor, lütfen bekleyiniz';
    
    // Detayları gizle
    document.getElementById('resultDetails').innerHTML = '';
    
    // Sonuca scroll et
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ─────────────────────────────────────────────────────────────────────────────
// SONUCU GÖSTER
// ─────────────────────────────────────────────────────────────────────────────
function displayResult(result) {
    const resultMain = document.querySelector('.result-main');
    const resultIcon = document.getElementById('resultIcon');
    const resultTitle = document.getElementById('resultTitle');
    const resultDescription = document.getElementById('resultDescription');
    const resultDetails = document.getElementById('resultDetails');
    
    // Tahmin sonucuna göre renk ve ikon belirle
    let statusClass, iconClass, title, description;
    
    const predictionValue = typeof result.prediction === 'string'
        ? result.prediction.toLowerCase()
        : result.prediction;
    const riskLevelRaw = result.riskLevel ?? result.risk_level ?? '';
    const riskLevel = normalizeRiskLevel(riskLevelRaw);
    const isChurn = predictionValue === 1 || predictionValue === 'yes' || predictionValue === 'evet';

    if (isChurn) {
        // Müşteri kaybı riski yüksek
        if (riskLevel === 'HIGH') {
            statusClass = 'danger';
            iconClass = 'fa-exclamation-triangle';
            title = '⚠️ YÜKSEK RİSK - Müşteri Kayıp İhtimali Yüksek!';
            description = 'Bu müşteri için acil önlem alınması önerilir.';
        } else {
            statusClass = 'warning';
            iconClass = 'fa-exclamation-circle';
            title = '⚡ ORTA RİSK - Müşteri Kayıp İhtimali Var';
            description = 'Bu müşteri için önleyici aksiyonlar düşünülmelidir.';
        }
    } else {
        // Müşteri kayıp riski düşük
        statusClass = 'success';
        iconClass = 'fa-check-circle';
        title = '✅ DÜŞÜK RİSK - Müşteri Sadık';
        description = 'Bu müşterinin kayıp ihtimali düşüktür.';
    }
    
    resultMain.className = `result-main ${statusClass}`;
    resultIcon.className = `result-icon ${statusClass}`;
    resultIcon.innerHTML = `<i class="fas ${iconClass}"></i>`;
    resultTitle.textContent = title;
    resultDescription.textContent = description;
    
    // Detaylı bilgileri göster
    const churnProbability = result.churnProbability ?? result.churn_probability ?? 0;
    const probability = (churnProbability * 100).toFixed(1);
    // Gerçek güven skoru: modelin kararsızlıktan (P=0.5) ne kadar uzak olduğu
    // Formül: (max(P, 1-P) - 0.5) * 2  →  P=0.5'te %0, P=0 veya P=1'de %100
    const maxP = Math.max(churnProbability, 1 - churnProbability);
    const confidence = ((maxP - 0.5) * 2 * 100).toFixed(1);
    const modelVersion = result.modelVersion ?? result.model_version ?? 'N/A';
    
    resultDetails.innerHTML = `
        <div class="detail-item">
            <h4>Kayıp Olasılığı</h4>
            <p>${probability}%</p>
        </div>
        <div class="detail-item">
            <h4>Risk Seviyesi</h4>
            <p>${translateRiskLevel(riskLevelRaw)}</p>
        </div>
        <div class="detail-item">
            <h4>Güven Skoru</h4>
            <p>${confidence}%</p>
        </div>
        <div class="detail-item">
            <h4>Model</h4>
            <p>${modelVersion}</p>
        </div>
    `;
}

// ─────────────────────────────────────────────────────────────────────────────
// HATA MESAJI GÖSTER
// ─────────────────────────────────────────────────────────────────────────────
function showError(message) {
    const resultSection = document.getElementById('resultSection');
    const resultMain = document.querySelector('.result-main');
    const resultIcon = document.getElementById('resultIcon');
    const resultTitle = document.getElementById('resultTitle');
    const resultDescription = document.getElementById('resultDescription');
    
    resultSection.style.display = 'block';
    resultMain.className = 'result-main danger';
    resultIcon.className = 'result-icon danger';
    resultIcon.innerHTML = '<i class="fas fa-times-circle"></i>';
    resultTitle.textContent = '❌ Hata Oluştu';
    resultDescription.textContent = message;
    
    document.getElementById('resultDetails').innerHTML = '';
    
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ─────────────────────────────────────────────────────────────────────────────
// YARDIMCI FONKSİYONLAR
// ─────────────────────────────────────────────────────────────────────────────
function translateRiskLevel(level) {
    const normalized = normalizeRiskLevel(level);
    const translations = {
        'LOW': 'Düşük',
        'MEDIUM': 'Orta',
        'HIGH': 'Yüksek'
    };
    return translations[normalized] || level;
}

function normalizeRiskLevel(level) {
    if (!level) return '';

    const value = String(level).trim().toLowerCase();
    if (value === 'low' || value === 'düşük' || value === 'dusuk') return 'LOW';
    if (value === 'medium' || value === 'orta') return 'MEDIUM';
    if (value === 'high' || value === 'yüksek' || value === 'yuksek') return 'HIGH';

    return String(level).toUpperCase();
}

function incrementTodayPredictions() {
    const element = document.getElementById('todayPredictions');
    let current = parseInt(element.textContent) || 0;
    element.textContent = current + 1;
}

function resetForm() {
    document.getElementById('predictionForm').reset();
    document.getElementById('resultSection').style.display = 'none';
}

// ─────────────────────────────────────────────────────────────────────────────
// RASTGELE ÖRNEK OLUŞTURUCU
// ─────────────────────────────────────────────────────────────────────────────
function generateRandomExample() {
    const randomData = {
        gender: Math.random() > 0.5 ? 'Male' : 'Female',
        seniorCitizen: Math.random() > 0.8 ? '1' : '0',
        partner: Math.random() > 0.5 ? 'Yes' : 'No',
        dependents: Math.random() > 0.3 ? 'No' : 'Yes',
        tenure: Math.floor(Math.random() * 72) + 1,
        phoneService: Math.random() > 0.1 ? 'Yes' : 'No',
        multipleLines: ['No', 'Yes', 'No phone service'][Math.floor(Math.random() * 3)],
        internetService: ['DSL', 'Fiber optic', 'No'][Math.floor(Math.random() * 3)],
        onlineSecurity: ['No', 'Yes', 'No internet service'][Math.floor(Math.random() * 3)],
        onlineBackup: ['No', 'Yes', 'No internet service'][Math.floor(Math.random() * 3)],
        deviceProtection: ['No', 'Yes', 'No internet service'][Math.floor(Math.random() * 3)],
        techSupport: ['No', 'Yes', 'No internet service'][Math.floor(Math.random() * 3)],
        streamingTV: ['No', 'Yes', 'No internet service'][Math.floor(Math.random() * 3)],
        streamingMovies: ['No', 'Yes', 'No internet service'][Math.floor(Math.random() * 3)],
        contract: ['Month-to-month', 'One year', 'Two year'][Math.floor(Math.random() * 3)],
        paperlessBilling: Math.random() > 0.4 ? 'Yes' : 'No',
        paymentMethod: ['Electronic check', 'Mailed check', 'Bank transfer (automatic)', 'Credit card (automatic)'][Math.floor(Math.random() * 4)],
        monthlyCharges: (Math.random() * 100 + 20).toFixed(2),
        totalCharges: (Math.random() * 8000 + 100).toFixed(2)
    };

    // Form alanlarını doldur
    document.getElementById('gender').value = randomData.gender;
    document.getElementById('seniorCitizen').value = randomData.seniorCitizen;
    document.getElementById('partner').value = randomData.partner;
    document.getElementById('dependents').value = randomData.dependents;
    document.getElementById('tenure').value = randomData.tenure;
    document.getElementById('phoneService').value = randomData.phoneService;
    document.getElementById('multipleLines').value = randomData.multipleLines;
    document.getElementById('internetService').value = randomData.internetService;
    document.getElementById('onlineSecurity').value = randomData.onlineSecurity;
    document.getElementById('onlineBackup').value = randomData.onlineBackup;
    document.getElementById('deviceProtection').value = randomData.deviceProtection;
    document.getElementById('techSupport').value = randomData.techSupport;
    document.getElementById('streamingTV').value = randomData.streamingTV;
    document.getElementById('streamingMovies').value = randomData.streamingMovies;
    document.getElementById('contract').value = randomData.contract;
    document.getElementById('paperlessBilling').value = randomData.paperlessBilling;
    document.getElementById('paymentMethod').value = randomData.paymentMethod;
    document.getElementById('monthlyCharges').value = randomData.monthlyCharges;
    document.getElementById('totalCharges').value = randomData.totalCharges;

    // Başarı mesajı göster
    showNotification('🎲 Rastgele örnek oluşturuldu!', 'success');
}

// Bildirim gösterme fonksiyonu
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#27ae60' : '#3498db'};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease;
        display: flex;
        align-items: center;
        gap: 10px;
    `;
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ─────────────────────────────────────────────────────────────────────────────
// NAVİGASYON
// ─────────────────────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        
        // Aktif linki değiştir
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        this.classList.add('active');
        
        // Sayfa değiştirme mantığı buraya eklenebilir (gelecek için)
        console.log('Navigasyon:', this.getAttribute('href'));
    });
});

// ─────────────────────────────────────────────────────────────────────────────
// CONSOLE BANNER
// ─────────────────────────────────────────────────────────────────────────────
console.log('%c🚀 CHURN RISK PLATFORM', 'color: #2563eb; font-size: 24px; font-weight: bold;');
console.log('%cTelco Müşteri Kayıp Tahmin Sistemi', 'color: #64748b; font-size: 14px;');
console.log('%cPowered by Machine Learning & AI', 'color: #10b981; font-size: 12px;');
console.log('');
console.log('Dashboard hazır! API Endpoint:', API_CONFIG.BASE_URL);
