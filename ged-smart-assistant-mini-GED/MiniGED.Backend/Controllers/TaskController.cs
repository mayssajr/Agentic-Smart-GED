using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Security.Claims;
using MiniGED.API.Data;
using MiniGED.API.Dtos;
using MiniGED.API.Models;

namespace MiniGED.API.Controllers;

[Authorize]
[ApiController]
[Route("api/[controller]")]
public class TaskController : ControllerBase
{
    private readonly ApplicationDbContext _context;

    public TaskController(ApplicationDbContext context)
    {
        _context = context;
    }

    [HttpPost]
    public async Task<IActionResult> CreateTask([FromBody] CreateTaskDto createTaskDto)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
            return Unauthorized();

        int userId = int.Parse(userIdClaim.Value);

        // Vérifier que le document appartient bien à l'utilisateur
        var document = await _context.Documents
            .FirstOrDefaultAsync(d => d.Id == createTaskDto.DocumentId && d.UserId == userId);

        if (document == null)
            return BadRequest(new { message = "Document introuvable ou accès refusé." });

        var task = new DocumentTask
        {
            Title = createTaskDto.Title,
            Description = createTaskDto.Description,
            Priority = createTaskDto.Priority,
            DueDate = createTaskDto.DueDate,
            DocumentId = createTaskDto.DocumentId,
            Status = DocumentTaskStatus.Pending,
            CreatedAt = DateTime.UtcNow,
            AssignedUserId   = createTaskDto.AssignedUserId,
            AssignedUserName = createTaskDto.AssignedUserName,
        };

        _context.DocumentTasks.Add(task);
        await _context.SaveChangesAsync();

        var taskDto = new TaskDto
        {
            Id = task.Id,
            Title = task.Title,
            Description = task.Description,
            Status = task.Status,
            Priority = task.Priority,
            DueDate = task.DueDate,
            CreatedAt = task.CreatedAt,
            UpdatedAt = task.UpdatedAt,
            DocumentId = task.DocumentId,
            AssignedUserId   = task.AssignedUserId,
            AssignedUserName = task.AssignedUserName,
        };

