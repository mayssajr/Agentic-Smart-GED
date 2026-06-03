using GedSmartAssistant.Api.Dtos.Requests;
using GedSmartAssistant.Api.Exceptions;
using GedSmartAssistant.Api.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace GedSmartAssistant.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public sealed class ChatController(IChatService chatService) : ControllerBase
{
    
    [HttpPost]
    public async Task<IActionResult> Chat([FromBody] ChatRequest request, CancellationToken cancellationToken)
    {
        // DEBUG
        Console.WriteLine($"[DEBUG Controller] Message='{request.Message}' | Body brut reçu");
        Console.WriteLine($"[DEBUG Controller] ModelState valid={ModelState.IsValid}");
        
        if (!ModelState.IsValid)
        {
            return ValidationProblem(ModelState);
        }

        try
        {
            var response = await chatService.ProcessAsync(request, cancellationToken);
            return Ok(response);
        }
        catch (MissingSessionException)
        {
            return Unauthorized(new { message = "You must log in before using the assistant." });
        }
        catch (UnsupportedToolException exception)
        {
            return BadRequest(new { message = exception.Message });
        }
        catch (InvalidOperationException exception)
        {
            return BadRequest(new { message = exception.Message });
        }
    }
    [HttpPost("debug")]
    public async Task<IActionResult> Debug([FromBody] System.Text.Json.JsonElement body)
    {
        Console.WriteLine($"[DEBUG] Body reçu: {body}");
        return Ok(new { received = body });
    }
}
