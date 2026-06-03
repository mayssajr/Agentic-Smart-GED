using GedSmartAssistant.Api.Exceptions;
using GedSmartAssistant.Api.Interfaces;
using GedSmartAssistant.Api.Models.Auth;
using GedSmartAssistant.Api.Models.Documents;

namespace GedSmartAssistant.Api.Services;

public sealed class MiniGedSessionService(
    IMiniGedApiClient miniGedApiClient,
    ISessionTokenStore sessionTokenStore) : IMiniGedSessionService
{
    public async Task<UserProfile> LoginAsync(string email, string password, CancellationToken cancellationToken)
    {
        var tokens = await miniGedApiClient.LoginAsync(email, password, cancellationToken);
        sessionTokenStore.SetTokens(tokens);
        return await miniGedApiClient.GetCurrentUserAsync(tokens.AccessToken, cancellationToken);
    }

    public async Task<UserProfile> BootstrapAsync(TokenPair tokens, UserProfile expectedUser, CancellationToken cancellationToken)
    {
        var validatedSession = await miniGedApiClient.ValidateSessionAsync(tokens, cancellationToken);

        EnsureSameUser(expectedUser, validatedSession.User);
        sessionTokenStore.SetTokens(validatedSession.Tokens);

        return validatedSession.User;
    }

    public Task<UserProfile> GetCurrentUserAsync(CancellationToken cancellationToken) =>
        ExecuteAuthorizedAsync(accessToken => miniGedApiClient.GetCurrentUserAsync(accessToken, cancellationToken), cancellationToken);

    public Task<string> CreateDocumentAsync(CreateDocumentCommand command, CancellationToken cancellationToken) =>
        ExecuteAuthorizedAsync(accessToken => miniGedApiClient.CreateDocumentAsync(accessToken, command, cancellationToken), cancellationToken);

    public Task<SearchDocumentsResponse> SearchDocumentsAsync(string keyword, CancellationToken cancellationToken) =>
        ExecuteAuthorizedAsync(accessToken => miniGedApiClient.SearchDocumentsAsync(accessToken, keyword, cancellationToken), cancellationToken);

    public void Logout() => sessionTokenStore.ClearTokens();

    private static void EnsureSameUser(UserProfile expectedUser, UserProfile actualUser)
    {
        var sameId = expectedUser.Id > 0 && expectedUser.Id == actualUser.Id;
        var sameEmail = !string.IsNullOrWhiteSpace(expectedUser.Email)
            && string.Equals(expectedUser.Email, actualUser.Email, StringComparison.OrdinalIgnoreCase);

        if (sameId || sameEmail)
        {
            return;
        }

        throw new InvalidOperationException("The provided MiniGed user does not match the authenticated session.");
    }

    private async Task<T> ExecuteAuthorizedAsync<T>(Func<string, Task<T>> operation, CancellationToken cancellationToken)
    {
        var tokens = sessionTokenStore.GetTokens() ?? throw new MissingSessionException();

        try
        {
            return await operation(tokens.AccessToken);
        }
        catch (MiniGedUnauthorizedException)
        {
            try
            {
                var refreshedTokens = await miniGedApiClient.RefreshTokenAsync(tokens.RefreshToken, cancellationToken);
                sessionTokenStore.SetTokens(refreshedTokens);
                return await operation(refreshedTokens.AccessToken);
            }
            catch (MiniGedUnauthorizedException)
            {
                sessionTokenStore.ClearTokens();
                throw new MissingSessionException();
            }
        }
    }
}
