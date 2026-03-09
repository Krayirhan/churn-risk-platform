// ============================================================================
// Services/PythonApiService.cs — Python API İle İletişim Servisi
// ============================================================================
// AMAÇ:
//   Python FastAPI backend'ine HTTP istekleri gönderir.
//   Basit ve anlaşılır servis katmanı.
// ============================================================================

using ChurnRiskAPI.Models;
using Newtonsoft.Json;
using System.Text;

namespace ChurnRiskAPI.Services;

public class PythonApiService
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<PythonApiService> _logger;
    private readonly string? _apiKey;

    public PythonApiService(HttpClient httpClient, ILogger<PythonApiService> logger, IConfiguration configuration)
    {
        _httpClient = httpClient;
        _logger = logger;
        // PythonAPI:ApiKey config veya PYTHON_API_KEY env var'ından oku
        _apiKey = configuration["PythonAPI:ApiKey"]
                  ?? Environment.GetEnvironmentVariable("PYTHON_API_KEY");
    }

    /// <summary>
    /// Her isteğe API key header'ı ekler (tanımlıysa).
    /// </summary>
    private void ApplyApiKeyHeader(HttpRequestMessage? request = null)
    {
        if (!string.IsNullOrEmpty(_apiKey))
        {
            _httpClient.DefaultRequestHeaders.Remove("X-API-Key");
            _httpClient.DefaultRequestHeaders.Add("X-API-Key", _apiKey);
        }
    }

    /// <summary>
    /// Müşteri churn tahmini yap
    /// </summary>
    public async Task<PredictionResponse?> PredictChurnAsync(CustomerRequest customer)
    {
        try
        {
            _logger.LogInformation("Tahmin isteği gönderiliyor...");
            ApplyApiKeyHeader();

            var json = JsonConvert.SerializeObject(customer);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            var response = await _httpClient.PostAsync("/predict", content);
            response.EnsureSuccessStatusCode();

            var responseData = await response.Content.ReadAsStringAsync();
            var result = JsonConvert.DeserializeObject<PredictionResponse>(responseData);

            _logger.LogInformation("Tahmin başarılı: {Prediction}", result?.Prediction);
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Tahmin hatası!");
            throw;
        }
    }

    /// <summary>
    /// Model bilgilerini getir
    /// </summary>
    public async Task<ModelInfo?> GetModelInfoAsync()
    {
        try
        {
            _logger.LogInformation("Model bilgisi getiriliyor...");
            ApplyApiKeyHeader();

            var response = await _httpClient.GetAsync("/model-info");
            response.EnsureSuccessStatusCode();

            var responseData = await response.Content.ReadAsStringAsync();
            var result = JsonConvert.DeserializeObject<ModelInfo>(responseData);

            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Model bilgisi alma hatası!");
            throw;
        }
    }

    /// <summary>
    /// Sağlık kontrolü yap
    /// </summary>
    public async Task<HealthStatus?> GetHealthStatusAsync()
    {
        try
        {
            ApplyApiKeyHeader();
            var response = await _httpClient.GetAsync("/health");
            response.EnsureSuccessStatusCode();

            var responseData = await response.Content.ReadAsStringAsync();
            var result = JsonConvert.DeserializeObject<HealthStatus>(responseData);

            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Sağlık kontrolü hatası!");
            return new HealthStatus
            {
                Status = "unhealthy",
                ModelLoaded = false,
                PreprocessorLoaded = false
            };
        }
    }

    /// <summary>
    /// Drift durumunu kontrol et
    /// </summary>
    public async Task<DriftStatus?> GetDriftStatusAsync()
    {
        try
        {
            ApplyApiKeyHeader();
            var response = await _httpClient.GetAsync("/monitor/drift");
            response.EnsureSuccessStatusCode();

            var responseData = await response.Content.ReadAsStringAsync();
            var result = JsonConvert.DeserializeObject<DriftStatus>(responseData);

            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Drift kontrolü hatası!");
            throw;
        }
    }
}
