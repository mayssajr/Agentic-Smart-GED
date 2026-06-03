using Microsoft.EntityFrameworkCore;
using MiniGED.API.Data;
using MiniGED.API.Dtos;
using MiniGED.API.Interfaces;
using MiniGED.API.Models;
using System.Text.Json;


namespace MiniGED.API.Services;

public class FileProcessingJob : IFileProcessingJob
{
    private readonly ApplicationDbContext _context;
    private readonly IDocumentTextExtractor _documentTextExtractor;
    private readonly IDocumentSearchService _documentSearchService;
    private readonly IFileService _fileService;

    private readonly IHttpClientFactory     _httpClientFactory;
    private readonly IConfiguration         _configuration;

    public FileProcessingJob(
        ApplicationDbContext context,
        IDocumentTextExtractor documentTextExtractor,
        IDocumentSearchService documentSearchService,
        IFileService fileService,
        IHttpClientFactory httpClientFactory,
        IConfiguration configuration)
    {
        _context = context;
        _documentTextExtractor = documentTextExtractor;
        _documentSearchService = documentSearchService;
        _fileService = fileService;
        _httpClientFactory     = httpClientFactory;
        _configuration         = configuration;
    }

    public async Task ProcessFileAsync(FileProcessingPayload parsingPayload)
    {
        try
        {
            _fileService.ChangeFileStatus(parsingPayload.FileId, FileProcessingStatus.Processing);
            
            var parsingResponse = _documentTextExtractor.ParsePdfContent(parsingPayload);
            var documentFile = await _context.DocumentFiles
                .FirstOrDefaultAsync(file => file.Id == parsingPayload.FileId);

            if (documentFile == null)
            {
                return;
            }

            documentFile.ExtractedText = parsingResponse.ExtractedText;
            documentFile.PageCount = parsingResponse.PageCount;
            documentFile.UpdateDate = DateTime.UtcNow;

            await _context.SaveChangesAsync();
            await _documentSearchService.RefreshDocumentSearchableTextAsync(
                parsingPayload.DocumentId);

            _fileService.ChangeFileStatus(parsingPayload.FileId, FileProcessingStatus.Completed);
            //declenchement auto de l'analyse ia agentique 
            _ = TriggerAiAnalysisAsync(parsingPayload.DocumentId);

        }
        catch (Exception ex)
        {
            Console.WriteLine($"File processing failed for file {parsingPayload.FileId}: {ex}");
            _fileService.ChangeFileStatus(parsingPayload.FileId, FileProcessingStatus.Failed);
        }
    }
    
    private async Task TriggerAiAnalysisAsync(int documentId)
    {
        try
        {
            var aiBaseUrl = _configuration["AiBackendUrl"]
                         ?? _configuration["AI_BACKEND_URL"]
                         ?? "http://localhost:8000";
 
            var client = _httpClientFactory.CreateClient("AiBackend");
 
            var payload = JsonSerializer.Serialize(new
            {
                miniged_token = "",
                force         = false,   // ne re-analyse pas si déjà fait
            });
 
            var content = new StringContent(
                payload,
                System.Text.Encoding.UTF8,
                "application/json");
 
            Console.WriteLine(
                $"[FileProcessingJob] Auto-analyse IA → doc={documentId}");
 
            var response = await client.PostAsync(
                $"{aiBaseUrl}/analyze-document/{documentId}",
                content);
 
            Console.WriteLine(
                $"[FileProcessingJob] Réponse analyse IA — doc={documentId} " +
                $"status={response.StatusCode}");
        }
        catch (Exception ex)
        {
            // Non bloquant : l'utilisateur peut toujours lancer l'analyse manuellement
            Console.WriteLine(
                $"[FileProcessingJob] Auto-analyse IA échouée (non bloquant) " +
                $"— doc={documentId} : {ex.Message}");
        }
    }
}