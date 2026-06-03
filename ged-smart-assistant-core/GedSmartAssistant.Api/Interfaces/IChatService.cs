using GedSmartAssistant.Api.Dtos.Requests;
using GedSmartAssistant.Api.Dtos.Response;

namespace GedSmartAssistant.Api.Interfaces;

public interface IChatService
{
    Task<ChatResponse> ProcessAsync(ChatRequest request, CancellationToken cancellationToken);
}
