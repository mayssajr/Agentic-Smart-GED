using MiniGED.API.Data;
using MiniGED.API.Dtos;
using MiniGED.API.Interfaces;
using UglyToad.PdfPig;

namespace MiniGED.API.Services;

public class DocumentTextExtractor : IDocumentTextExtractor
{
    private readonly ApplicationDbContext _context;

    public DocumentTextExtractor(ApplicationDbContext context)
    {
        _context = context;
    }

    public FileExtractionResult ParsePdfContent(FileProcessingPayload dataparseobj)
    {
        var containingDocument = _context.Documents.Find(dataparseobj.DocumentId);
        var fileMetaData = _context.DocumentFiles.Find(dataparseobj.FileId);
        if (containingDocument == null || fileMetaData == null)
        {
            return new FileExtractionResult();
        }

        var folderName = Path.Combine("Resource", "AllFiles");
        var pathToSave = Path.Combine(Directory.GetCurrentDirectory(), folderName);
        var fullPath = Path.Combine(pathToSave, $"{dataparseobj.FileId}.pdf");

        if (!File.Exists(fullPath))
        {
            return new FileExtractionResult();
        }

        var pageTexts = new List<string>();
        using var document = PdfDocument.Open(fullPath);
        foreach (var page in document.GetPages())
        {
            pageTexts.Add(page.Text);
        }

        return new FileExtractionResult
        {
            ExtractedText = string.Join(Environment.NewLine + Environment.NewLine, pageTexts),
            PageCount = pageTexts.Count
        };
    }
}
