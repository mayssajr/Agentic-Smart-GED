using System.ComponentModel.DataAnnotations;

namespace MiniGED.API.Models
{
    public class DocumentTask
    {
        public int Id { get; set; }
        
        [Required]
        public string Title { get; set; } = string.Empty;
        
        public string? Description { get; set; }
        
        public DocumentTaskStatus Status { get; set; } = DocumentTaskStatus.Pending;
        
        public DocumentTaskPriority Priority { get; set; } = DocumentTaskPriority.Medium;
        
        public DateTime? DueDate { get; set; }
        
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
        
        public DateTime? UpdatedAt { get; set; }

        public int? AssignedUserId { get; set; }

        public string? AssignedUserName { get; set; }

        // Foreign key to Document
        public int DocumentId { get; set; }
        
        // Navigation property
        public Document Document { get; set; } = null!;
    }

    public enum DocumentTaskStatus
    {
        Pending = 0,
        InProgress = 1,
        Completed = 2,
        Cancelled = 3
    }

    public enum DocumentTaskPriority
    {
        Low = 0,
        Medium = 1,
        High = 2,
        Urgent = 3
    }
}
