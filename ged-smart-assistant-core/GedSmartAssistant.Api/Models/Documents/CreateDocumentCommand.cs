namespace GedSmartAssistant.Api.Models.Documents;

public sealed class CreateDocumentCommand
{
    public string Title { get; init; } = string.Empty;
    public string Description { get; init; } = string.Empty;
}
