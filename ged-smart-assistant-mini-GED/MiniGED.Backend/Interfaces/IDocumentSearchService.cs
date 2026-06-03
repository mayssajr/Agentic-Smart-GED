using MiniGED.API.Dtos;

namespace MiniGED.API.Interfaces;

public interface IDocumentSearchService
{
    Task<PagedResult<DocumentSearchResultDto>> SearchAsync(DocumentSearchRequest request, int userId);
    Task RefreshDocumentSearchableTextAsync(int documentId, CancellationToken cancellationToken = default);
}
