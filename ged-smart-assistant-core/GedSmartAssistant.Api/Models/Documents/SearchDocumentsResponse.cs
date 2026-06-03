namespace GedSmartAssistant.Api.Models.Documents;

public sealed class SearchDocumentsResponse
{
    public bool Success { get; init; }
    public SearchResults Results { get; init; } = new();
}

public sealed class SearchResults
{
    public IReadOnlyList<SearchHit> Items { get; init; } = Array.Empty<SearchHit>();
    public int Page { get; init; }
    public int PageSize { get; init; }
    public int TotalCount { get; init; }
}

public sealed class SearchHit
{
    public int FileId { get; init; }
    public string FileName { get; init; } = string.Empty;
    public int FileStatus { get; init; }
    public int DocumentId { get; init; }
    public string DocumentTitle { get; init; } = string.Empty;
    public string DocumentDescription { get; init; } = string.Empty;
    public DateTimeOffset UploadedAt { get; init; }
    public string Snippet { get; init; } = string.Empty;
    public double Rank { get; init; }
}
