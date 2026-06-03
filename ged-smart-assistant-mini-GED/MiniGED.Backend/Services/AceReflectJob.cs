
using Microsoft.Extensions.Logging;

namespace MiniGED.API.Services;

public class AceReflectJob
{
    private readonly IHttpClientFactory            _http;
    private readonly ILogger<AceReflectJob>        _logger;
    private const string AcePythonUrl = "http://localhost:8000";

    public AceReflectJob(IHttpClientFactory http, ILogger<AceReflectJob> logger)
    {
        _http   = http;
        _logger = logger;
    }

    /// <summary>
    /// Lance le cycle complet de réflexion ACE (Reflector global).
    /// À planifier dans Program.cs via Hangfire RecurringJob.
    /// </summary>
    public async Task RunDailyReflectionAsync()
    {
        _logger.LogInformation("[ACE] Démarrage réflexion journalière...");
        try
        {
            using var http     = _http.CreateClient();
            http.Timeout       = TimeSpan.FromSeconds(120); // Le Reflector LLM peut prendre du temps
            var response       = await http.PostAsync($"{AcePythonUrl}/ace/reflect",
                                     new StringContent("{}", System.Text.Encoding.UTF8, "application/json"));
            var body           = await response.Content.ReadAsStringAsync();

            if (response.IsSuccessStatusCode)
                _logger.LogInformation("[ACE] Réflexion journalière OK | {Body}", body[..Math.Min(200, body.Length)]);
            else
                _logger.LogWarning("[ACE] Réflexion HTTP {Status} | {Body}",
                    (int)response.StatusCode, body[..Math.Min(100, body.Length)]);
        }
        catch (Exception ex)
        {
            _logger.LogError("[ACE] Réflexion journalière échouée: {Message}", ex.Message);
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Dans Program.cs, ajouter après app.UseHangfireDashboard() :
//
//   // ACE : réflexion globale quotidienne à 3h du matin
//   RecurringJob.AddOrUpdate<AceReflectJob>(
//       "ace-daily-reflect",
//       job => job.RunDailyReflectionAsync(),
//       "0 3 * * *",           // Cron : 3h00 chaque nuit
//       new RecurringJobOptions { TimeZone = TimeZoneInfo.Utc }
//   );
//
// S'assurer que AceReflectJob est enregistré dans le DI :
//   builder.Services.AddScoped<AceReflectJob>();
//   builder.Services.AddHttpClient();  // si pas déjà fait
// ─────────────────────────────────────────────────────────────────────────────