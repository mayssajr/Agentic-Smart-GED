using System.Text.Json;
using System.Text.Json.Serialization;

namespace GedSmartAssistant.Api.Models.Ai;

/// <summary>
/// Désérialise la réponse brute du backend Python /infer.
/// IMPORTANT : tous les champs snake_case Python doivent avoir
/// un [JsonPropertyName] correspondant.
/// </summary>
public sealed class AiInferenceResult
{
    [JsonPropertyName("tool_name")]
    public string? Tool { get; init; }

    public Dictionary<string, JsonElement> Arguments { get; init; } = new(StringComparer.OrdinalIgnoreCase);

    [JsonPropertyName("needs_more_info")]
    public bool NeedsMoreInfo { get; init; }

    [JsonPropertyName("direct_answer")]
    public string? DirectAnswer { get; init; }

    [JsonPropertyName("suggestions")]
    public List<object>? Suggestions { get; init; }

    // ── Champs EMAIL DRAFT (manquants avant — c'est la cause du bug) ──────────

    /// <summary>
    /// ID de la pending action créée par Python (uuid).
    /// Doit être renvoyé au frontend pour que le bouton "Envoyer" fonctionne.
    /// Python retourne ce champ sous le nom "email_action_id".
    /// </summary>
    [JsonPropertyName("email_action_id")]
    public string? EmailActionId { get; init; }

    /// <summary>
    /// Brouillon email généré par Python (to, subject, body, filename, has_attachment).
    /// Python retourne ce champ sous le nom "email_draft".
    /// </summary>
    [JsonPropertyName("email_draft")]
    public AiEmailDraft? EmailDraft { get; init; }

    /// <summary>
    /// Action réalisée par Python (ex: "email_draft_ready").
    /// Permet de détecter le flux brouillon même sans tool_name.
    /// </summary>
    [JsonPropertyName("action_done")]
    public string? ActionDone { get; init; }
}

/// <summary>
/// Brouillon email tel que retourné par Python assistant_agent.
/// Tous les champs sont en snake_case côté Python.
/// </summary>
public sealed class AiEmailDraft
{
    [JsonPropertyName("to")]
    public string To { get; init; } = string.Empty;

    [JsonPropertyName("subject")]
    public string Subject { get; init; } = string.Empty;

    [JsonPropertyName("body")]
    public string Body { get; init; } = string.Empty;

    [JsonPropertyName("filename")]
    public string Filename { get; init; } = string.Empty;

    [JsonPropertyName("has_attachment")]
    public bool HasAttachment { get; init; }
}