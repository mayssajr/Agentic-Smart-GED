using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using MiniGED.API.Data;
using MiniGED.API.Models;
using MiniGED.API.Dtos;
using System.Security.Claims;

namespace MiniGED.API.Controllers;

[Authorize]
[ApiController]
[Route("api/dashboard")]
public class DashboardController : ControllerBase
{
    private readonly ApplicationDbContext _db;

    public DashboardController(ApplicationDbContext db)
    {
        _db = db;
    }

    // ─────────────────────────────────────────────────────────────────────
    // GET /api/dashboard/stats
    // ─────────────────────────────────────────────────────────────────────

    [HttpGet("stats")]
    public async Task<IActionResult> GetStats()
    {
        var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

        var documents = await _db.Documents
            .Where(d => d.UserId == userId)
            .Include(d => d.Files)
            .ToListAsync();

        var totalFiles    = documents.Sum(d => d.Files.Count);
        var analyzedCount = documents.Count(d => d.AiAnalyzedAt != null);

        var byType = documents
            .Where(d => !string.IsNullOrEmpty(d.AiDocumentType))
            .GroupBy(d => d.AiDocumentType!)
            .ToDictionary(g => g.Key, g => g.Count());

        var allFiles = documents.SelectMany(d => d.Files).ToList();
        var byStatus = allFiles
            .GroupBy(f => f.Status.ToString())
            .ToDictionary(g => g.Key, g => g.Count());

        // Répartition des types de fichiers individuels (CV, Lettre, etc.)
        var byFileType = allFiles
            .Where(f => !string.IsNullOrEmpty(f.AiFileType))
            .GroupBy(f => f.AiFileType!)
            .ToDictionary(g => g.Key, g => g.Count());

        var recentAnalyzed = documents
            .Where(d => d.AiAnalyzedAt != null)
            .OrderByDescending(d => d.AiAnalyzedAt)
            .Take(5)
            .Select(d => new
            {
                id             = d.Id,
                title          = d.Title,
                aiDocumentType = d.AiDocumentType,
                aiAnalyzedAt   = d.AiAnalyzedAt,
            })
            .ToList();

        return Ok(new
        {
            totalDocuments  = documents.Count,
            totalFiles,
            analyzedCount,
            pendingAnalysis = documents.Count - analyzedCount,
            byType,       // types agrégés des documents
            byFileType,   // types individuels des fichiers
            byStatus,
            recentAnalyzed,
        });
    }

    // ─────────────────────────────────────────────────────────────────────
    // GET /api/dashboard/documents
    // ─────────────────────────────────────────────────────────────────────

    [HttpGet("documents")]
    public async Task<IActionResult> GetDocuments(
        [FromQuery] string? type    = null,
        [FromQuery] int     page    = 1,
        [FromQuery] int     perPage = 20)
    {
        var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

        var query = _db.Documents
            .Where(d => d.UserId == userId)
            .Include(d => d.Files)
            .AsQueryable();

        if (!string.IsNullOrWhiteSpace(type))
            query = query.Where(d => d.AiDocumentType == type);

        var total = await query.CountAsync();

        var documents = await query
            .OrderByDescending(d => d.UploadedAt)
            .Skip((page - 1) * perPage)
            .Take(perPage)
            .Select(d => new
            {
                id             = d.Id,
                title          = d.Title,
                description    = d.Description,
                uploadedAt     = d.UploadedAt,
                fileCount      = d.Files.Count,
                aiDocumentType = d.AiDocumentType ?? "Non analysé",
                aiSummaryPreview = d.AiSummary != null
                    ? d.AiSummary.Substring(0, Math.Min(150, d.AiSummary.Length))
                    : null,
                aiAnalyzedAt   = d.AiAnalyzedAt,
                isAnalyzed     = d.AiAnalyzedAt != null,
                // Types de fichiers individuels détectés
                fileTypes = d.Files
                    .Where(f => f.AiFileType != null)
                    .Select(f => new { f.Id, f.FileName, f.AiFileType })
                    .ToList(),
            })
            .ToListAsync();

        return Ok(new
        {
            total,
            page,
            perPage,
            totalPages = (int)Math.Ceiling(total / (double)perPage),
            documents,
        });
    }

