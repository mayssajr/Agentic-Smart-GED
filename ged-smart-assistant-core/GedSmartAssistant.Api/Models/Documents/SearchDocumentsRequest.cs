namespace GedSmartAssistant.Api.Models.Documents;

public sealed class SearchDocumentsRequest
{
    public string? Query { get; init; }
    public int Page { get; init; } = 1;
    public int PageSize { get; init; } = 5;
    public int Sort { get; init; } = 0;
}
