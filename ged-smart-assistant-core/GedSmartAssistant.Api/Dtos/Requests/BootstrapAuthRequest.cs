using System.ComponentModel.DataAnnotations;
using GedSmartAssistant.Api.Models.Auth;

namespace GedSmartAssistant.Api.Dtos.Requests;

public sealed class BootstrapAuthRequest
{
    [Required]
    public string AccessToken { get; init; } = string.Empty;

    [Required]
    public string RefreshToken { get; init; } = string.Empty;

    [Required]
    public UserProfile User { get; init; } = new();

    public string? SourceSystem { get; init; }
}
