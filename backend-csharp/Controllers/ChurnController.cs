// ============================================================================
// Controllers/ChurnController.cs — Ana API Controller
// ============================================================================
// AMAÇ:
//   Frontend'in kullanacağı RESTful endpoint'ler.
//   Basit ve anlaşılır API yapısı.
// ============================================================================

using Microsoft.AspNetCore.Mvc;
using ChurnRiskAPI.Models;
using ChurnRiskAPI.Services;

namespace ChurnRiskAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ChurnController : ControllerBase
{
    private readonly PythonApiService _pythonApiService;
    private readonly ILogger<ChurnController> _logger;

    public ChurnController(PythonApiService pythonApiService, ILogger<ChurnController> logger)
    {
        _pythonApiService = pythonApiService;
        _logger = logger;
    }

    /// <summary>
    /// Karşılama mesajı
    /// </summary>
    [HttpGet]
    public IActionResult Welcome()
    {
        return Ok(new
        {
            Message = "🚀 Churn Risk Platform - C# Backend",
            Version = "1.0.0",
            Status = "Çalışıyor",
            Endpoints = new[]
            {
                "GET  /api/churn - Bu mesaj",
                "POST /api/churn/predict - Müşteri tahmini",
                "GET  /api/churn/model-info - Model bilgileri",
                "GET  /api/churn/health - Sistem sağlığı",
                "GET  /api/churn/drift - Drift durumu"
            }
        });
    }

    /// <summary>
    /// Müşteri churn tahmini yap
    /// </summary>
    /// <remarks>
    /// Örnek istek:
    /// 
    ///     POST /api/churn/predict
    ///     {
    ///       "gender": "Female",
    ///       "seniorCitizen": 0,
    ///       "partner": "Yes",
    ///       "dependents": "No",
    ///       "tenure": 12,
    ///       "phoneService": "Yes",
    ///       "multipleLines": "No",
    ///       "internetService": "Fiber optic",
    ///       "onlineSecurity": "No",
    ///       "onlineBackup": "Yes",
    ///       "deviceProtection": "No",
    ///       "techSupport": "No",
    ///       "streamingTV": "Yes",
    ///       "streamingMovies": "No",
    ///       "contract": "Month-to-month",
    ///       "paperlessBilling": "Yes",
    ///       "paymentMethod": "Electronic check",
    ///       "monthlyCharges": 70.35,
    ///       "totalCharges": 1397.48
    ///     }
    /// </remarks>
    [HttpPost("predict")]
    public async Task<IActionResult> Predict([FromBody] CustomerRequest customer)
    {
        try
        {
            _logger.LogInformation("Tahmin isteği alındı");

            var result = await _pythonApiService.PredictChurnAsync(customer);

            if (result == null)
            {
                return StatusCode(500, new { Error = "Tahmin yapılamadı" });
            }

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Tahmin hatası");
            return StatusCode(500, new { Error = ex.Message });
        }
    }

    /// <summary>
    /// Model bilgilerini getir
    /// </summary>
    [HttpGet("model-info")]
    public async Task<IActionResult> GetModelInfo()
    {
        try
        {
            var result = await _pythonApiService.GetModelInfoAsync();
            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Model bilgisi alma hatası");
            return StatusCode(500, new { Error = ex.Message });
        }
    }

    /// <summary>
    /// Sistem sağlık kontrolü
    /// </summary>
    [HttpGet("health")]
    public async Task<IActionResult> GetHealth()
    {
        try
        {
            var result = await _pythonApiService.GetHealthStatusAsync();
            
            if (result?.Status == "healthy")
            {
                return Ok(result);
            }
            else
            {
                return StatusCode(503, result);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Sağlık kontrolü hatası");
            return StatusCode(503, new { Status = "unhealthy", Error = ex.Message });
        }
    }

    /// <summary>
    /// Model drift durumunu kontrol et
    /// </summary>
    [HttpGet("drift")]
    public async Task<IActionResult> GetDriftStatus()
    {
        try
        {
            var result = await _pythonApiService.GetDriftStatusAsync();
            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Drift kontrolü hatası");
            return StatusCode(500, new { Error = ex.Message });
        }
    }
}
