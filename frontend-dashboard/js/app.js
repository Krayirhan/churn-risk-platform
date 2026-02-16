// ============================================================================
// app.js — Dashboard JavaScript Mantığı
// ============================================================================
// AMAÇ: C# API ile iletişim ve kullanıcı etkileşimleri
// ============================================================================

// ─────────────────────────────────────────────────────────────────────────────
// API AYARLARI
// ─────────────────────────────────────────────────────────────────────────────
const API_CONFIG = {
    BASE_URL: 'http://localhost:5001/api/churn',
    TIMEOUT: 30000
};

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
    
    // Her 30 saniyede bir sistem durumunu güncelle
    setInterval(checkSystemHealth, 30000);
});

// ─────────────────────────────────────────────────────────────────────────────
// SİSTEM SAĞLIK KONTROLÜ
// ─────────────────────────────────────────────────────────────────────────────
async function checkSystemHealth() {
    try {
        // Model durumunu kontrol et
        const healthResponse = await fetch(`${API_CONFIG.BASE_URL}/health`);
        const healthData = await healthResponse.json();
        
        updateHealthStatus(healthData);
        
        // Model bilgilerini al
        const modelResponse = await fetch(`${API_CONFIG.BASE_URL}/model-info`);
        const modelData = await modelResponse.json();
        
        updateModelInfo(modelData);
        
        // Drift durumunu kontrol et (opsiyonel)
        try {
            const driftResponse = await fetch(`${API_CONFIG.BASE_URL}/drift`);
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
    if (data.metrics && data.metrics.accuracy) {
        const accuracy = (data.metrics.accuracy * 100).toFixed(2);
        document.getElementById('modelAccuracy').textContent = `%${accuracy}`;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// DRIFT DURUMU GÜNCELLEMESİ
// ─────────────────────────────────────────────────────────────────────────────
function updateDriftStatus(data) {
    const driftElement = document.getElementById('driftStatus');
    
    if (data.driftDetected) {
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
            headers: {
                'Content-Type': 'application/json'
            },
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
    
    if (result.prediction === 'Yes' || result.prediction === 'Evet') {
        // Müşteri kaybı riski yüksek
        if (result.riskLevel === 'HIGH') {
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
    const probability = (result.churnProbability * 100).toFixed(1);
    const confidence = (result.confidence * 100).toFixed(1);
    
    resultDetails.innerHTML = `
        <div class="detail-item">
            <h4>Kayıp Olasılığı</h4>
            <p>${probability}%</p>
        </div>
        <div class="detail-item">
            <h4>Risk Seviyesi</h4>
            <p>${translateRiskLevel(result.riskLevel)}</p>
        </div>
        <div class="detail-item">
            <h4>Güven Skoru</h4>
            <p>${confidence}%</p>
        </div>
        <div class="detail-item">
            <h4>Model Versiyonu</h4>
            <p>${result.modelVersion}</p>
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
    const translations = {
        'LOW': 'Düşük',
        'MEDIUM': 'Orta',
        'HIGH': 'Yüksek'
    };
    return translations[level] || level;
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
