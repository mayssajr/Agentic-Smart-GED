using GedSmartAssistant.Api.Models.Auth;
using GedSmartAssistant.Api.Models.Documents;

namespace GedSmartAssistant.Api.Interfaces;

public interface IMiniGedSessionService
{
    Task<UserProfile> LoginAsync(string email, string password, CancellationToken cancellationToken);
    Task<UserProfile> BootstrapAsync(TokenPair tokens, UserProfile expectedUser, CancellationToken cancellationToken);
    Task<UserProfile> GetCurrentUserAsync(CancellationToken cancellationToken);
    Task<string> CreateDocumentAsync(CreateDocumentCommand command, CancellationToken cancellationToken);
    Task<SearchDocumentsResponse> SearchDocumentsAsync(string keyword, CancellationToken cancellationToken);
    void Logout();
}
