using NpgsqlTypes;

namespace MiniGED.API.Models;

public class DocumentFile : BaseModel
{

    public string FileName { get; set; } = null!;
    public string FilePath { get; set; } = null!;
    public long FileSize { get; set; }

    public FileProcessingStatus Status { get; set; }
    public string? ExtractedText { get; set; }
    public string? SearchableText { get; set; }
    public int PageCount { get; set; }
    public NpgsqlTsVector SearchVector { get; set; } = null!;

    public int DocumentId { get; set; }
    public Document Document { get; set; } = null!;

    public string?   AiFileType   { get; set; }   
    public string?   AiSummary    { get; set; }   
    public DateTime? AiAnalyzedAt { get; set; }  
}
public enum FileProcessingStatus
{
    Pending,
    Processing,
    Completed,
    Failed
}