    // ─────────────────────────────────────────────────────────────────────
    // GET /api/dashboard/document/{id}
    //
    // Retourne le document avec :
    //   - ai.documentType  : type agrégé (ex: "Candidature")
    //   - ai.summary       : synthèse globale structurée
    //   - files[].aiFileType : type individuel de chaque fichier
    //   - files[].aiSummary  : résumé spécialisé de chaque fichier
    // ─────────────────────────────────────────────────────────────────────

    [HttpGet("document/{id}")]
    public async Task<IActionResult> GetDocument(int id)
    {
        var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

        var document = await _db.Documents
            .Include(d => d.Files)
            .Include(d => d.Tasks)
            .FirstOrDefaultAsync(d => d.Id == id && d.UserId == userId);

        if (document == null)
            return NotFound(new { error = "Document introuvable." });

        return Ok(new
        {
            id          = document.Id,
            title       = document.Title,
            description = document.Description,
            uploadedAt  = document.UploadedAt,

            // Données IA au niveau document (agrégées)
            ai = new
            {
                documentType = document.AiDocumentType ?? "Non analysé",
                summary      = document.AiSummary,      // synthèse globale
                analyzedAt   = document.AiAnalyzedAt,
                isAnalyzed   = document.AiAnalyzedAt != null,
            },

            // Fichiers avec leurs données IA individuelles
            files = document.Files.Select(f => new
            {
                id          = f.Id,
                filename    = f.FileName,
                fileSize    = f.FileSize,
                status      = f.Status.ToString(),
                pageCount   = f.PageCount,
                // Données IA de CE fichier spécifiquement
                aiFileType  = f.AiFileType,   // ex: "CV", "Lettre de motivation"
                aiSummary   = f.AiSummary,    // résumé spécialisé selon son type
                isAnalyzed  = f.AiAnalyzedAt != null,
            }),

            tasks = document.Tasks.Select(t => new
            {
                id       = t.Id,
                title    = t.Title,
                status   = t.Status.ToString(),
                priority = t.Priority.ToString(),
                dueDate  = t.DueDate,
            }),
        });
    }

    // ─────────────────────────────────────────────────────────────────────
    // PATCH /api/dashboard/document/{id}/ai
    //
    // Stocke le résumé consolidé + type agrégé au niveau document
    // ET les données IA individuelles de chaque fichier.
    // Appelé par DocumentSummary.vue après calcul côté Python.
    // ─────────────────────────────────────────────────────────────────────
    [AllowAnonymous] 
    [HttpPatch("document/{id}/ai")]
    public async Task<IActionResult> SaveAiData(int id,
        [FromBody] SaveAiRequest request)
    {

        var document = await _db.Documents
            .Include(d => d.Files)
            .FirstOrDefaultAsync(d => d.Id == id );

        if (document == null)
            return NotFound();

        // Résumé consolidé + type agrégé au niveau document
        document.AiSummary      = request.Summary;
        document.AiDocumentType = request.DocumentType;
        document.AiAnalyzedAt   = DateTime.UtcNow;

        // Données IA individuelles par fichier
        if (request.FileSummaries != null)
        {
            foreach (var fs in request.FileSummaries)
            {
                var file = document.Files.FirstOrDefault(f => f.Id == fs.FileId);
                if (file == null) continue;

                file.AiFileType   = fs.AiFileType;
                file.AiSummary    = fs.AiSummary;
                file.AiAnalyzedAt = DateTime.UtcNow;
            }
        }

        await _db.SaveChangesAsync();
        return Ok(new { success = true });
    }
}