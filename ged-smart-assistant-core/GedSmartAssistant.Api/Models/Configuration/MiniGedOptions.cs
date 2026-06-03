namespace GedSmartAssistant.Api.Models.Configuration;

public sealed class MiniGedOptions
{
    public const string SectionName = "MiniGed";

    public string BaseUrl { get; init; } = string.Empty;
}
