using MiniGED.API.Models;

namespace MiniGED.API.Dtos;

public class DocumentSearchResultDto
{
    public int FileId { get; set; }
    public string FileName { get; set; } = string.Empty;
    public FileProcessingStatus FileStatus { get; set; }
    public int DocumentId { get; set; }
    public string DocumentTitle { get; set; } = string.Empty;
    public string DocumentDescription { get; set; } = string.Empty;
    public DateTime UploadedAt { get; set; }
    public string Snippet { get; set; } = string.Empty;
    public double Rank { get; set; }
}