        return CreatedAtAction(nameof(GetTaskById), new { id = task.Id }, taskDto);
    }

    [HttpGet]
    public async Task<IActionResult> GetAllTasks()
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
            return Unauthorized();

        int userId = int.Parse(userIdClaim.Value);

        var tasks = await _context.DocumentTasks
            .Where(t => t.Document.UserId == userId)
            .OrderByDescending(t => t.CreatedAt)
            .Select(t => new TaskDto
            {
                Id = t.Id,
                Title = t.Title,
                Description = t.Description,
                Status = t.Status,
                Priority = t.Priority,
                DueDate = t.DueDate,
                CreatedAt = t.CreatedAt,
                UpdatedAt = t.UpdatedAt,
                DocumentId = t.DocumentId,
                AssignedUserId   = t.AssignedUserId,
                AssignedUserName = t.AssignedUserName,
            })
            .ToListAsync();

        return Ok(tasks);
    }

    [HttpGet("document/{documentId}")]
    public async Task<IActionResult> GetTasksByDocument(int documentId)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
            return Unauthorized();

        int userId = int.Parse(userIdClaim.Value);

        // Vérifier que le document appartient bien à l'utilisateur
        var document = await _context.Documents
            .FirstOrDefaultAsync(d => d.Id == documentId && d.UserId == userId);

        if (document == null)
            return BadRequest(new { message = "Document introuvable ou accès refusé." });

        var tasks = await _context.DocumentTasks
            .Where(t => t.DocumentId == documentId)
            .OrderBy(t => t.Priority)
            .ThenBy(t => t.DueDate)
            .Select(t => new TaskDto
            {
                Id = t.Id,
                Title = t.Title,
                Description = t.Description,
                Status = t.Status,
                Priority = t.Priority,
                DueDate = t.DueDate,
                CreatedAt = t.CreatedAt,
                UpdatedAt = t.UpdatedAt,
                DocumentId = t.DocumentId,
                AssignedUserId   = t.AssignedUserId,
                AssignedUserName = t.AssignedUserName,
            })
            .ToListAsync();

        return Ok(tasks);
    }

    [HttpGet("{id}")]
    public async Task<IActionResult> GetTaskById(int id)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
            return Unauthorized();

        int userId = int.Parse(userIdClaim.Value);

        var task = await _context.DocumentTasks
            .Include(t => t.Document)
            .FirstOrDefaultAsync(t => t.Id == id && t.Document.UserId == userId);

        if (task == null)
            return NotFound(new { message = "Tâche introuvable ou accès refusé." });

        var taskDto = new TaskDto
        {
            Id = task.Id,
            Title = task.Title,
            Description = task.Description,
            Status = task.Status,
            Priority = task.Priority,
            DueDate = task.DueDate,
            CreatedAt = task.CreatedAt,
            UpdatedAt = task.UpdatedAt,
            DocumentId = task.DocumentId,
            AssignedUserId   = task.AssignedUserId,
            AssignedUserName = task.AssignedUserName,
        };

        return Ok(taskDto);
    }

    [HttpPut("{id}")]
    public async Task<IActionResult> UpdateTask(int id, [FromBody] UpdateTaskDto updateTaskDto)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
            return Unauthorized();

        int userId = int.Parse(userIdClaim.Value);

        var task = await _context.DocumentTasks
            .Include(t => t.Document)
            .FirstOrDefaultAsync(t => t.Id == id && t.Document.UserId == userId);

        if (task == null)
            return NotFound(new { message = "Tâche introuvable ou accès refusé." });

        // Mettre à jour uniquement les propriétés fournies
        if (updateTaskDto.Title != null)
            task.Title = updateTaskDto.Title;
        
        if (updateTaskDto.Description != null)
            task.Description = updateTaskDto.Description;
        
        if (updateTaskDto.Status.HasValue)
            task.Status = updateTaskDto.Status.Value;
        
        if (updateTaskDto.Priority.HasValue)
            task.Priority = updateTaskDto.Priority.Value;
        
        if (updateTaskDto.DueDate.HasValue)
            task.DueDate = updateTaskDto.DueDate.Value;
        
        if (updateTaskDto.AssignedUserId.HasValue || updateTaskDto.AssignedUserName != null)
        {
            task.AssignedUserId   = updateTaskDto.AssignedUserId;
            task.AssignedUserName = updateTaskDto.AssignedUserName;
        }

        task.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();

        var taskDto = new TaskDto
        {
            Id = task.Id,
            Title = task.Title,
            Description = task.Description,
            Status = task.Status,
            Priority = task.Priority,
            DueDate = task.DueDate,
            CreatedAt = task.CreatedAt,
            UpdatedAt = task.UpdatedAt,
            DocumentId = task.DocumentId,
            AssignedUserId   = task.AssignedUserId,
            AssignedUserName = task.AssignedUserName,
        };

        return Ok(taskDto);
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteTask(int id)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
            return Unauthorized();

        int userId = int.Parse(userIdClaim.Value);

        var task = await _context.DocumentTasks
            .Include(t => t.Document)
            .FirstOrDefaultAsync(t => t.Id == id && t.Document.UserId == userId);

        if (task == null)
            return NotFound(new { message = "Tâche introuvable ou accès refusé." });

        _context.DocumentTasks.Remove(task);
        await _context.SaveChangesAsync();

        return Ok(new { message = "Tâche supprimée avec succès." });
    }

    [HttpPatch("{id}/status")]
    public async Task<IActionResult> UpdateTaskStatus(int id, [FromBody] UpdateTaskStatusDto updateStatusDto)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
            return Unauthorized();

        int userId = int.Parse(userIdClaim.Value);

        var task = await _context.DocumentTasks
            .Include(t => t.Document)
            .FirstOrDefaultAsync(t => t.Id == id && t.Document.UserId == userId);

        if (task == null)
            return NotFound(new { message = "Tâche introuvable ou accès refusé." });

        task.Status = updateStatusDto.Status;
        task.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();

        return Ok(new { message = "Statut de la tâche mis à jour avec succès." });
    }
}

public class UpdateTaskStatusDto
{
    public DocumentTaskStatus Status { get; set; }
}
