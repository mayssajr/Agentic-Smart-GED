namespace GedSmartAssistant.Api.Exceptions;

public sealed class MissingSessionException : Exception
{
    public MissingSessionException() : base("No authenticated MiniGed session is available.")
    {
    }
}
