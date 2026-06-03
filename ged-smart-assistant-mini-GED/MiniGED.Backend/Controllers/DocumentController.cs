using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using MiniGED.API.Data;
using MiniGED.API.Dtos;
using MiniGED.API.Interfaces;
using MiniGED.API.Models;
using System.Security.Claims;

namespace MiniGED.API.Controllers;

[Authorize]
[ApiController]
[Route("api/[controller]")]
public class DocumentController : ControllerBase
{
    private readonly ApplicationDbContext _context;
    private readonly IDocumentSearchService _documentSearchService;

    public DocumentController(
        ApplicationDbContext context,
        IDocumentSearchService documentSearchService)
    {
        _context = context;
        _documentSearchService = documentSearchService;
    }

    [HttpPost("add")]
    public async Task<IActionResult> AddNewDocument([FromBody] DocumentDto documentDto)
    {
        var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);
        var user = await _context.Users.FindAsync(userId);
        if (user == null)
        {
            return Unauthorized("User Not Authenticated");
        }

        var newDocument = new Document
        {
            Title = documentDto.Title,
            Description = documentDto.Description,
            UserId = userId
        };

        _context.Documents.Add(newDocument);
        await _context.SaveChangesAsync();
        return Ok("done");
    }

    [HttpGet]
    public async Task<IActionResult> GetUserDocuments()
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
        {
            return Unauthorized();
        }

        var userId = int.Parse(userIdClaim.Value);
        var documents = await _context.Documents
            .Where(d => d.UserId == userId)
            .Include(d => d.Files)
            .Select(d => new
            {
                d.Id,
                d.Title,
                d.Description,
                d.UploadedAt
            })
            .ToListAsync();

        return Ok(documents);
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteDocument(int id)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
        {
            return Unauthorized();
        }

        var userId = int.Parse(userIdClaim.Value);
        var document = await _context.Documents
            .Include(d => d.Files)
            .FirstOrDefaultAsync(d => d.Id == id && d.UserId == userId);

        if (document == null)
        {
            return NotFound(new { message = "Document introuvable ou accès refusé." });
        }

        _context.Documents.Remove(document);
        await _context.SaveChangesAsync();

        return Ok(new { message = "Document supprimé avec succès." });
    }

    [HttpPut("{id}")]
    public async Task<IActionResult> UpdateDocument(int id, [FromBody] DocumentDto documentDto)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
        {
            return Unauthorized();
        }

        var userId = int.Parse(userIdClaim.Value);
        var document = await _context.Documents
            .FirstOrDefaultAsync(d => d.Id == id && d.UserId == userId);

        if (document == null)
        {
            return NotFound(new { message = "Document introuvable ou accès refusé." });
        }

        document.Title = documentDto.Title;
        document.Description = documentDto.Description;
        document.UpdateDate = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        await _documentSearchService.RefreshDocumentSearchableTextAsync(document.Id);

        return Ok(new { message = "Document modifié avec succès." });
    }

    [HttpGet("{id}")]
    public async Task<IActionResult> GetDocumentById(int id)
    {
        var userIdClaim = User.FindFirst(ClaimTypes.NameIdentifier);
        if (userIdClaim == null)
        {
            return Unauthorized();
        }

        var userId = int.Parse(userIdClaim.Value);
        var document = await _context.Documents
            .Include(d => d.Files)
            .FirstOrDefaultAsync(d => d.Id == id && d.UserId == userId);

        if (document == null)
        {
            return NotFound(new { message = "Document introuvable ou accès refusé." });
        }

        return Ok(new
        {
            document.Id,
            document.Title,
            document.Description,
            document.UploadedAt,
            Files = document.Files.Select(f => new
            {
                f.Id,
                f.FileName,
                f.FilePath,
                f.FileSize,
                f.Status,
                f.PageCount
            }).ToList()
        });
    }
}
