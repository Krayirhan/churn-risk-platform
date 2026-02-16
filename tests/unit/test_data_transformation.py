# ============================================================================
# test_data_transformation.py — DataTransformation Sınıfı için Unit Testler
# ============================================================================
# TEST EDİLEN SINIFLAR:
#   - TelcoCleaner: TotalCharges temizliği, business logic imputing
#   - TelcoFeatureEngineer: 10 yeni feature üretimi
#   - DataTransformation: Tam dönüşüm pipeline'ı (ColumnTransformer)
#
# TEST PRENSİBİ:
#   Her sınıf AYRI test edilir (Single Responsibility).
#   TelcoCleaner testleri TelcoFeatureEngineer'a bağımlı DEĞİL.
# ============================================================================

import os
import pytest
import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# TelcoCleaner Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestTelcoCleaner:
    """Veri temizliği işlemlerinin doğruluğunu test eder."""

    def test_total_charges_space_converted_to_numeric(self, sample_raw_dataframe):
        """TotalCharges'taki boşluklar (' ') sayıya dönüştürülmeli."""
        from src.components.data_transformation import TelcoCleaner

        df = sample_raw_dataframe.copy()
        # Boşluk olan satırlar var (tenure=0 olanlar)
        assert (df["TotalCharges"] == " ").any(), "Test verisi boşluk içermeli"

        cleaned = TelcoCleaner.basic_impute(df)

        # Temizlik sonrası TotalCharges sayısal olmalı
        assert pd.api.types.is_numeric_dtype(cleaned["TotalCharges"]), \
            "TotalCharges hala numeric değil!"

    def test_total_charges_no_nan_after_cleaning(self, sample_raw_dataframe):
        """Temizlik sonrası TotalCharges'ta NaN kalmamalı."""
        from src.components.data_transformation import TelcoCleaner

        df = sample_raw_dataframe.copy()
        cleaned = TelcoCleaner.basic_impute(df)

        nan_count = cleaned["TotalCharges"].isna().sum()
        assert nan_count == 0, f"TotalCharges'ta {nan_count} NaN kaldı!"

    def test_tenure_zero_gets_total_charges_zero(self, sample_raw_dataframe):
        """tenure=0 olan müşterilerin TotalCharges'ı 0 olmalı (business rule)."""
        from src.components.data_transformation import TelcoCleaner

        df = sample_raw_dataframe.copy()
        cleaned = TelcoCleaner.basic_impute(df)

        # tenure=0 ve TotalCharges=" " olan satırlar → TotalCharges=0 olmalı
        mask = df["tenure"] == 0
        if mask.any():
            tc_values = cleaned.loc[mask, "TotalCharges"]
            assert (tc_values == 0.0).all(), \
                f"tenure=0 olan satırlarda TotalCharges ≠ 0: {tc_values.unique()}"


