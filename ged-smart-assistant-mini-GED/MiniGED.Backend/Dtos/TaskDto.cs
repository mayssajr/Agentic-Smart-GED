using System.ComponentModel.DataAnnotations;
using MiniGED.API.Models;

namespace MiniGED.API.Dtos
{
    public class TaskDto
    {
        public int Id { get; set; }
        
        [Required]
        public string Title { get; set; } = string.Empty;
        
        public string? Description { get; set; }
        
        public DocumentTaskStatus Status { get; set; } = DocumentTaskStatus.Pending;
        
        public DocumentTaskPriority Priority { get; set; } = DocumentTaskPriority.Medium;
        
        public DateTime? DueDate { get; set; }
        
        public DateTime CreatedAt { get; set; }
        
        public DateTime? UpdatedAt { get; set; }
        
        public int DocumentId { get; set; }

        public int?    AssignedUserId   { get; set; }
        public string? AssignedUserName { get; set; }
    }

    public class CreateTaskDto
    {
        [Required]
        public string Title { get; set; } = string.Empty;
        
        public string? Description { get; set; }
        
        public DocumentTaskPriority Priority { get; set; } = DocumentTaskPriority.Medium;
        
        public DateTime? DueDate { get; set; }
        
        [Required]
        public int DocumentId { get; set; }

        public int?    AssignedUserId   { get; set; }
        public string? AssignedUserName { get; set; }
    }

    public class UpdateTaskDto
    {
        public string? Title { get; set; }
        
        public string? Description { get; set; }
        
        public DocumentTaskStatus? Status { get; set; }
        
        public DocumentTaskPriority? Priority { get; set; }
        
        public DateTime? DueDate { get; set; }

        public int?    AssignedUserId   { get; set; }
        public string? AssignedUserName { get; set; }
    }
}
