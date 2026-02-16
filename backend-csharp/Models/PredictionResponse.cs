// ============================================================================
// Models/PredictionResponse.cs — Tahmin Sonucu Modeli
// ============================================================================
// AMAÇ: Python API'den dönen tahmin sonucunu temsil eder.
// ============================================================================

namespace ChurnRiskAPI.Models;

/// <summary>
/// Tahmin sonucunu içeren model
/// </summary>
public class PredictionResponse
{
    public string Prediction { get; set; } = string.Empty;
    public double ChurnProbability { get; set; }
    public string RiskLevel { get; set; } = string.Empty;
    public double Confidence { get; set; }
    public string ModelVersion { get; set; } = string.Empty;
    public string PredictionId { get; set; } = string.Empty;
}

/// <summary>
/// Model bilgisi modeli
/// </summary>
public class ModelInfo
{
    public string ModelName { get; set; } = string.Empty;
    public string Version { get; set; } = string.Empty;
    public Dictionary<string, double> Metrics { get; set; } = new();
    public Dictionary<string, double> FeatureImportance { get; set; } = new();
}

/// <summary>
/// Sağlık durumu modeli
/// </summary>
public class HealthStatus
{
    public string Status { get; set; } = string.Empty;
    public bool ModelLoaded { get; set; }
    public bool PreprocessorLoaded { get; set; }
    public DateTime Timestamp { get; set; }
}

/// <summary>
/// Drift durumu modeli
/// </summary>
public class DriftStatus
{
    public bool DriftDetected { get; set; }
    public double DriftScore { get; set; }
    public double Threshold { get; set; }
    public string Recommendation { get; set; } = string.Empty;
    public DateTime Timestamp { get; set; }
}
