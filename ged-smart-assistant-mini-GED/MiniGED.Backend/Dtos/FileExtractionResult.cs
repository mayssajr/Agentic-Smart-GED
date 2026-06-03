namespace MiniGED.API.Dtos;

public class FileExtractionResult
{
    public string ExtractedText { get; set; } = string.Empty;
    public int PageCount { get; set; }
}
