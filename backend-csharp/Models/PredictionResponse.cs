// ============================================================================
// Models/PredictionResponse.cs — Tahmin Sonucu Modeli
// ============================================================================
// AMAÇ: Python API'den dönen tahmin sonucunu temsil eder.
// ============================================================================

using Newtonsoft.Json;

namespace ChurnRiskAPI.Models;

/// <summary>
/// Tahmin sonucunu içeren model
/// </summary>
public class PredictionResponse
{
    [JsonProperty("prediction")]
    public int Prediction { get; set; }

    [JsonProperty("churn_probability")]
    public double ChurnProbability { get; set; }

    [JsonProperty("risk_level")]
    public string RiskLevel { get; set; } = string.Empty;

    [JsonProperty("customerID")]
    public string CustomerId { get; set; } = string.Empty;
}

/// <summary>
/// Model bilgisi modeli
/// </summary>
public class ModelInfo
{
    [JsonProperty("model_name")]
    public string ModelName { get; set; } = string.Empty;

    [JsonProperty("accuracy")]
    public double? Accuracy { get; set; }

    [JsonProperty("f1")]
    public double? F1 { get; set; }

    [JsonProperty("recall")]
    public double? Recall { get; set; }

    [JsonProperty("precision")]
    public double? Precision { get; set; }

    [JsonProperty("roc_auc")]
    public double? RocAuc { get; set; }

    [JsonProperty("pr_auc")]
    public double? PrAuc { get; set; }
}

/// <summary>
/// Sağlık durumu modeli
/// </summary>
public class HealthStatus
{
    [JsonProperty("status")]
    public string Status { get; set; } = string.Empty;

    [JsonProperty("model_loaded")]
    public bool ModelLoaded { get; set; }

    [JsonProperty("preprocessor_loaded")]
    public bool PreprocessorLoaded { get; set; }
}

/// <summary>
/// Drift durumu modeli
/// </summary>
public class DriftStatus
{
    [JsonProperty("drift_detected")]
    public bool DriftDetected { get; set; }

    [JsonProperty("drift_ratio")]
    public double DriftRatio { get; set; }

    [JsonProperty("drifted_features")]
    public List<string> DriftedFeatures { get; set; } = new();

    [JsonProperty("alert_level")]
    public string AlertLevel { get; set; } = string.Empty;

    [JsonProperty("message")]
    public string Message { get; set; } = string.Empty;

    [JsonProperty("sample_size")]
    public int? SampleSize { get; set; }

    [JsonProperty("total_features_checked")]
    public int? TotalFeaturesChecked { get; set; }

    [JsonProperty("threshold")]
    public double Threshold { get; set; }
}
