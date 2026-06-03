using System.Security.Claims;
using Hangfire;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using MiniGED.API.Data;
using MiniGED.API.Dtos;
using MiniGED.API.Interfaces;
using MiniGED.API.Models;
using Microsoft.EntityFrameworkCore;

namespace MiniGED.API.Controllers;

[Authorize]
[ApiController]
[Route("api/document")]
public class DocumentFileController : ControllerBase
{
    private readonly ApplicationDbContext _context;
    private readonly IFileService _fileService;
    private readonly IDocumentSearchService _documentSearchService;

    public DocumentFileController(
        ApplicationDbContext context,
        IFileService fileService,
        IDocumentSearchService documentSearchService)
    {
        _context = context;
        _fileService = fileService;
        _documentSearchService = documentSearchService;
    }

    [HttpGet("{id}/files")]
    public async Task<IActionResult> GetDocumentFiles(int id)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
        {
            return Unauthorized();
        }

        var userId = int.Parse(userIdClaim.Value);
        var document = await _context.Documents.FindAsync(id);
        if (document == null || document.UserId != userId)
        {
            return Unauthorized();
        }

        var documentFiles = _context.DocumentFiles
            .Where(x => x.DocumentId == id)
            .Select(d => new DocFileResponse
            {
                Id = d.Id,
                FileName = d.FileName,
                FileSize = d.FileSize,
                FilePath = d.FilePath
            })
            .ToList();

        if (documentFiles.Count == 0)
        {
            return NotFound("No Files found for the given DocumentId");
        }

