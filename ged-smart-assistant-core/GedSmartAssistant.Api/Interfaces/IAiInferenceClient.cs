using GedSmartAssistant.Api.Models.Ai;

namespace GedSmartAssistant.Api.Interfaces;

public interface IAiInferenceClient
{
    Task<AiInferenceResult> InferAsync(
    string message,
    string? documentId,
    string? documentType,
    string? filename,
    string? userId,
    CancellationToken cancellationToken);
}
