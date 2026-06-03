using Microsoft.EntityFrameworkCore;
using MiniGED.API.Data;
using MiniGED.API.Dtos;
using MiniGED.API.Interfaces;
using MiniGED.API.Models;
using Npgsql;
using NpgsqlTypes;

namespace MiniGED.API.Services;

public class DocumentSearchService : IDocumentSearchService
{
    private readonly ApplicationDbContext _context;

    public DocumentSearchService(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<PagedResult<DocumentSearchResultDto>> SearchAsync(
        DocumentSearchRequest request,
        int userId)
    {
        request.Page = Math.Max(request.Page, 1);
        request.PageSize = Math.Clamp(request.PageSize, 1, 50);

        var hasQuery = !string.IsNullOrWhiteSpace(request.Query);
        var queryText = request.Query?.Trim() ?? string.Empty;

        const string sql = """
            WITH filtered_files AS (
                SELECT
                    df."Id" AS "FileId",
                    df."FileName",
                    df."Status" AS "FileStatus",
                    d."Id" AS "DocumentId",
                    d."Title" AS "DocumentTitle",
                    d."Description" AS "DocumentDescription",
                    d."UploadedAt",
                    CASE
                        WHEN @hasQuery THEN ts_rank(df."SearchVector", websearch_to_tsquery('simple', @query))
                        ELSE 0
                    END AS "Rank",
                    CASE
                        WHEN @hasQuery THEN ts_headline(
                            'simple',
                            coalesce(df."ExtractedText", coalesce(df."SearchableText", '')),
                            websearch_to_tsquery('simple', @query),
                            'StartSel=<mark>, StopSel=</mark>, MaxWords=25, MinWords=10, ShortWord=2, HighlightAll=false, MaxFragments=3, FragmentDelimiter= ... '
                        )
                        ELSE left(coalesce(df."ExtractedText", coalesce(df."SearchableText", '')), 240)
                    END AS "Snippet"
                FROM "DocumentFiles" df
                INNER JOIN "Documents" d ON d."Id" = df."DocumentId"
                WHERE d."UserId" = @userId
                  AND (NOT @hasQuery OR df."SearchVector" @@ websearch_to_tsquery('simple', @query))
                  AND (@documentIds IS NULL OR array_length(@documentIds, 1) IS NULL OR d."Id" = ANY(@documentIds))
                  AND (@fileStatuses IS NULL OR array_length(@fileStatuses, 1) IS NULL OR df."Status" = ANY(@fileStatuses))
                  AND (@uploadedFrom IS NULL OR d."UploadedAt" >= @uploadedFrom)
                  AND (@uploadedTo IS NULL OR d."UploadedAt" <= @uploadedTo)
                  AND (
                    (
                        (@taskStatuses IS NULL OR array_length(@taskStatuses, 1) IS NULL)
                        AND (@taskPriorities IS NULL OR array_length(@taskPriorities, 1) IS NULL)
                        AND @taskDueFrom IS NULL
                        AND @taskDueTo IS NULL
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM "DocumentTasks" dt
                        WHERE dt."DocumentId" = d."Id"
                          AND (@taskStatuses IS NULL OR array_length(@taskStatuses, 1) IS NULL OR dt."Status" = ANY(@taskStatuses))
                          AND (@taskPriorities IS NULL OR array_length(@taskPriorities, 1) IS NULL OR dt."Priority" = ANY(@taskPriorities))
                          AND (@taskDueFrom IS NULL OR dt."DueDate" >= @taskDueFrom)
                          AND (@taskDueTo IS NULL OR dt."DueDate" <= @taskDueTo)
                    )
                  )
            )
            SELECT
                ff.*,
                COUNT(*) OVER()::int AS "TotalCount"
            FROM filtered_files ff
            ORDER BY
                CASE WHEN @sort = 0 THEN ff."Rank" END DESC,
                CASE WHEN @sort = 1 THEN ff."UploadedAt" END DESC,
                ff."UploadedAt" DESC,
                ff."FileId" DESC
            OFFSET @offset
            LIMIT @pageSize
            """;

        var rows = await _context.Database.SqlQueryRaw<DocumentSearchQueryRow>(
            sql,
            CreateParameter("hasQuery", hasQuery, NpgsqlDbType.Boolean),
            CreateParameter("query", queryText, NpgsqlDbType.Text),
            CreateParameter("userId", userId, NpgsqlDbType.Integer),
            CreateArrayParameter("documentIds", request.DocumentIds?.ToArray()),
            CreateArrayParameter("fileStatuses", request.FileStatuses?.Select(status => (int)status).ToArray()),
            CreateParameter("uploadedFrom", request.UploadedFrom, NpgsqlDbType.TimestampTz),
            CreateParameter("uploadedTo", request.UploadedTo, NpgsqlDbType.TimestampTz),
            CreateArrayParameter("taskStatuses", request.TaskStatuses?.Select(status => (int)status).ToArray()),
            CreateArrayParameter("taskPriorities", request.TaskPriorities?.Select(priority => (int)priority).ToArray()),
            CreateParameter("taskDueFrom", request.TaskDueFrom, NpgsqlDbType.TimestampTz),
            CreateParameter("taskDueTo", request.TaskDueTo, NpgsqlDbType.TimestampTz),
            CreateParameter("sort", (int)request.Sort, NpgsqlDbType.Integer),
            CreateParameter("offset", (request.Page - 1) * request.PageSize, NpgsqlDbType.Integer),
            CreateParameter("pageSize", request.PageSize, NpgsqlDbType.Integer))
            .ToListAsync();

        var totalCount = rows.FirstOrDefault()?.TotalCount ?? 0;
        return new PagedResult<DocumentSearchResultDto>
        {
            Items = rows.Select(row => new DocumentSearchResultDto
            {
                FileId = row.FileId,
                FileName = row.FileName,
                FileStatus = (FileProcessingStatus)row.FileStatus,
                DocumentId = row.DocumentId,
                DocumentTitle = row.DocumentTitle,
                DocumentDescription = row.DocumentDescription,
                UploadedAt = row.UploadedAt,
                Snippet = row.Snippet ?? string.Empty,
                Rank = row.Rank
            }).ToList(),
            Page = request.Page,
            PageSize = request.PageSize,
            TotalCount = totalCount
        };
    }

    public async Task RefreshDocumentSearchableTextAsync(
        int documentId,
        CancellationToken cancellationToken = default)
    {
        var document = await _context.Documents
            .Include(d => d.Files)
            .FirstOrDefaultAsync(d => d.Id == documentId, cancellationToken);

        if (document == null)
        {
            return;
        }

        foreach (var file in document.Files)
        {
            file.SearchableText = BuildSearchableText(
                file.FileName,
                document.Title,
                document.Description,
                file.ExtractedText);
            file.UpdateDate = DateTime.UtcNow;
        }

        await _context.SaveChangesAsync(cancellationToken);
    }

    public static string BuildSearchableText(
        string? fileName,
        string? documentTitle,
        string? documentDescription,
        string? extractedText)
    {
        return string.Join(
            Environment.NewLine,
            new[] { fileName, documentTitle, documentDescription, extractedText }
                .Where(value => !string.IsNullOrWhiteSpace(value))
                .Select(value => value!.Trim()));
    }

    private static NpgsqlParameter CreateParameter(string name, object? value, NpgsqlDbType type)
    {
        return new NpgsqlParameter(name, type)
        {
            Value = value ?? DBNull.Value
        };
    }

    private static NpgsqlParameter CreateArrayParameter(string name, int[]? values)
    {
        return new NpgsqlParameter(name, NpgsqlDbType.Array | NpgsqlDbType.Integer)
        {
            Value = values is null ? (object)DBNull.Value : values
        };
    }

    public sealed class DocumentSearchQueryRow
    {
        public int FileId { get; set; }
        public string FileName { get; set; } = string.Empty;
        public int FileStatus { get; set; }
        public int DocumentId { get; set; }
        public string DocumentTitle { get; set; } = string.Empty;
        public string DocumentDescription { get; set; } = string.Empty;
        public DateTime UploadedAt { get; set; }
        public string? Snippet { get; set; }
        public double Rank { get; set; }
        public int TotalCount { get; set; }
    }
}
