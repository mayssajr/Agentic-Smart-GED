namespace GedSmartAssistant.Api.Models.Configuration;

public sealed class AiServiceOptions
{
    public const string SectionName = "AiService";

    public string BaseUrl { get; init; } = string.Empty;
}
