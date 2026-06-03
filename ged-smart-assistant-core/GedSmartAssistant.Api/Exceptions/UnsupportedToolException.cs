namespace GedSmartAssistant.Api.Exceptions;

public sealed class UnsupportedToolException : Exception
{
    public UnsupportedToolException(string? toolName)
        : base($"Unsupported tool '{toolName ?? "<null>"}'.")
    {
    }
}
