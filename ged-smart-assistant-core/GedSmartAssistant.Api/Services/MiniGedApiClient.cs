using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using GedSmartAssistant.Api.Exceptions;
using GedSmartAssistant.Api.Interfaces;
using GedSmartAssistant.Api.Models.Auth;
using GedSmartAssistant.Api.Models.Documents;

namespace GedSmartAssistant.Api.Services;

public sealed class MiniGedApiClient(HttpClient httpClient) : IMiniGedApiClient
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public async Task<TokenPair> LoginAsync(string email, string password, CancellationToken cancellationToken)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "/api/Account/login",
            new { email, password },
            JsonOptions,
            cancellationToken);

        return await ReadRequiredAsync<TokenPair>(response, cancellationToken);
    }

    public async Task<TokenPair> RefreshTokenAsync(string refreshToken, CancellationToken cancellationToken)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "/users/refresh-token",
            new { refreshToken },
            JsonOptions,
            cancellationToken);

        if (!response.IsSuccessStatusCode)
        {
            throw new MiniGedUnauthorizedException("MiniGed rejected the refresh token.");
        }

        return await ReadRequiredAsync<TokenPair>(response, cancellationToken);
    }

    public async Task<UserProfile> GetCurrentUserAsync(string accessToken, CancellationToken cancellationToken)
    {
        using var request = CreateRequest(HttpMethod.Get, "/api/Account/me", accessToken);
        using var response = await httpClient.SendAsync(request, cancellationToken);

        return await ReadRequiredAsync<UserProfile>(response, cancellationToken);
    }

    public async Task<(TokenPair Tokens, UserProfile User)> ValidateSessionAsync(TokenPair tokens, CancellationToken cancellationToken)
    {
        try
        {
            var user = await GetCurrentUserAsync(tokens.AccessToken, cancellationToken);
            return (tokens, user);
        }
        catch (MiniGedUnauthorizedException)
        {
            var refreshedTokens = await RefreshTokenAsync(tokens.RefreshToken, cancellationToken);
            var user = await GetCurrentUserAsync(refreshedTokens.AccessToken, cancellationToken);
            return (refreshedTokens, user);
        }
    }

    public async Task<string> CreateDocumentAsync(string accessToken, CreateDocumentCommand command, CancellationToken cancellationToken)
    {
        using var request = CreateRequest(HttpMethod.Post, "/api/Document/add", accessToken);
        request.Content = JsonContent.Create(command, options: JsonOptions);

        using var response = await httpClient.SendAsync(request, cancellationToken);

        if (response.StatusCode == HttpStatusCode.Unauthorized)
        {
            throw new MiniGedUnauthorizedException("MiniGed rejected the access token while creating a document.");
        }

        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync(cancellationToken);
    }

    public async Task<SearchDocumentsResponse> SearchDocumentsAsync(string accessToken, string keyword, CancellationToken cancellationToken)
    {
        using var request = CreateRequest(HttpMethod.Post, "/api/document/search", accessToken);
        request.Content = JsonContent.Create(
            new SearchDocumentsRequest
            {
                Query = keyword,
                Page = 1,
                PageSize = 5,
                Sort = 0
            },
            options: JsonOptions);
        using var response = await httpClient.SendAsync(request, cancellationToken);

        return await ReadRequiredAsync<SearchDocumentsResponse>(response, cancellationToken);
    }

    private static HttpRequestMessage CreateRequest(HttpMethod method, string uri, string accessToken)
    {
        var request = new HttpRequestMessage(method, uri);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        return request;
    }

    private static async Task<T> ReadRequiredAsync<T>(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        if (response.StatusCode == HttpStatusCode.Unauthorized)
        {
            throw new MiniGedUnauthorizedException("MiniGed rejected the access token.");
        }

        response.EnsureSuccessStatusCode();

        var payload = await response.Content.ReadFromJsonAsync<T>(JsonOptions, cancellationToken);
        return payload ?? throw new InvalidOperationException($"MiniGed returned an empty payload for {typeof(T).Name}.");
    }
}
