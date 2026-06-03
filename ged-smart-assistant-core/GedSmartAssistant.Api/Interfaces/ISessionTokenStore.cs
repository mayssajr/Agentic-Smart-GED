using GedSmartAssistant.Api.Models.Auth;

namespace GedSmartAssistant.Api.Interfaces;

public interface ISessionTokenStore
{
    SessionTokens? GetTokens();
    void SetTokens(TokenPair tokens);
    void ClearTokens();
}
