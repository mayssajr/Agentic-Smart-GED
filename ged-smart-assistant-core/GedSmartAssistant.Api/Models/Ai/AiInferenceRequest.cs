using System.Text.Json.Serialization;

namespace GedSmartAssistant.Api.Models.Ai;

public sealed class AiInferenceRequest
{
    /// <summary>Message enrichi (avec préfixe utilisateur).</summary>
    public string Message { get; init; } = string.Empty;

    /// <summary>
    /// Token JWT MiniGED de la session courante.
    /// Transmis au backend Python pour que GED_SEARCH puisse
    /// appeler l'API MiniGED et retourner les vrais documents.
    /// </summary>
    [JsonPropertyName("miniged_token")]
    public string MinigedToken { get; init; } = string.Empty;

    [JsonPropertyName("document_id")]
    public string DocumentId { get; init; } = string.Empty;

    [JsonPropertyName("document_type")]
    public string DocumentType { get; init; } = string.Empty;

    [JsonPropertyName("filename")]
    public string Filename { get; init; } = string.Empty;
}