# ─────────────────────────────────────────────────────────────────────────────
# TelcoFeatureEngineer Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestTelcoFeatureEngineer:
    """10 yeni feature'ın doğru üretildiğini test eder."""

    def _get_engineer(self):
        """Feature engineer nesnesini oluşturur."""
        from src.components.data_transformation import (
            TelcoFeatureEngineer, DataTransformationConfig
        )
        config = DataTransformationConfig()
        return TelcoFeatureEngineer(config)

    def test_adds_loyalty_index(self, sample_raw_dataframe):
        """LoyaltyIndex sütunu eklenmeli."""
        fe = self._get_engineer()
        result = fe.add_features(sample_raw_dataframe)
        assert "LoyaltyIndex" in result.columns

    def test_loyalty_index_nonnegative(self, sample_raw_dataframe):
        """LoyaltyIndex = log1p(tenure) → her zaman ≥ 0 olmalı."""
        fe = self._get_engineer()
        result = fe.add_features(sample_raw_dataframe)
        assert (result["LoyaltyIndex"] >= 0).all()

    def test_adds_total_addon_services(self, sample_raw_dataframe):
        """TotalAddOnServices sütunu eklenmeli ve 0-6 arasında olmalı."""
        fe = self._get_engineer()
        result = fe.add_features(sample_raw_dataframe)

        assert "TotalAddOnServices" in result.columns
        assert result["TotalAddOnServices"].min() >= 0
        assert result["TotalAddOnServices"].max() <= 6

    def test_adds_risk_scope_flag(self, sample_raw_dataframe):
        """RiskScope_Fiber_NoSupport_NoSec binary (0/1) olmalı."""
        fe = self._get_engineer()
        result = fe.add_features(sample_raw_dataframe)

        assert "RiskScope_Fiber_NoSupport_NoSec" in result.columns
        unique_vals = set(result["RiskScope_Fiber_NoSupport_NoSec"].unique())
        assert unique_vals.issubset({0, 1})

    def test_adds_all_ten_features(self, sample_raw_dataframe):
        """Toplam 10 yeni feature eklenmeli."""
        fe = self._get_engineer()
        original_cols = set(sample_raw_dataframe.columns)
        result = fe.add_features(sample_raw_dataframe)
        new_cols = set(result.columns) - original_cols

        expected = {
            "LoyaltyIndex", "TotalAddOnServices", "UnitCost",
            "AvgPaidPerMonth", "ChargeGap", "RiskScope_Fiber_NoSupport_NoSec",
            "IsMonthToMonth", "IsPaperless", "IsElectronicCheck", "TenureBucket"
        }
        missing = expected - new_cols
        assert len(missing) == 0, f"Eksik feature'lar: {missing}"

    def test_tenure_bucket_valid_labels(self, sample_raw_dataframe):
        """TenureBucket yalnızca tanımlı etiketleri içermeli."""
        fe = self._get_engineer()
        result = fe.add_features(sample_raw_dataframe)

        valid_labels = {"0-6", "7-12", "13-24", "25-48", "49-72", "72+"}
        actual = set(result["TenureBucket"].unique())
        invalid = actual - valid_labels
        assert len(invalid) == 0, f"Geçersiz TenureBucket etiketleri: {invalid}"


# ─────────────────────────────────────────────────────────────────────────────
# DataTransformation Pipeline Testleri
# ─────────────────────────────────────────────────────────────────────────────

class TestDataTransformationPipeline:
    """Tam dönüşüm pipeline'ının çıktılarını test eder."""

    def _prepare_data(self, sample_raw_dataframe):
        """Sentetik veriyi train/test olarak böler (test yardımcısı)."""
        from sklearn.model_selection import train_test_split

        df = sample_raw_dataframe.copy()
        # Churn'ü binary yap
        df["Churn"] = df["Churn"].map({"Yes": 1, "No": 0}).astype(int)

        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
        return train_df, test_df

    def test_initiate_returns_five_elements(self, sample_raw_dataframe):
        """initiate() → (X_train, X_test, y_train, y_test, preprocessor_path)."""
        from src.components.data_transformation import DataTransformation

        train_df, test_df = self._prepare_data(sample_raw_dataframe)
        transformer = DataTransformation()
        result = transformer.initiate(train_df, test_df)

        assert len(result) == 5, f"initiate() {len(result)} eleman döndü, 5 bekleniyordu"

    def test_output_is_numpy_arrays(self, sample_raw_dataframe):
        """Çıktı X_train ve X_test numpy array olmalı."""
        from src.components.data_transformation import DataTransformation

        train_df, test_df = self._prepare_data(sample_raw_dataframe)
        transformer = DataTransformation()
        X_train, X_test, y_train, y_test, _ = transformer.initiate(train_df, test_df)

        assert isinstance(X_train, np.ndarray)
        assert isinstance(X_test, np.ndarray)

    def test_preprocessor_pkl_created(self, sample_raw_dataframe):
        """Preprocessor .pkl dosyası oluşturulmuş olmalı."""
        from src.components.data_transformation import DataTransformation

        train_df, test_df = self._prepare_data(sample_raw_dataframe)
        transformer = DataTransformation()
        _, _, _, _, pp_path = transformer.initiate(train_df, test_df)

        assert os.path.exists(pp_path), f"preprocessor.pkl oluşturulmadı: {pp_path}"

    def test_no_nan_in_output(self, sample_raw_dataframe):
        """Çıktı matrislerinde NaN olmamalı (imputer'lar temizlemiş olmalı)."""
        from src.components.data_transformation import DataTransformation

        train_df, test_df = self._prepare_data(sample_raw_dataframe)
        transformer = DataTransformation()
        X_train, X_test, _, _, _ = transformer.initiate(train_df, test_df)

        assert not np.isnan(X_train).any(), "X_train'de NaN var!"
        assert not np.isnan(X_test).any(), "X_test'de NaN var!"
