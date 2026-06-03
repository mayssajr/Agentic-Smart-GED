using System.Security.Claims;
using System.Text;
using System.Text.Json;
using Hangfire;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using MiniGED.API.Data;
using MiniGED.API.Dtos;
using MiniGED.API.Interfaces;
using MiniGED.API.Models;

namespace MiniGED.API.Controllers;

[ApiController]
[Route("api/recruitment")]
public class RecruitmentController : ControllerBase
{
    private readonly ApplicationDbContext           _db;
    private readonly IFileService                   _fileService;
    private readonly IHttpClientFactory             _http;
    private readonly ILogger<RecruitmentController> _logger;

    private const string AcePythonUrl = "http://localhost:8000";

    public RecruitmentController(
        ApplicationDbContext            db,
        IFileService                    fileService,
        IHttpClientFactory              http,
        ILogger<RecruitmentController>  logger)
    {
        _db          = db;
        _fileService = fileService;
        _http        = http;
        _logger      = logger;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // POST /api/recruitment/apply
    // ─────────────────────────────────────────────────────────────────────────
    [AllowAnonymous]
    [HttpPost("apply")]
    public async Task<IActionResult> Apply([FromForm] ApplyRequest request)
    {
        if (request.Files is null || request.Files.Count == 0)
            return BadRequest(new { error = "Au moins un fichier est requis" });

        if (string.IsNullOrWhiteSpace(request.CandidateName))
            return BadRequest(new { error = "candidate_name est requis" });

        var userId = User.FindFirst(ClaimTypes.NameIdentifier) != null
            ? int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value)
            : 1;

        var document = new Document
        {
            Title       = $"Candidature — {request.CandidateName} — {request.Position}",
            Description = $"Dossier reçu depuis la plateforme RH externe. " +
                          $"Poste : {request.Position}. Email : {request.CandidateEmail}",
            UserId = userId,
        };
        _db.Documents.Add(document);
        await _db.SaveChangesAsync();

        var uploadedFiles = new List<int>();

        foreach (var file in request.Files)
        {
            if (file.Length == 0) continue;

            var docFile = new DocumentFile
            {
                FileName   = file.FileName,
                FileSize   = file.Length,
                Status     = FileProcessingStatus.Pending,
                FilePath   = string.Empty,
                DocumentId = document.Id,
            };
            _db.DocumentFiles.Add(docFile);
            await _db.SaveChangesAsync();

            var uploadResult = await _fileService.UploadFile(docFile, file);
            if (uploadResult is "file not selected" or "file Already Exists")
            {
                _db.DocumentFiles.Remove(docFile);
                await _db.SaveChangesAsync();
                continue;
            }

            docFile.FilePath = uploadResult;
            await _db.SaveChangesAsync();

            BackgroundJob.Enqueue<IFileProcessingJob>(job => job.ProcessFileAsync(
                new FileProcessingPayload
                {
                    DocumentId = document.Id,
                    FileId     = docFile.Id,
                    UserId     = userId,
                }));

            uploadedFiles.Add(docFile.Id);
        }

        if (uploadedFiles.Count == 0)
        {
            _db.Documents.Remove(document);
            await _db.SaveChangesAsync();
            return BadRequest(new { error = "Aucun fichier uploadé avec succès" });
        }

        var candidate = new CandidateApplication
        {
            CandidateName  = request.CandidateName,
            CandidateEmail = request.CandidateEmail,
            CandidatePhone = request.CandidatePhone,
            Position       = request.Position,
            DocumentId     = document.Id,
            Status         = CandidateStatus.Recu,
        };
        _db.CandidateApplications.Add(candidate);
        await _db.SaveChangesAsync();

        return Ok(new
        {
            success       = true,
            candidateId   = candidate.Id,
            documentId    = document.Id,
            filesUploaded = uploadedFiles.Count,
            status        = candidate.Status.ToString(),
            nextStep      = $"Attendre 5-10s puis POST http://localhost:8000/analyze-document/{document.Id}",
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // GET /api/recruitment/applications
    // ─────────────────────────────────────────────────────────────────────────
    [AllowAnonymous]
    [HttpGet("applications")]
    public async Task<IActionResult> GetApplications(
        [FromQuery] string? status   = null,
        [FromQuery] string? position = null,
        [FromQuery] int     page     = 1,
        [FromQuery] int     pageSize = 20)
    {
        var query = _db.CandidateApplications
            .Include(c => c.Document)
                .ThenInclude(d => d.Files)
            .AsQueryable();

        if (!string.IsNullOrWhiteSpace(status) &&
            Enum.TryParse<CandidateStatus>(status, true, out var s))
            query = query.Where(c => c.Status == s);

        if (!string.IsNullOrWhiteSpace(position))
            query = query.Where(c =>
                c.Position.ToLower().Contains(position.ToLower()));

        var total = await query.CountAsync();

        var candidates = await query
            .OrderByDescending(c => c.CreateDate)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .Select(c => new
            {
                candidateId      = c.Id,
                name             = c.CandidateName,
                email            = c.CandidateEmail,
                phone            = c.CandidatePhone,
                position         = c.Position,
                status           = c.Status.ToString(),
                notes            = c.Notes,
                createdAt        = c.CreateDate,
                documentId       = c.DocumentId,
                aiScore          = c.AiScore,
                aiRecommendation = c.AiRecommendation,
                aiDocumentType   = c.Document != null ? c.Document.AiDocumentType : null,
                aiSummaryPreview = c.Document != null && c.Document.AiSummary != null
                    ? c.Document.AiSummary.Substring(0, Math.Min(200, c.Document.AiSummary.Length))
                    : null,
                aiAnalyzedAt = c.Document != null ? c.Document.AiAnalyzedAt : null,
                isAnalyzed   = c.Document != null && c.Document.AiAnalyzedAt != null,
                fileCount    = c.Document != null ? c.Document.Files.Count : 0,
                fileTypes    = c.Document != null
                    ? c.Document.Files
                        .Where(f => f.AiFileType != null)
                        .Select(f => new { f.Id, f.FileName, f.AiFileType })
                        .ToList()
                    : null,
            })
            .ToListAsync();

        return Ok(new
        {
            total,
            page,
            pageSize,
            totalPages = (int)Math.Ceiling(total / (double)pageSize),
            candidates,
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // GET /api/recruitment/application/{id}
    // ─────────────────────────────────────────────────────────────────────────
    [AllowAnonymous]
    [HttpGet("application/{id}")]
    public async Task<IActionResult> GetApplication(int id)
    {
        var c = await _db.CandidateApplications
            .Include(x => x.Document)
                .ThenInclude(d => d.Files)
            .FirstOrDefaultAsync(x => x.Id == id);

        if (c is null)
            return NotFound(new { error = $"Candidature {id} introuvable" });

        return Ok(new
        {
            candidateId      = c.Id,
            name             = c.CandidateName,
            email            = c.CandidateEmail,
            phone            = c.CandidatePhone,
            position         = c.Position,
            status           = c.Status.ToString(),
            notes            = c.Notes,
            createdAt        = c.CreateDate,
            aiScore          = c.AiScore,
            aiRecommendation = c.AiRecommendation,
            document         = c.Document == null ? null : new
            {
                id             = c.Document.Id,
                title          = c.Document.Title,
                aiDocumentType = c.Document.AiDocumentType,
                aiSummary      = c.Document.AiSummary,
                aiAnalyzedAt   = c.Document.AiAnalyzedAt,
                isAnalyzed     = c.Document.AiAnalyzedAt != null,
                files          = c.Document.Files.Select(f => new
                {
                    id         = f.Id,
                    filename   = f.FileName,
                    fileSize   = f.FileSize,
                    status     = f.Status.ToString(),
                    pageCount  = f.PageCount,
                    aiFileType = f.AiFileType,
                    aiSummary  = f.AiSummary,
                    isAnalyzed = f.AiAnalyzedAt != null,
                }),
            },
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PATCH /api/recruitment/application/{id}/status
    //
    // NOUVEAU : accepte RhNotes = [{ sign: "+"/"-", text: "..." }]
    // Les notes sont :
    //   1. Formatées et stockées dans candidate.Notes (lisible par le RH)
    //   2. Transmises à ACE en JSON structuré pour apprentissage précis
    // ─────────────────────────────────────────────────────────────────────────
    [AllowAnonymous]
    [HttpPatch("application/{id}/status")]
    public async Task<IActionResult> UpdateStatus(int id,
        [FromBody] UpdateCandidateStatusRequest request)
    {
        if (!Enum.TryParse<CandidateStatus>(request.Status, true, out var newStatus))
            return BadRequest(new
            {
                error = $"Statut invalide : '{request.Status}'",
                valid = Enum.GetNames<CandidateStatus>(),
            });

        var candidate = await _db.CandidateApplications
            .Include(c => c.Document)
            .FirstOrDefaultAsync(c => c.Id == id);

        if (candidate is null)
            return NotFound(new { error = $"Candidature {id} introuvable" });

        var previousStatus = candidate.Status;
        candidate.Status   = newStatus;

        // ── Formater les notes +/- pour stockage lisible ──────────────────────
        // Format final stocké dans candidate.Notes :
        //   + Maîtrise FreeRTOS confirmée en production
        //   - Pas d'expérience DO-178C
        //   Note libre : ...
        var noteParts = new List<string>();

        if (request.RhNotes.Any())
        {
            foreach (var n in request.RhNotes)
            {
                if (!string.IsNullOrWhiteSpace(n.Text))
                    noteParts.Add($"{n.Sign} {n.Text.Trim()}");
            }
        }

        if (!string.IsNullOrWhiteSpace(request.Notes))
            noteParts.Add($"Note : {request.Notes.Trim()}");

        if (noteParts.Any())
            candidate.Notes = string.Join("\n", noteParts);

        await _db.SaveChangesAsync();

        _ = NotifyAceOverrideAsync(candidate, previousStatus, newStatus,
                                   candidate.Notes ?? "", request.RhNotes);

        return Ok(new
        {
            candidateId = candidate.Id,
            name        = candidate.CandidateName,
            status      = candidate.Status.ToString(),
            notes       = candidate.Notes,
            updatedAt   = candidate.UpdateDate,
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // GET /api/recruitment/stats
    // ─────────────────────────────────────────────────────────────────────────
    [AllowAnonymous]
    [HttpGet("stats")]
    public async Task<IActionResult> GetStats()
    {
        var candidates = await _db.CandidateApplications
            .Include(c => c.Document)
                .ThenInclude(d => d.Files)
            .ToListAsync();

        return Ok(new
        {
            total      = candidates.Count,
            byStatus   = candidates
                .GroupBy(c => c.Status.ToString())
                .ToDictionary(g => g.Key, g => g.Count()),
            byPosition = candidates
                .GroupBy(c => c.Position)
                .ToDictionary(g => g.Key, g => g.Count()),
            analyzedCount  = candidates.Count(c => c.Document?.AiAnalyzedAt != null),
            byDocumentType = candidates
                .Where(c => c.Document?.AiDocumentType != null)
                .GroupBy(c => c.Document!.AiDocumentType!)
                .ToDictionary(g => g.Key, g => g.Count()),
            byFileType = candidates
                .Where(c => c.Document?.Files != null)
                .SelectMany(c => c.Document!.Files)
                .Where(f => f.AiFileType != null)
                .GroupBy(f => f.AiFileType!)
                .ToDictionary(g => g.Key, g => g.Count()),
            withAiScore = candidates.Count(c => c.AiScore.HasValue),
            avgAiScore  = candidates.Where(c => c.AiScore.HasValue)
                                    .Select(c => c.AiScore!.Value)
                                    .DefaultIfEmpty(0)
                                    .Average(),
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PATCH /api/recruitment/application/{id}/ai-score
    // ─────────────────────────────────────────────────────────────────────────
    [AllowAnonymous]
    [HttpPatch("application/{id}/ai-score")]
    public async Task<IActionResult> UpdateAiScore(int id,
        [FromBody] UpdateAiScoreRequest request)
    {
        var candidate = await _db.CandidateApplications.FindAsync(id);
        if (candidate is null)
            return NotFound(new { error = $"Candidature {id} introuvable" });

        candidate.AiScore          = request.AiScore;
        candidate.AiRecommendation = request.AiRecommendation;
        await _db.SaveChangesAsync();

        return Ok(new
        {
            candidateId      = candidate.Id,
            aiScore          = candidate.AiScore,
            aiRecommendation = candidate.AiRecommendation,
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // MÉTHODE PRIVÉE — Notification ACE avec RhNotes structurées
    //
    // Payload envoyé à POST /ace/override :
    // {
    //   candidate_id, position, ai_score, ai_status, human_status,
    //   notes: "texte formaté",
    //   rh_notes: [{ sign: "+", text: "..." }, { sign: "-", text: "..." }]
    // }
    //
    // Le Generator ACE lit rh_notes pour comprendre POURQUOI le RH a décidé
    // et crée des bullets plus précis dans le playbook.
    // ─────────────────────────────────────────────────────────────────────────
    private async Task NotifyAceOverrideAsync(
        CandidateApplication candidate,
        CandidateStatus      previousStatus,
        CandidateStatus      newStatus,
        string               notes,
        List<RhNote>         rhNotes)
    {
        try
        {
            // Score IA : champ dédié en priorité, fallback sur AiSummary JSON
            var aiScore = candidate.AiScore ?? 0;
            var aiRec   = candidate.AiRecommendation ?? "ListeAttente";

            if (aiScore == 0 && candidate.Document?.AiSummary is not null)
            {
                try
                {
                    using var doc = JsonDocument.Parse(candidate.Document.AiSummary);
                    if (doc.RootElement.TryGetProperty("score", out var scoreEl))
                        aiScore = scoreEl.GetInt32();
                    if (doc.RootElement.TryGetProperty("recommendation", out var recEl))
                        aiRec = recEl.GetString() ?? "ListeAttente";
                }
                catch { }
            }

            var userId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value
                      ?? User.FindFirst(ClaimTypes.Name)?.Value
                      ?? User.FindFirst(ClaimTypes.Email)?.Value
                      ?? "anonymous";

            // ── Construire le payload ACE ──────────────────────────────────────

            var payload = new
            {
                candidate_id      = candidate.Id,
                candidate_name    = candidate.CandidateName,
                position          = candidate.Position,
                ai_score          = aiScore,
                ai_recommendation = aiRec,
                ai_status         = previousStatus.ToString(),
                human_status      = newStatus.ToString(),
                user_id           = userId,
                notes             = notes,
                rh_notes          = rhNotes.Select(n => new
                {
                    sign = n.Sign,
                    text = n.Text,
                }).ToList(),
            };

            var json    = JsonSerializer.Serialize(payload);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            using var http = _http.CreateClient();
            http.Timeout   = TimeSpan.FromSeconds(10);

            var response = await http.PostAsync($"{AcePythonUrl}/ace/override", content);

            if (response.IsSuccessStatusCode)
                _logger.LogInformation(
                    "[ACE] Override notifié | candidate={Id} | {Prev}→{New} | " +
                    "notes={NotesCount} | user={User}",
                    candidate.Id, previousStatus, newStatus,
                    rhNotes.Count, userId);
            else
                _logger.LogWarning(
                    "[ACE] Override HTTP {Status} | candidate={Id}",
                    (int)response.StatusCode, candidate.Id);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(
                "[ACE] NotifyOverride failed (non-bloquant): {Message}", ex.Message);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // GET /api/recruitment/application-by-document/{documentId}
    // Retourne la candidature associée à un document GED
    // ─────────────────────────────────────────────────────────────────────────────
    [AllowAnonymous]
    [HttpGet("application-by-document/{documentId}")]
    public async Task<IActionResult> GetApplicationByDocument(int documentId)
    {
        var candidate = await _db.CandidateApplications
            .Include(c => c.Document)
                .ThenInclude(d => d.Files)
            .FirstOrDefaultAsync(c => c.DocumentId == documentId);
    
        if (candidate is null)
            return NotFound(new { error = $"Aucune candidature pour document {documentId}" });
    
        return Ok(new
        {
            candidateId      = candidate.Id,
            name             = candidate.CandidateName,
            email            = candidate.CandidateEmail,
            phone            = candidate.CandidatePhone,
            position         = candidate.Position,
            status           = candidate.Status.ToString(),
            notes            = candidate.Notes,
            createdAt        = candidate.CreateDate,
            aiScore          = candidate.AiScore,
            aiRecommendation = candidate.AiRecommendation,
            documentId       = candidate.DocumentId,
            // Données scoring pour le contexte chat
            scoringContext = candidate.AiScore > 0 ? new
            {
                score          = candidate.AiScore,
                recommendation = candidate.AiRecommendation,
                status         = candidate.Status.ToString(),
                position       = candidate.Position,
            } : null,
        });
    }

 
}


// ─────────────────────────────────────────────────────────────────────────────
// DTO PATCH ai-score
// ─────────────────────────────────────────────────────────────────────────────
public record UpdateAiScoreRequest(int AiScore, string AiRecommendation);