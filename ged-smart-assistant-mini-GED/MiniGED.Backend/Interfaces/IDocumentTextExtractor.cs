using MiniGED.API.Dtos;

namespace MiniGED.API.Interfaces;

public interface IDocumentTextExtractor
{
    FileExtractionResult ParsePdfContent(FileProcessingPayload dataparseobj);
}
