using System.Text;
using System.Text.Json;
using GedSmartAssistant.Api.Dtos.Requests;
using GedSmartAssistant.Api.Dtos.Response;
using GedSmartAssistant.Api.Interfaces;
using GedSmartAssistant.Api.Models.Ai;
using GedSmartAssistant.Api.Models.Auth;
using GedSmartAssistant.Api.Models.Documents;

namespace GedSmartAssistant.Api.Services;

public sealed class ChatService(
    IAiInferenceClient aiInferenceClient,
    IMiniGedSessionService miniGedSessionService) : IChatService
{
    public async Task<ChatResponse> ProcessAsync(
        ChatRequest request, CancellationToken cancellationToken)
    {
        Console.WriteLine($"[DEBUG ChatService] Message='{request.Message}' | DocId='{request.DocumentId}' | DocType='{request.DocumentType}'");
        var currentUser     = await miniGedSessionService.GetCurrentUserAsync(cancellationToken);
        var enrichedMessage = BuildInferencePrompt(currentUser, request.Message);
        var inference       = await aiInferenceClient.InferAsync(enrichedMessage, request.DocumentId, request.DocumentType, request.Filename, currentUser.Id.ToString(), cancellationToken);

        if (inference.ActionDone == "email_draft_ready" && inference.EmailDraft != null)
        {
            return BuildEmailDraft(inference);
        }

        return inference.Tool switch
        {
            null or "" or "answer" => BuildDirectAnswer(inference),
            "create_document"      => await HandleCreateDocumentAsync(inference, cancellationToken),
            "search_documents"     => await HandleSearchDocumentsAsync(inference, request.Message, cancellationToken),
            "summarize"            => BuildActionSuggestion(inference, "summarize",
                "Je peux résumer ce document. Voulez-vous que je lance l'analyse ?",
                new[] { new ActionButton("Analyser le document", "analyze", "primary") }),
            "sign_document"        => BuildActionSuggestion(inference, "sign_document",
                "Ce document nécessite une signature. Confirmez-vous ?",
                new[] { new ActionButton("Signer", "sign", "primary"),
                        new ActionButton("Annuler", "cancel", "secondary") }),

            // ── "send_email" → toujours construire un draft, jamais envoyer directement
            "send_email"           => BuildEmailDraft(inference),

            "legal_analysis"       => BuildActionSuggestion(inference, "legal_analysis",
                inference.DirectAnswer ?? "Analyse juridique identifiée pour ce document.",
                new[] { new ActionButton("Voir l'analyse", "legal", "primary") }),
            "extract_fields"       => BuildActionSuggestion(inference, "extract_fields",
                inference.DirectAnswer ?? "Je peux extraire les informations clés.",
                new[] { new ActionButton("Extraire", "extract", "primary") }),
            _                      => BuildDirectAnswer(inference),
        };
    }

    // ── Réponse directe ───────────────────────────────────────────────

    private static ChatResponse BuildDirectAnswer(AiInferenceResult inference) => new()
    {
        Reply         = !string.IsNullOrWhiteSpace(inference.DirectAnswer)
                        ? inference.DirectAnswer
                        : "Je suis désolé, pouvez-vous reformuler ?",
        NeedsMoreInfo = inference.NeedsMoreInfo,
        Suggestions   = MapSuggestions(inference.Suggestions),
    };

    // ── Suggestion d'action ───────────────────────────────────────────

    private static ChatResponse BuildActionSuggestion(
        AiInferenceResult inference,
        string tool,
        string defaultReply,
        ActionButton[] buttons) => new()
    {
        Reply         = !string.IsNullOrWhiteSpace(inference.DirectAnswer)
                        ? inference.DirectAnswer : defaultReply,
        Tool          = tool,
        ToolArguments = ToSerializableArguments(inference.Arguments),
        ActionButtons = buttons.ToList(),
        Suggestions   = MapSuggestions(inference.Suggestions),
    };


    private static ChatResponse BuildEmailDraft(AiInferenceResult inference)
    {
  
        string to, subject, body, filename;
        bool   hasAttachment;

        if (inference.EmailDraft != null)
        {
            to            = inference.EmailDraft.To;
            subject       = inference.EmailDraft.Subject;
            body          = inference.EmailDraft.Body;
            filename      = inference.EmailDraft.Filename;
            hasAttachment = inference.EmailDraft.HasAttachment;
        }
        else
        {
            to            = GetStringArgument(inference.Arguments, "to")
                         ?? GetStringArgument(inference.Arguments, "email_to")
                         ?? "";
            filename      = GetStringArgument(inference.Arguments, "filename") ?? "Document";
            subject       = $"[MiniGED] {filename}";
            body          = !string.IsNullOrWhiteSpace(inference.DirectAnswer)
                            ? inference.DirectAnswer
                            : "Bonjour,\n\nVeuillez trouver ci-joint les informations demandées.\n\nCordialement,";
            hasAttachment = false;
        }

        return new ChatResponse
        {
            Reply         = !string.IsNullOrWhiteSpace(inference.DirectAnswer)
                            ? inference.DirectAnswer
                            : $"Voici le brouillon d'email pour **{to}**. Modifiez si besoin puis cliquez Envoyer.",
            Tool          = "send_email",
            ToolArguments = ToSerializableArguments(inference.Arguments),

            // ← CRUCIAL : ces deux champs manquaient avant
            EmailActionId = inference.EmailActionId,
            EmailDraft    = new EmailDraft
            {
                To            = to,
                Subject       = subject,
                Body          = body,
                Filename      = filename,
                HasAttachment = hasAttachment,
            },

            ActionButtons = new List<ActionButton>
            {
                new("Envoyer",  "confirm_email", "primary"),
                new("Modifier", "edit_email",    "secondary"),
                new("Annuler",  "cancel_email",  "secondary"),
            },
            Suggestions = MapSuggestions(inference.Suggestions),
        };
    }

    // ── Recherche documents ───────────────────────────────────────────

    private async Task<ChatResponse> HandleSearchDocumentsAsync(
        AiInferenceResult inference,
        string originalMessage,
        CancellationToken cancellationToken)
    {
        var keyword = ExtractMeaningfulKeyword(inference.Arguments, originalMessage);

        if (string.IsNullOrWhiteSpace(keyword))
        {
            return new ChatResponse
            {
                Reply       = !string.IsNullOrWhiteSpace(inference.DirectAnswer)
                              ? inference.DirectAnswer
                              : "Précisez ce que vous recherchez dans vos documents.",
                Suggestions = MapSuggestions(inference.Suggestions),
            };
        }

        try
        {
            var results  = await miniGedSessionService.SearchDocumentsAsync(keyword, cancellationToken);
            var hitCount = results.Results.TotalCount;

            if (hitCount > 0)
            {
                var names = results.Results.Items
                    .Take(5)
                    .Select(h => h.DocumentTitle ?? h.FileName ?? "Document")
                    .ToArray();

                var sb = new StringBuilder();
                sb.AppendLine(
                    $"J'ai trouvé **{hitCount} document{(hitCount > 1 ? "s" : "")}**" +
                    $" pour « {keyword} » :");
                foreach (var name in names)
                    sb.AppendLine($"• {name}");

                return new ChatResponse
                {
                    Reply         = sb.ToString().Trim(),
                    Tool          = "search_documents",
                    ToolArguments = ToSerializableArguments(inference.Arguments),
                    ToolResult    = results,
                    Suggestions   = MapSuggestions(inference.Suggestions),
                };
            }
        }
        catch
        {
        }

        return new ChatResponse
        {
            Reply       = !string.IsNullOrWhiteSpace(inference.DirectAnswer)
                          ? inference.DirectAnswer
                          : $"Aucun document trouvé pour « {keyword} ».",
            Suggestions = MapSuggestions(inference.Suggestions),
        };
    }

    // ── Créer document ────────────────────────────────────────────────

    private async Task<ChatResponse> HandleCreateDocumentAsync(
        AiInferenceResult inference,
        CancellationToken cancellationToken)
    {
        var title       = GetRequiredStringArgument(inference.Arguments, "title");
        var description = GetRequiredStringArgument(inference.Arguments, "description");
        var result      = await miniGedSessionService.CreateDocumentAsync(
            new CreateDocumentCommand { Title = title, Description = description },
            cancellationToken);

        return new ChatResponse
        {
            Reply         = $"Document « {title} » créé avec succès.",
            Tool          = inference.Tool,
            ToolArguments = ToSerializableArguments(inference.Arguments),
            ToolResult    = result,
        };
    }

    // ── Helpers ───────────────────────────────────────────────────────

    private static string BuildInferencePrompt(UserProfile user, string message) => message;

    private static readonly HashSet<string> _stopWords =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "quels","quel","quelle","quelles","il","y","a","t",
            "le","la","les","un","une","des","de","du","que","qui",
            "est","sont","ont","dans","pour","avec","sur","par",
            "au","aux","en","et","ou","mon","ma","mes","vos","nos",
            "document","documents","fichier","fichiers","ged",
            "existent","existe","maintenant","actuellement",
            "liste","tous","toutes","moi","montre","affiche",
            "cherche","trouve","donne","voir","quoi",
        };

    private static string ExtractMeaningfulKeyword(
        Dictionary<string, JsonElement> arguments,
        string originalMessage)
    {
        foreach (var key in new[] { "keyword", "query", "search_term", "term" })
        {
            var v = GetStringArgument(arguments, key);
            if (!string.IsNullOrWhiteSpace(v))
            {
                var cleaned = FilterStopWords(v);
                if (!string.IsNullOrWhiteSpace(cleaned)) return cleaned;
            }
        }
        return FilterStopWords(originalMessage);
    }

    private static string FilterStopWords(string raw)
    {
        var words = raw
            .Split(new[] { ' ', '?', '!', '.', ',', ';', ':', '\n', '\r' },
                   StringSplitOptions.RemoveEmptyEntries)
            .Where(w => w.Length > 2 && !_stopWords.Contains(w))
            .Take(4)
            .ToArray();
        return string.Join(" ", words);
    }

    private static List<ActionSuggestion>? MapSuggestions(List<object>? raw)
    {
        if (raw == null || raw.Count == 0) return null;
        var result = new List<ActionSuggestion>();
        foreach (var item in raw)
        {
            try
            {
                var json = item is JsonElement je
                    ? je : JsonSerializer.SerializeToElement(item);
                result.Add(new ActionSuggestion
                {
                    Label    = json.TryGetProperty("label",    out var l) ? l.GetString() ?? "" : "",
                    Action   = json.TryGetProperty("action",   out var a) ? a.GetString() ?? "" : "",
                    Icon     = json.TryGetProperty("icon",     out var i) ? i.GetString() ?? "" : "",
                    Prefill  = json.TryGetProperty("prefill",  out var p) ? p.GetString() ?? "" : "",
                    Workflow = json.TryGetProperty("workflow", out var w) ? w.GetString() ?? "" : "",
                });
            }
            catch { }
        }
        return result.Count > 0 ? result : null;
    }

    private static string GetRequiredStringArgument(
        Dictionary<string, JsonElement> arguments, string key)
    {
        if (!arguments.TryGetValue(key, out var value))
            throw new InvalidOperationException($"Argument requis manquant : '{key}'.");
        var parsed = value.ValueKind == JsonValueKind.String
            ? value.GetString() : value.ToString();
        if (string.IsNullOrWhiteSpace(parsed))
            throw new InvalidOperationException($"Argument vide : '{key}'.");
        return parsed;
    }

    private static string? GetStringArgument(
        Dictionary<string, JsonElement> arguments, string key)
    {
        if (!arguments.TryGetValue(key, out var value)) return null;
        return value.ValueKind == JsonValueKind.String
            ? value.GetString() : value.ToString();
    }

    private static Dictionary<string, object?> ToSerializableArguments(
        Dictionary<string, JsonElement> arguments) =>
        arguments.ToDictionary(
            p => p.Key,
            p => p.Value.ValueKind switch
            {
                JsonValueKind.String => p.Value.GetString(),
                JsonValueKind.Number when p.Value.TryGetInt64(out var l) => l,
                JsonValueKind.Number when p.Value.TryGetDecimal(out var d) => d,
                JsonValueKind.True   => true,
                JsonValueKind.False  => false,
                JsonValueKind.Null   => null,
                _                   => (object?)p.Value.ToString()
            },
            StringComparer.OrdinalIgnoreCase);
}