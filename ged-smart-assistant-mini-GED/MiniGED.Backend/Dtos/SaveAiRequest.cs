namespace MiniGED.API.Dtos;

public class SaveAiRequest
{
    public string? Summary      { get; set; }
    public string? DocumentType { get; set; }
    public List<FileSummaryItem>? FileSummaries { get; set; }
}

public class FileSummaryItem
{
    public int FileId { get; set; }
    public string Filename { get; set; } = string.Empty;
    public string? AiFileType { get; set; }
    public string? AiSummary { get; set; }
}