        return Ok(documentFiles);
    }

    [HttpPost("upload")]
    public async Task<IActionResult> Upload([FromForm] FileUploadModel model)
    {
        try
        {
            var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
            if (userIdClaim == null || !int.TryParse(userIdClaim.Value, out var userId))
            {
                return Unauthorized();
            }

            var user = await _context.Users.FindAsync(userId);
            if (user == null)
            {
                return BadRequest("Invalid user");
            }

            if (model.Files == null || model.Files.Count == 0)
            {
                return BadRequest("No files selected");
            }

            var document = await _context.Documents.FindAsync(model.DocumentId);
            if (document == null)
            {
                return BadRequest("Document doesn't exist");
            }

            if (user.Id != document.UserId)
            {
                return Unauthorized("Not authorized to update this document");
            }

            foreach (var file in model.Files)
            {
                if (file.Length == 0)
                {
                    continue;
                }

                var sanitizedFileName = Path.GetFileNameWithoutExtension(file.FileName)
                    + Path.GetExtension(file.FileName).ToLower();

                var newDocFile = new DocumentFile
                {
                    FileName = sanitizedFileName,
                    FileSize = file.Length,
                    Status = FileProcessingStatus.Pending,
                    FilePath = string.Empty,
                    DocumentId = model.DocumentId
                };

                _context.DocumentFiles.Add(newDocFile);
                await _context.SaveChangesAsync();

                var result = await _fileService.UploadFile(newDocFile, file);
                if (result == "file not selected" || result == "file Already Exists")
                {
                    _context.DocumentFiles.Remove(newDocFile);
                    await _context.SaveChangesAsync();
                    return BadRequest($"Failed to upload {file.FileName}, {result}");
                }

                newDocFile.FilePath = result;
                await _context.SaveChangesAsync();

                try
                {
                    BackgroundJob.Enqueue<IFileProcessingJob>(job => job.ProcessFileAsync(
                        new FileProcessingPayload
                        {
                            DocumentId = newDocFile.DocumentId,
                            FileId = newDocFile.Id,
                            UserId = user.Id
                        }));
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"File processing job enqueue failed: {ex}");
                    return StatusCode(StatusCodes.Status500InternalServerError, ex.Message);
                }
            }

            return Ok(new
            {
                success = true,
                message = "All files uploaded successfully."
            });
        }
        catch (Exception e)
        {
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = e.Message });
        }
    }

    [AllowAnonymous]
    [HttpGet("pdf/{id}")]
    public IActionResult Get(int id)
    {
        var folderName = Path.Combine("Resource", "AllFiles");
        var pathToSave = Path.Combine(Directory.GetCurrentDirectory(), folderName);
        var fullPath = Path.Combine(pathToSave, $"{id}.pdf");

        if (!System.IO.File.Exists(fullPath))
        {
            return NotFound($"The requested version of the file does not exist. {fullPath}");
        }

        var stream = new FileStream(fullPath, FileMode.Open, FileAccess.ReadWrite, FileShare.ReadWrite);
        return File(stream, "application/pdf");
    }

    [HttpDelete("delete/{id}")]
    public IActionResult Delete(int id)
    {
        var result = _context.DocumentFiles.Find(id);
        if (result == null)
        {
            return NotFound("File Not Found");
        }

        _context.DocumentFiles.Remove(result);

        var isDeleted = _fileService.DeleteFile(id);
        if (!isDeleted)
        {
            return StatusCode(StatusCodes.Status500InternalServerError, "Unable to delete");
        }

        _context.SaveChanges();
        return Ok(new
        {
            success = true,
            message = "File Deleted Successfully !"
        });
    }

    [HttpPost("search")]
    public async Task<IActionResult> Search([FromBody] DocumentSearchRequest request)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null || !int.TryParse(userIdClaim.Value, out var userId))
        {
            return Unauthorized();
        }

        var user = await _context.Users.FindAsync(userId);
        if (user == null)
        {
            return BadRequest("Invalid user");
        }

        var results = await _documentSearchService.SearchAsync(request, userId);
        return Ok(new
        {
            success = true,
            results
        });
    }
    // ── Endpoint 1 : téléchargement bytes d'un fichier (par file_id) ─────────────
    [Authorize]
    [HttpGet("{documentId}/file/{fileId}/bytes")]
    public IActionResult GetFileBytes(int documentId, int fileId)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null || !int.TryParse(userIdClaim.Value, out var userId))
        {
            return Unauthorized();
        }
    
        // Vérifier que le document appartient à l'utilisateur
        var document = _context.Documents.Find(documentId);
        if (document == null || document.UserId != userId)
        {
            return NotFound(new { message = "Document introuvable ou accès refusé." });
        }
    
        var fileRecord = _context.DocumentFiles
            .FirstOrDefault(f => f.Id == fileId && f.DocumentId == documentId);
    
        if (fileRecord == null)
        {
            return NotFound(new { message = "Fichier introuvable." });
        }
    
        var folderName = Path.Combine("Resource", "AllFiles");
        var pathToSave = Path.Combine(Directory.GetCurrentDirectory(), folderName);
        var fullPath   = Path.Combine(pathToSave, $"{fileId}.pdf");
    
        if (!System.IO.File.Exists(fullPath))
        {
            return NotFound(new { message = $"Fichier physique introuvable: {fullPath}" });
        }
    
        var stream = new FileStream(fullPath, FileMode.Open, FileAccess.Read, FileShare.Read);
        return File(stream, "application/pdf", fileRecord.FileName);
    }
    
    
    // ── Endpoint 2 : téléchargement du premier fichier d'un document ──────────────
    [Authorize]
    [HttpGet("{documentId}/download")]
    public IActionResult DownloadDocument(int documentId)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null || !int.TryParse(userIdClaim.Value, out var userId))
        {
            return Unauthorized();
        }
    
        var document = _context.Documents
            .Include(d => d.Files)
            .FirstOrDefault(d => d.Id == documentId && d.UserId == userId);
    
        if (document == null)
        {
            return NotFound(new { message = "Document introuvable ou accès refusé." });
        }
    
        // Prendre le premier fichier PDF
        var fileRecord = document.Files
            .OrderBy(f => f.Id)
            .FirstOrDefault(f => f.Status == FileProcessingStatus.Completed);
    
        if (fileRecord == null)
        {
            return NotFound(new { message = "Aucun fichier disponible pour ce document." });
        }
    
        var folderName = Path.Combine("Resource", "AllFiles");
        var pathToSave = Path.Combine(Directory.GetCurrentDirectory(), folderName);
        var fullPath   = Path.Combine(pathToSave, $"{fileRecord.Id}.pdf");
    
        if (!System.IO.File.Exists(fullPath))
        {
            return NotFound(new { message = "Fichier physique introuvable." });
        }
    
        var stream = new FileStream(fullPath, FileMode.Open, FileAccess.Read, FileShare.Read);
        return File(stream, "application/pdf", fileRecord.FileName);
    }
}
