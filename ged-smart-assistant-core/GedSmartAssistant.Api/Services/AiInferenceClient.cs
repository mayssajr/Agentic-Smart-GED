using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using GedSmartAssistant.Api.Interfaces;
using GedSmartAssistant.Api.Models.Ai;

namespace GedSmartAssistant.Api.Services;

public sealed class AiInferenceClient(
    HttpClient httpClient,
    ISessionTokenStore sessionTokenStore) : IAiInferenceClient
{
    private static readonly JsonSerializerOptions JsonOptions =
        new(JsonSerializerDefaults.Web);

    public async Task<AiInferenceResult> InferAsync(
        string message,
        string? documentId,
        string? documentType,
        string? filename,
        string? userId,
        CancellationToken cancellationToken)
    {
        var tokens       = sessionTokenStore.GetTokens();
        var minigedToken = tokens?.AccessToken ?? "";

        var request = new
        {
            message      = message,
            miniged_token = minigedToken,
            document_id   = documentId   ?? "",
            document_type = documentType ?? "",
            filename      = filename     ?? "",
            user_id       = userId       ?? "",
        };

        using var response = await httpClient.PostAsJsonAsync(
            "/infer",
            request,
            JsonOptions,
            cancellationToken);

        response.EnsureSuccessStatusCode();

        var payload = await response.Content
            .ReadFromJsonAsync<AiInferenceResult>(JsonOptions, cancellationToken);

        return payload
            ?? throw new InvalidOperationException(
                "AI service returned an empty inference payload.");
    }
}