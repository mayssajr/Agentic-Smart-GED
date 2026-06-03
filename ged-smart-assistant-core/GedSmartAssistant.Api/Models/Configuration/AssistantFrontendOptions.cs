namespace GedSmartAssistant.Api.Models.Configuration;

public sealed class AssistantFrontendOptions
{
    public const string SectionName = "AssistantFrontend";

    public string[] AllowedOrigins { get; init; } = [];
}
