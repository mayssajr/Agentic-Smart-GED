using System.Text.Json.Serialization;

namespace GedSmartAssistant.Api.Dtos.Response;

/// <summary>
/// Réponse du ChatService envoyée au frontend Vue.
/// </summary>
public sealed class ChatResponse
{
    public string Reply { get; init; } = string.Empty;

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Tool { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public Dictionary<string, object?>? ToolArguments { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public object? ToolResult { get; init; }

    public bool NeedsMoreInfo { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public List<ActionButton>? ActionButtons { get; init; }

    /// <summary>
    /// Brouillon email — maintenant avec HasAttachment et Filename
    /// pour afficher le badge "avec pièce jointe" dans le frontend.
    /// </summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public EmailDraft? EmailDraft { get; init; }

    /// <summary>
    /// ID de la pending action Python à confirmer via /confirm-action.
    /// CRUCIAL : sans ce champ, le bouton "Envoyer" du frontend ne peut pas
    /// appeler /confirm-action et l'email ne part jamais.
    /// </summary>
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? EmailActionId { get; init; }

    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public List<ActionSuggestion>? Suggestions { get; init; }
}

public sealed class ActionButton
{
    public ActionButton() { }
    public ActionButton(string label, string action, string severity = "secondary")
    {
        Label    = label;
        Action   = action;
        Severity = severity;
    }

    public string Label    { get; init; } = string.Empty;
    public string Action   { get; init; } = string.Empty;
    public string Severity { get; init; } = "secondary";
}

/// <summary>
/// Brouillon email transmis au frontend.
/// Correspond exactement aux champs lus par MessageBubble.vue.
/// </summary>
public sealed class EmailDraft
{
    public string To            { get; init; } = string.Empty;
    public string Subject       { get; init; } = string.Empty;
    public string Body          { get; init; } = string.Empty;

    /// <summary>Nom du fichier joint (ex: ingenieur-mecanique.pdf)</summary>
    public string Filename      { get; init; } = string.Empty;

    /// <summary>true = PDF récupéré, badge vert "avec pièce jointe" affiché</summary>
    public bool   HasAttachment { get; init; }
}

public sealed class ActionSuggestion
{
    public string Label    { get; set; } = string.Empty;
    public string Action   { get; set; } = string.Empty;
    public string Icon     { get; set; } = string.Empty;
    public string Prefill  { get; set; } = string.Empty;
    public string Workflow { get; set; } = string.Empty;
}