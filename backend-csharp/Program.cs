// ============================================================================
// Program.cs — ASP.NET Core Web API Giriş Noktası
// ============================================================================
// AMAÇ:
//   Python FastAPI backend'ini çağıran C# katmanı.
//   Çalışanların anlayacağı basit bir API yapısı.
// ============================================================================

using ChurnRiskAPI.Services;
using ChurnRiskAPI.Models;

var builder = WebApplication.CreateBuilder(args);

// ─────────────────────────────────────────────────────────────────────────────
// SERVİSLERİ KAYDET
// ─────────────────────────────────────────────────────────────────────────────
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// HTTP Client servisini ekle (Python API'ye bağlanmak için)
builder.Services.AddHttpClient<PythonApiService>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["PythonAPI:BaseUrl"] 
        ?? "http://localhost:8000");
    client.Timeout = TimeSpan.FromSeconds(30);
});

// CORS ayarları (Frontend'in API'ye erişmesi için)
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.WithOrigins("http://localhost:3000", "http://localhost:5500", "http://127.0.0.1:5500")
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

// ─────────────────────────────────────────────────────────────────────────────
// HTTP PİPELINE'I YAPILANDIR
// ─────────────────────────────────────────────────────────────────────────────
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors("AllowFrontend");
app.UseAuthorization();
app.MapControllers();

Console.WriteLine("╔════════════════════════════════════════════════════════════════╗");
Console.WriteLine("║     CHURN RISK PLATFORM - C# BACKEND BAŞLATILDI              ║");
Console.WriteLine("╠════════════════════════════════════════════════════════════════╣");
Console.WriteLine("║  Swagger UI: http://localhost:5001/swagger                    ║");
Console.WriteLine("║  Python API: http://localhost:8000                            ║");
Console.WriteLine("║  Frontend:   http://localhost:5500                            ║");
Console.WriteLine("╚════════════════════════════════════════════════════════════════╝");

app.Run();
