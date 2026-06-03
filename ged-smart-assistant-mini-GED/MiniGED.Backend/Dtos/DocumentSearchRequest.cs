using MiniGED.API.Models;

namespace MiniGED.API.Dtos;

public class DocumentSearchRequest
{
    public string? Query { get; set; }
    public List<int>? DocumentIds { get; set; }
    public List<FileProcessingStatus>? FileStatuses { get; set; }
    public DateTime? UploadedFrom { get; set; }
    public DateTime? UploadedTo { get; set; }
    public List<DocumentTaskStatus>? TaskStatuses { get; set; }
    public List<DocumentTaskPriority>? TaskPriorities { get; set; }
    public DateTime? TaskDueFrom { get; set; }
    public DateTime? TaskDueTo { get; set; }
    public int Page { get; set; } = 1;
    public int PageSize { get; set; } = 10;
    public DocumentSearchSort Sort { get; set; } = DocumentSearchSort.Relevance;
}

public enum DocumentSearchSort
{
    Relevance = 0,
    UploadedAt = 1
}
