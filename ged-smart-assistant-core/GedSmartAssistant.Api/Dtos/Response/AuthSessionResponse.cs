using GedSmartAssistant.Api.Models.Auth;

namespace GedSmartAssistant.Api.Dtos.Response;

public sealed class AuthSessionResponse
{
    public bool IsAuthenticated { get; init; }
    public UserProfile? User { get; init; }
}
