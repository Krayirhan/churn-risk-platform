# ============================================================================
# conftest.py — Pytest Ortak Fixture'lar ve Konfigürasyon
# ============================================================================
# NEDEN BU DOSYA VAR?
#   pytest çalıştığında bu dosyayı otomatik bulur ve içindeki fixture'ları
#   TÜM test dosyalarına sunar. Böylece her test dosyasında aynı setup
#   kodunu tekrar yazmana gerek kalmaz.
#
# FIXTURE NEDİR?
#   Test fonksiyonlarına parametre olarak verilen hazır nesneler.
#   pytest otomatik olarak fixture'ı çalıştırır ve sonucunu teste enjekte eder.
#   @pytest.fixture dekoratörü ile tanımlanır.
#
# KULLANIM:
#   def test_something(sample_npz_data):  ← fixture adını parametre yaz, pytest halleder
#       X_train, X_test, y_train, y_test = sample_npz_data
# ============================================================================

import os
import sys
import pytest
import numpy as np
import pandas as pd

# Proje kökünü Python path'ine ekle — import'lar çalışsın diye
# Bu olmadan "from src.components..." import'ları ModuleNotFoundError verir.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ─────────────────────────────────────────────────────────────────────────────
# TEMEL FIXTURE'LAR
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def project_root() -> str:
    """
    Proje kök dizinini döndürür.
    scope="session" → tüm test oturumu boyunca 1 kez çalışır (performans).
    """
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def config_dict(project_root) -> dict:
    """
    configs/config.yaml içeriğini dict olarak döndürür.
    Testlerde dosya yollarını config'den okumak için kullanılır.
    """
    from src.utils.common import load_yaml
    return load_yaml(os.path.join(project_root, "configs", "config.yaml"))


@pytest.fixture(scope="session")
def processing_dict(project_root) -> dict:
    """
    configs/processing.yaml içeriğini dict olarak döndürür.
    """
    from src.utils.common import load_yaml
    return load_yaml(os.path.join(project_root, "configs", "processing.yaml"))


@pytest.fixture(scope="session")
def model_params_dict(project_root) -> dict:
    """
    configs/model_params.yaml içeriğini dict olarak döndürür.
    """
    from src.utils.common import load_yaml
    return load_yaml(os.path.join(project_root, "configs", "model_params.yaml"))


# ─────────────────────────────────────────────────────────────────────────────
# SENTETİK VERİ FIXTURE'LARI
# ─────────────────────────────────────────────────────────────────────────────
# NEDEN SENTETİK VERİ?
#   Unit testler gerçek veriye bağımlı OLMAMALI.
#   - Gerçek CSV değişirse testler kırılır → kırılgan test
#   - Sentetik veri ile her zaman aynı sonucu alırsın → güvenilir test
#   - Testler çok hızlı çalışır (7043 satır yerine 200 satır)

@pytest.fixture
def sample_raw_dataframe() -> pd.DataFrame:
    """
    Telco verisine benzeyen küçük sentetik DataFrame üretir.
    data_ingestion ve data_transformation testlerinde kullanılır.
    """
    np.random.seed(42)
    n = 200

    df = pd.DataFrame({
        "customerID": [f"CUST-{i:04d}" for i in range(n)],
        "gender": np.random.choice(["Male", "Female"], n),
        "SeniorCitizen": np.random.choice([0, 1], n, p=[0.84, 0.16]),
        "Partner": np.random.choice(["Yes", "No"], n),
        "Dependents": np.random.choice(["Yes", "No"], n),
        "tenure": np.random.randint(0, 73, n),
        "PhoneService": np.random.choice(["Yes", "No"], n),
        "MultipleLines": np.random.choice(["Yes", "No", "No phone service"], n),
        "InternetService": np.random.choice(["DSL", "Fiber optic", "No"], n),
        "OnlineSecurity": np.random.choice(["Yes", "No", "No internet service"], n),
        "OnlineBackup": np.random.choice(["Yes", "No", "No internet service"], n),
        "DeviceProtection": np.random.choice(["Yes", "No", "No internet service"], n),
        "TechSupport": np.random.choice(["Yes", "No", "No internet service"], n),
        "StreamingTV": np.random.choice(["Yes", "No", "No internet service"], n),
        "StreamingMovies": np.random.choice(["Yes", "No", "No internet service"], n),
        "Contract": np.random.choice(["Month-to-month", "One year", "Two year"], n),
        "PaperlessBilling": np.random.choice(["Yes", "No"], n),
        "PaymentMethod": np.random.choice([
            "Electronic check", "Mailed check",
            "Bank transfer (automatic)", "Credit card (automatic)"
        ], n),
        "MonthlyCharges": np.round(np.random.uniform(18, 118, n), 2),
        "TotalCharges": None,  # Aşağıda hesaplanacak
        "Churn": np.random.choice(["Yes", "No"], n, p=[0.27, 0.73]),
    })

    # TotalCharges ≈ tenure × MonthlyCharges (gerçekçi simülasyon)
    df["TotalCharges"] = (df["tenure"] * df["MonthlyCharges"]).round(2).astype(str)
    # Birkaç satıra boşluk koy (gerçek verideki gibi)
    df.loc[df["tenure"] == 0, "TotalCharges"] = " "

    return df


@pytest.fixture
def sample_npz_arrays() -> tuple:
    """
    Notebook'un ürettiği npz verisine benzeyen sentetik matrisler.
    model_trainer ve model_evaluation testlerinde kullanılır.

    Returns:
        (X_train, X_test, y_train, y_test) — numpy array'ler
    """
    np.random.seed(42)
    n_train, n_test, n_features = 160, 40, 30

    X_train = np.random.randn(n_train, n_features)
    X_test = np.random.randn(n_test, n_features)

    # Dengesiz hedef (%27 churn — gerçek orana yakın)
    y_train = np.random.choice([0, 1], n_train, p=[0.73, 0.27])
    y_test = np.random.choice([0, 1], n_test, p=[0.73, 0.27])

    return X_train, X_test, y_train, y_test


@pytest.fixture
def tmp_artifacts_dir(tmp_path) -> str:
    """
    Geçici artifacts klasörü oluşturur.
    tmp_path: pytest'in her test için otomatik oluşturduğu geçici dizin.
    Test bittikten sonra otomatik silinir → gerçek artifacts/ kirlenmez.
    """
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    return str(artifacts)


@pytest.fixture(scope="session")
def monitoring_dict(project_root) -> dict:
    """
    configs/monitoring.yaml içeriğini dict olarak döndürür.
    """
    from src.utils.common import load_yaml
    return load_yaml(os.path.join(project_root, "configs", "monitoring.yaml"))

