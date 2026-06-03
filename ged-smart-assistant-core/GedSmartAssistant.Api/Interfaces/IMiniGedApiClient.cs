using GedSmartAssistant.Api.Models.Auth;
using GedSmartAssistant.Api.Models.Documents;

namespace GedSmartAssistant.Api.Interfaces;

public interface IMiniGedApiClient
{
    Task<TokenPair> LoginAsync(string email, string password, CancellationToken cancellationToken);
    Task<TokenPair> RefreshTokenAsync(string refreshToken, CancellationToken cancellationToken);
    Task<UserProfile> GetCurrentUserAsync(string accessToken, CancellationToken cancellationToken);
    Task<(TokenPair Tokens, UserProfile User)> ValidateSessionAsync(TokenPair tokens, CancellationToken cancellationToken);
    Task<string> CreateDocumentAsync(string accessToken, CreateDocumentCommand command, CancellationToken cancellationToken);
    Task<SearchDocumentsResponse> SearchDocumentsAsync(string accessToken, string keyword, CancellationToken cancellationToken);
}
