namespace GedSmartAssistant.Api.Exceptions;

public sealed class MiniGedUnauthorizedException : Exception
{
    public MiniGedUnauthorizedException(string message) : base(message)
    {
    }
}
