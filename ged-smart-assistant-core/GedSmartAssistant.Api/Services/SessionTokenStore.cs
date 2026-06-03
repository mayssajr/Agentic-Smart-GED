using GedSmartAssistant.Api.Interfaces;
using GedSmartAssistant.Api.Models.Auth;

namespace GedSmartAssistant.Api.Services;

public sealed class SessionTokenStore(IHttpContextAccessor httpContextAccessor) : ISessionTokenStore
{
    private const string AccessTokenCookieName = "ged_access_token";
    private const string RefreshTokenCookieName = "ged_refresh_token";
    private const string AccessTokenHeaderName = "X-Ged-Access-Token";
    private const string RefreshTokenHeaderName = "X-Ged-Refresh-Token";

    public SessionTokens? GetTokens()
    {
        var httpContext = GetHttpContext();
        var requestCookies = httpContext.Request.Cookies;

        var accessToken = requestCookies[AccessTokenCookieName];
        var refreshToken = requestCookies[RefreshTokenCookieName];

        if (string.IsNullOrWhiteSpace(accessToken) || string.IsNullOrWhiteSpace(refreshToken))
        {
            accessToken = httpContext.Request.Headers[AccessTokenHeaderName];
            refreshToken = httpContext.Request.Headers[RefreshTokenHeaderName];
        }

        return string.IsNullOrWhiteSpace(accessToken) || string.IsNullOrWhiteSpace(refreshToken)
            ? null
            : new SessionTokens(accessToken, refreshToken);
    }

    public void SetTokens(TokenPair tokens)
    {
        var httpContext = GetHttpContext();
        var options = CreateCookieOptions();
        var responseCookies = httpContext.Response.Cookies;

        responseCookies.Append(AccessTokenCookieName, tokens.AccessToken, options);
        responseCookies.Append(RefreshTokenCookieName, tokens.RefreshToken, options);
        httpContext.Response.Headers[AccessTokenHeaderName] = tokens.AccessToken;
        httpContext.Response.Headers[RefreshTokenHeaderName] = tokens.RefreshToken;
    }

    public void ClearTokens()
    {
        var httpContext = GetHttpContext();
        var responseCookies = httpContext.Response.Cookies;
        var options = CreateCookieOptions();

        responseCookies.Delete(AccessTokenCookieName, options);
        responseCookies.Delete(RefreshTokenCookieName, options);
        httpContext.Response.Headers.Remove(AccessTokenHeaderName);
        httpContext.Response.Headers.Remove(RefreshTokenHeaderName);
    }

    private HttpContext GetHttpContext() =>
        httpContextAccessor.HttpContext ?? throw new InvalidOperationException("No active HttpContext is available.");

    private static CookieOptions CreateCookieOptions() => new()
    {
        HttpOnly = true,
        Secure = true,
        SameSite = SameSiteMode.None,
        IsEssential = true,
        Path = "/"
    };
}
