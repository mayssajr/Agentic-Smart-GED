using System.ComponentModel;
using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using ModelContextProtocol.Server;
using MiniGED.API.Data;
using MiniGED.API.Dtos;
using MiniGED.API.Interfaces;
using MiniGED.API.Models;

namespace MiniGED.API.Mcp;

[McpServerToolType]
public class MiniGedMcpTools
{
    private readonly ApplicationDbContext    _db;
    private readonly IDocumentSearchService  _search;

    private static readonly JsonSerializerOptions _json = new()
    {
        WriteIndented          = false,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        PropertyNamingPolicy   = JsonNamingPolicy.CamelCase,
    };

    public MiniGedMcpTools(ApplicationDbContext db, IDocumentSearchService search)
    {
        _db     = db;
        _search = search;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // HELPER : normalisation des accents pour la recherche
    // Convertit "Ingénieur systèmes embarqués" → "ingenieur systemes embarques"
    // Permet de matcher les mots normalisés envoyés par Python avec les textes
    // accentués stockés en base de données.
    // ─────────────────────────────────────────────────────────────────────────
    private static string NormalizeForSearch(string? text)
    {
        if (string.IsNullOrEmpty(text)) return "";
        // NFD décompose les caractères composés : é → e + combining accent
        var decomposed = text.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(decomposed.Length);
        foreach (var c in decomposed)
        {
            // Ignorer les combining marks (accents détachés)
            if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }
        return sb.ToString().ToLower();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // get_documents
    // ─────────────────────────────────────────────────────────────────────────

    [McpServerTool(Name = "get_documents")]
    [Description("Liste les documents GED d'un utilisateur (max 50).")]
    public async Task<string> GetDocuments(
        [Description("ID de l'utilisateur")] int user_id,
        [Description("Limite (défaut 20)")]  int limit = 20)
    {
        var docs = await _db.Documents
            .Where(d => d.UserId == user_id)
            .OrderByDescending(d => d.UploadedAt)
            .Take(Math.Min(limit, 50))
            .Select(d => new { id = d.Id, title = d.Title,
                               description = d.Description, uploadedAt = d.UploadedAt,
                               fileCount = d.Files.Count })
            .ToListAsync();
        return JsonSerializer.Serialize(docs, _json);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // get_document
    // ─────────────────────────────────────────────────────────────────────────

    [McpServerTool(Name = "get_document")]
    [Description("Récupère un document GED par ID avec ses fichiers.")]
    public async Task<string> GetDocument(
        [Description("ID du document")] int document_id,
        [Description("ID utilisateur (optionnel)")] int user_id = 0)
    {
        var query = _db.Documents
            .Include(d => d.Files)
            .Include(d => d.Tasks)       // ← AJOUT pour _get_existing_task_titles
            .Where(d => d.Id == document_id);
        if (user_id > 0) query = query.Where(d => d.UserId == user_id);
        var doc = await query.FirstOrDefaultAsync();
        if (doc is null)
            return JsonSerializer.Serialize(
                new { error = $"Document {document_id} introuvable" }, _json);
        return JsonSerializer.Serialize(new
        {
            id          = doc.Id,
            title       = doc.Title,
            description = doc.Description,
            uploadedAt  = doc.UploadedAt,
            files = doc.Files.Select(f => new
            {
                id          = f.Id,
                filename    = f.FileName,
                fileSize    = f.FileSize,
                status      = f.Status.ToString(),
                pageCount   = f.PageCount,
                textContent = f.ExtractedText,
                hasText     = !string.IsNullOrWhiteSpace(f.ExtractedText),
            }).ToList(),
            tasks = doc.Tasks.Select(t => new   // ← AJOUT
            {
                id       = t.Id,
                title    = t.Title,
                status   = t.Status.ToString(),
                priority = t.Priority.ToString(),
                dueDate  = t.DueDate,
            }).ToList(),
        }, _json);
}

    // ─────────────────────────────────────────────────────────────────────────
    // get_document_text
    // ─────────────────────────────────────────────────────────────────────────

    [McpServerTool(Name = "get_document_text")]
    [Description("Retourne le texte extrait de tous les fichiers PDF d'un document.")]
    public async Task<string> GetDocumentText(
        [Description("ID du document")] int document_id)
    {
        var files = await _db.DocumentFiles
            .Where(f => f.DocumentId == document_id).OrderBy(f => f.Id).ToListAsync();
        if (!files.Any())
            return JsonSerializer.Serialize(
                new { error = $"Aucun fichier pour {document_id}" }, _json);
        var fileResults = files.Select(f => new
        {
            fileId = f.Id, filename = f.FileName, status = f.Status.ToString(),
            pageCount = f.PageCount, textContent = f.ExtractedText ?? string.Empty,
            hasText = !string.IsNullOrWhiteSpace(f.ExtractedText),
        }).ToList();
        return JsonSerializer.Serialize(new
        {
            documentId = document_id, fileCount = fileResults.Count, files = fileResults,
            mergedText = string.Join("\n\n", fileResults.Where(f => f.hasText)
                .Select(f => $"=== {f.filename} ===\n{f.textContent}")),
        }, _json);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // search_documents
    // ─────────────────────────────────────────────────────────────────────────

    [McpServerTool(Name = "search_documents")]
    [Description(
        "Recherche full-text dans MiniGED via PostgreSQL tsvector. " +
        "Retourne une liste de documents avec leur type IA (aiDocumentType). " +
        "user_id=0 pour chercher dans tous les documents (mode MCP agent IA).")]
    public async Task<string> SearchDocuments(
        [Description("Termes de recherche")] string query,
        [Description("ID utilisateur (0 = tous les documents)")] int user_id = 0,
        [Description("Page")] int page = 1,
        [Description("Taille page")] int page_size = 10)
    {
        if (string.IsNullOrWhiteSpace(query))
            return JsonSerializer.Serialize(new { error = "query vide" }, _json);

        if (user_id <= 0)
            return await SearchAllUsers(query, page, Math.Min(page_size, 20));

        var result = await _search.SearchAsync(
            new DocumentSearchRequest
            {
                Query    = query,
                Page     = page,
                PageSize = Math.Min(page_size, 20),
            },
            user_id);

        var documentIds = result.Items.Select(i => i.DocumentId).Distinct().ToList();
        var docAiTypes  = await _db.Documents
            .Where(d => documentIds.Contains(d.Id))
            .Select(d => new { d.Id, d.AiDocumentType })
            .ToDictionaryAsync(d => d.Id, d => d.AiDocumentType);

        var items = result.Items.Select(r => new
        {
            documentId          = r.DocumentId,
            documentTitle       = r.DocumentTitle,
            documentDescription = r.DocumentDescription,
            fileId              = r.FileId,
            fileName            = r.FileName,
            snippet             = r.Snippet,
            rank                = r.Rank,
            uploadedAt          = r.UploadedAt,
            aiDocumentType      = docAiTypes.GetValueOrDefault(r.DocumentId),
        }).ToList();

        return JsonSerializer.Serialize(new
        {
            query,
            userId     = user_id,
            totalCount = result.TotalCount,
            results    = items,
        }, _json);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // SearchAllUsers — FIX ACCENTS
    //
    // Problème corrigé : Python envoie des mots normalisés sans accents
    // (ex: "ingenieur systemes embarques") mais la DB contient des textes
    // accentués (ex: "Ingénieur systèmes embarqués"). La comparaison
    // Contains() échouait car "é" ≠ "e".
    //
    // Solution : charger les documents en mémoire et utiliser NormalizeForSearch()
    // qui supprime les accents avant comparaison.
    // ─────────────────────────────────────────────────────────────────────────
    private async Task<string> SearchAllUsers(string query, int page, int pageSize)
    {
        // Découper la query en mots individuels (déjà normalisés sans accents par Python)
        var words = query.ToLower()
            .Split(' ', StringSplitOptions.RemoveEmptyEntries)
            .Where(w => w.Length > 2)
            .ToArray();

        if (words.Length == 0)
            return JsonSerializer.Serialize(
                new { query, userId = 0, totalCount = 0, results = new List<object>() }, _json);

        // Charger les 150 documents les plus récents en mémoire
        // (nécessaire pour appliquer NormalizeForSearch côté C# et non SQL)
        var allDocs = await _db.Documents
            .Include(d => d.Files)
            .OrderByDescending(d => d.UploadedAt)
            .Take(150)
            .ToListAsync();

        // Filtrer en mémoire avec normalisation des accents
        // NormalizeForSearch("Ingénieur") → "ingenieur" → match avec words["ingenieur"]
        var matchingDocs = allDocs.Where(d => words.Any(w =>
            NormalizeForSearch(d.Title).Contains(w) ||
            NormalizeForSearch(d.Description).Contains(w) ||
            NormalizeForSearch(d.AiDocumentType).Contains(w) ||
            d.Files.Any(f =>
                NormalizeForSearch(f.SearchableText).Contains(w) ||
                NormalizeForSearch(f.FileName).Contains(w))
        )).ToList();

        // Paginer
        var pagedDocs = matchingDocs
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .Select(d => new
            {
                documentId          = d.Id,
                documentTitle       = d.Title,
                documentDescription = d.Description,
                fileId              = d.Files.OrderBy(f => f.Id).Select(f => f.Id).FirstOrDefault(),
                fileName            = d.Files.OrderBy(f => f.Id).Select(f => f.FileName).FirstOrDefault(),
                snippet             = d.Description ?? "",
                rank                = 1.0,
                uploadedAt          = d.UploadedAt,
                aiDocumentType      = d.AiDocumentType,
            })
            .ToList();

        // Trier : offres d'emploi en premier, puis par date décroissante
        var sorted = pagedDocs
            .OrderByDescending(d =>
                NormalizeForSearch(d.aiDocumentType).Contains("offre") ||
                NormalizeForSearch(d.documentTitle).Contains("offre") ? 1 : 0)
            .ThenByDescending(d => d.uploadedAt)
            .ToList();

        return JsonSerializer.Serialize(new
        {
            query,
            userId     = 0,
            totalCount = sorted.Count,
            results    = sorted,
        }, _json);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // create_document
    // ─────────────────────────────────────────────────────────────────────────

    [McpServerTool(Name = "create_document")]
    [Description("Crée un nouveau document dans MiniGED.")]
    public async Task<string> CreateDocument(
        [Description("Titre")] string title,
        [Description("ID utilisateur")] int user_id,
        [Description("Description (optionnel)")] string description = "")
    {
        if (string.IsNullOrWhiteSpace(title))
            return JsonSerializer.Serialize(new { error = "title requis" }, _json);
        if (user_id <= 0)
            return JsonSerializer.Serialize(new { error = "user_id requis" }, _json);
        var doc = new Document
        {
            Title       = title.Trim(),
            Description = description.Trim(),
            UserId      = user_id
        };
        _db.Documents.Add(doc);
        await _db.SaveChangesAsync();
        return JsonSerializer.Serialize(new
        {
            success    = true,
            documentId = doc.Id,
            title      = doc.Title,
            uploadedAt = doc.UploadedAt
        }, _json);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // get_file_status
    // ─────────────────────────────────────────────────────────────────────────

    [McpServerTool(Name = "get_file_status")]
    [Description("Vérifie le statut d'extraction PdfPig d'un document.")]
    public async Task<string> GetFileStatus(
        [Description("ID du document")] int document_id)
    {
        var files = await _db.DocumentFiles
            .Where(f => f.DocumentId == document_id)
            .Select(f => new
            {
                fileId   = f.Id,
                filename = f.FileName,
                status   = f.Status.ToString(),
                hasText  = !string.IsNullOrWhiteSpace(f.ExtractedText),
                pageCount = f.PageCount
            })
            .ToListAsync();

        if (!files.Any())
            return JsonSerializer.Serialize(
                new { error = $"Aucun fichier pour {document_id}" }, _json);

        var allReady  = files.All(f => f.hasText);
        var anyFailed = files.Any(f => f.status == "Failed");
        return JsonSerializer.Serialize(new
        {
            documentId = document_id,
            files,
            allReady,
            anyFailed,
            readyForAI = allReady && !anyFailed,
            recommendation = allReady
                ? "Texte disponible — appeler get_document_text"
                : anyFailed
                    ? "Extraction échouée — vérifier /hangfire"
                    : "Extraction en cours — réessayer dans quelques secondes",
        }, _json);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // create_tasks
    // ─────────────────────────────────────────────────────────────────────────

    [McpServerTool(Name = "create_tasks")]
    [Description(
        "Crée une ou plusieurs tâches sur un document MiniGED. " +
        "tasks_json = tableau JSON : [{title, description, priority, due_days}] " +
        "où priority = Low|Medium|High|Urgent et due_days = nombre de jours.")]
    public async Task<string> CreateTasks(
        [Description("ID du document cible")] int document_id,
        [Description("Tableau JSON des tâches à créer")] string tasks_json)
    {
        var doc = await _db.Documents.FindAsync(document_id);
        if (doc is null)
            return JsonSerializer.Serialize(
                new { error = $"Document {document_id} introuvable" }, _json);

        List<TaskInput>? inputs;
        try
        {
            inputs = JsonSerializer.Deserialize<List<TaskInput>>(tasks_json,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }
        catch (Exception ex)
        {
            return JsonSerializer.Serialize(
                new { error = $"tasks_json invalide : {ex.Message}" }, _json);
        }

        if (inputs is null || inputs.Count == 0)
            return JsonSerializer.Serialize(new { error = "Aucune tâche à créer" }, _json);

        var created = new List<object>();
        foreach (var input in inputs)
        {
            if (string.IsNullOrWhiteSpace(input.Title)) continue;

            var priority = input.Priority?.ToLower() switch
            {
                "low"    => DocumentTaskPriority.Low,
                "high"   => DocumentTaskPriority.High,
                "urgent" => DocumentTaskPriority.Urgent,
                _        => DocumentTaskPriority.Medium,
            };

            var task = new DocumentTask
            {
                Title       = input.Title.Trim(),
                Description = input.Description?.Trim(),
                Priority    = priority,
                DueDate     = input.DueDays.HasValue
                              ? DateTime.UtcNow.AddDays(input.DueDays.Value)
                              : null,
                DocumentId  = document_id,
                Status      = DocumentTaskStatus.Pending,
                CreatedAt   = DateTime.UtcNow,
            };
            _db.DocumentTasks.Add(task);
            await _db.SaveChangesAsync();
            created.Add(new
            {
                id       = task.Id,
                title    = task.Title,
                priority = task.Priority.ToString(),
                dueDate  = task.DueDate
            });
        }

        return JsonSerializer.Serialize(new
        {
            success    = true,
            documentId = document_id,
            tasksCreated = created.Count,
            tasks      = created
        }, _json);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // update_candidate_status
    // ─────────────────────────────────────────────────────────────────────────

    [McpServerTool(Name = "update_candidate_status")]
    [Description(
        "Met à jour le statut d'une candidature RH. " +
        "Statuts valides : Recu, EnAnalyse, ATraiter, Entretien, Accepte, Refuse, ListeAttente. " +
        "document_id peut être utilisé si candidate_id est inconnu.")]
    public async Task<string> UpdateCandidateStatus(
        [Description("ID de la candidature (CandidateApplication.Id)")] int candidate_id = 0,
        [Description("ID du document MiniGED (alternatif si candidate_id inconnu)")] int document_id = 0,
        [Description("Nouveau statut")] string status = "",
        [Description("Note RH optionnelle")] string notes = "")
    {
        CandidateApplication? candidate = null;

        if (candidate_id > 0)
            candidate = await _db.CandidateApplications
                .Include(c => c.Document)
                .FirstOrDefaultAsync(c => c.Id == candidate_id);
        else if (document_id > 0)
            candidate = await _db.CandidateApplications
                .Include(c => c.Document)
                .FirstOrDefaultAsync(c => c.DocumentId == document_id);

        if (candidate is null)
            return JsonSerializer.Serialize(
                new { error = "Candidature introuvable" }, _json);

        if (!Enum.TryParse<CandidateStatus>(status, true, out var newStatus))
            return JsonSerializer.Serialize(new
            {
                error  = $"Statut invalide : '{status}'",
                valids = Enum.GetNames<CandidateStatus>(),
            }, _json);

        var oldStatus = candidate.Status;
        candidate.Status = newStatus;
        if (!string.IsNullOrWhiteSpace(notes))
            candidate.Notes = notes;

        await _db.SaveChangesAsync();

        // Notifier ACE (fire-and-forget, non bloquant)
        _ = NotifyAceFromMcpAsync(candidate, oldStatus, newStatus, notes);

        return JsonSerializer.Serialize(new
        {
            success     = true,
            candidateId = candidate.Id,
            name        = candidate.CandidateName,
            position    = candidate.Position,
            oldStatus   = oldStatus.ToString(),
            newStatus   = candidate.Status.ToString(),
            notes       = candidate.Notes,
        }, _json);
    }

    // ── Helper ACE pour le MCP tool ───────────────────────────────────────────
    private static async Task NotifyAceFromMcpAsync(
        CandidateApplication candidate,
        CandidateStatus      previousStatus,
        CandidateStatus      newStatus,
        string               notes)
    {
        try
        {
            var aiScore = candidate.AiScore ?? 0;
            var aiRec   = candidate.AiRecommendation ?? "ListeAttente";

            if (aiScore == 0 && candidate.Document?.AiSummary is not null)
            {
                try
                {
                    using var doc = JsonDocument.Parse(candidate.Document.AiSummary);
                    if (doc.RootElement.TryGetProperty("score", out var s))
                        aiScore = s.GetInt32();
                    if (doc.RootElement.TryGetProperty("recommendation", out var r))
                        aiRec = r.GetString() ?? "ListeAttente";
                }
                catch { }
            }

            var payload = new
            {
                candidate_id      = candidate.Id,
                candidate_name    = candidate.CandidateName,
                position          = candidate.Position,
                ai_score          = aiScore,
                ai_recommendation = aiRec,
                ai_status         = previousStatus.ToString(),
                human_status      = newStatus.ToString(),
                user_id           = "mcp_tool",
                notes             = notes,
            };

            var json    = JsonSerializer.Serialize(payload);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(8) };
            await http.PostAsync("http://localhost:8000/ace/override", content);
        }
        catch
        {
            // Non bloquant
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // get_candidate
    // ─────────────────────────────────────────────────────────────────────────

    [McpServerTool(Name = "get_candidate")]
    [Description(
        "Récupère les informations d'une candidature par document_id ou candidate_id. " +
        "Retourne nom, email, poste, statut, résumé IA, types de fichiers.")]
    public async Task<string> GetCandidate(
        [Description("ID de la candidature")] int candidate_id = 0,
        [Description("ID du document MiniGED")] int document_id = 0)
    {
        CandidateApplication? c = null;

        if (candidate_id > 0)
            c = await _db.CandidateApplications
                .Include(x => x.Document).ThenInclude(d => d.Files)
                .FirstOrDefaultAsync(x => x.Id == candidate_id);
        else if (document_id > 0)
            c = await _db.CandidateApplications
                .Include(x => x.Document).ThenInclude(d => d.Files)
                .FirstOrDefaultAsync(x => x.DocumentId == document_id);

        if (c is null)
            return JsonSerializer.Serialize(new { error = "Candidature introuvable" }, _json);

        return JsonSerializer.Serialize(new
        {
            candidateId    = c.Id,
            name           = c.CandidateName,
            email          = c.CandidateEmail,
            phone          = c.CandidatePhone,
            position       = c.Position,
            status         = c.Status.ToString(),
            notes          = c.Notes,
            aiScore        = c.AiScore,
            createdAt      = c.CreateDate,
            documentId     = c.DocumentId,
            aiDocumentType = c.Document?.AiDocumentType,
            aiSummary      = c.Document?.AiSummary,
            isAnalyzed     = c.Document?.AiAnalyzedAt != null,
            fileTypes      = c.Document?.Files
                .Where(f => f.AiFileType != null)
                .Select(f => new { f.Id, f.FileName, f.AiFileType })
                .ToList(),
        }, _json);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // list_candidates
    // ─────────────────────────────────────────────────────────────────────────

    [McpServerTool(Name = "list_candidates")]
    [Description(
        "Liste les candidatures RH avec filtres optionnels. " +
        "status_filter : Recu|EnAnalyse|ATraiter|Entretien|Accepte|Refuse|ListeAttente ou vide pour toutes.")]
    public async Task<string> ListCandidates(
        [Description("Filtre statut (vide = tous)")] string status_filter = "",
        [Description("Filtre poste (vide = tous)")] string position_filter = "",
        [Description("Limite résultats")] int limit = 20)
    {
        var query = _db.CandidateApplications
            .Include(c => c.Document)
            .AsQueryable();

        if (!string.IsNullOrWhiteSpace(status_filter) &&
            Enum.TryParse<CandidateStatus>(status_filter, true, out var s))
            query = query.Where(c => c.Status == s);

        if (!string.IsNullOrWhiteSpace(position_filter))
            query = query.Where(c => c.Position.ToLower().Contains(position_filter.ToLower()));

        var results = await query
            .OrderByDescending(c => c.CreateDate)
            .Take(Math.Min(limit, 50))
            .Select(c => new
            {
                candidateId    = c.Id,
                name           = c.CandidateName,
                email          = c.CandidateEmail,
                position       = c.Position,
                status         = c.Status.ToString(),
                isAnalyzed     = c.Document != null && c.Document.AiAnalyzedAt != null,
                aiDocumentType = c.Document != null ? c.Document.AiDocumentType : null,
                createdAt      = c.CreateDate,
            })
            .ToListAsync();

        return JsonSerializer.Serialize(new
        {
            total      = results.Count,
            candidates = results
        }, _json);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// DTOs
// ─────────────────────────────────────────────────────────────────────────────

public class TaskInput
{
    public string  Title       { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string? Priority    { get; set; }
    public int?    DueDays     { get; set; }
}