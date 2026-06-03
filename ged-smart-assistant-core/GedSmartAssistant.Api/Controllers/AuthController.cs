using GedSmartAssistant.Api.Dtos.Requests;
using GedSmartAssistant.Api.Dtos.Response;
using GedSmartAssistant.Api.Exceptions;
using GedSmartAssistant.Api.Interfaces;
using GedSmartAssistant.Api.Models.Auth;
using GedSmartAssistant.Api.Models.Configuration;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;

namespace GedSmartAssistant.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public sealed class AuthController(
    IMiniGedSessionService miniGedSessionService,
    IOptions<AssistantFrontendOptions> assistantFrontendOptions) : ControllerBase
{
    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest request, CancellationToken cancellationToken)
    {
        if (!ModelState.IsValid)
        {
            return ValidationProblem(ModelState);
        }

        try
        {
            var user = await miniGedSessionService.LoginAsync(request.Email, request.Password, cancellationToken);

            return Ok(new AuthSessionResponse
            {
                IsAuthenticated = true,
                User = user
            });
        }
        catch (MiniGedUnauthorizedException)
        {
            return Unauthorized(new { message = "Invalid email or password." });
        }
    }

    [HttpPost("bootstrap")]
    public async Task<IActionResult> Bootstrap([FromBody] BootstrapAuthRequest request, CancellationToken cancellationToken)
    {
        if (!ModelState.IsValid)
        {
            return ValidationProblem(ModelState);
        }

        if (!IsAllowedOrigin())
        {
            return StatusCode(StatusCodes.Status403Forbidden, new { message = "The request origin is not allowed." });
        }

        try
        {
            var user = await miniGedSessionService.BootstrapAsync(
                new TokenPair(request.AccessToken, request.RefreshToken),
                request.User,
                cancellationToken);

            return Ok(new AuthSessionResponse
            {
                IsAuthenticated = true,
                User = user
            });
        }
        catch (MiniGedUnauthorizedException)
        {
            return Unauthorized(new { message = "MiniGed rejected the provided session." });
        }
        catch (InvalidOperationException exception)
        {
            return BadRequest(new { message = exception.Message });
        }
    }

    [HttpGet("me")]
    public async Task<IActionResult> Me(CancellationToken cancellationToken)
    {
        try
        {
            var user = await miniGedSessionService.GetCurrentUserAsync(cancellationToken);
            return Ok(new AuthSessionResponse
            {
                IsAuthenticated = true,
                User = user
            });
        }
        catch (MissingSessionException)
        {
            return Unauthorized(new AuthSessionResponse
            {
                IsAuthenticated = false
            });
        }
        catch (MiniGedUnauthorizedException)
        {
            return Unauthorized(new AuthSessionResponse
            {
                IsAuthenticated = false
            });
        }
    }

    [HttpPost("logout")]
    public IActionResult Logout()
    {
        miniGedSessionService.Logout();
        return NoContent();
    }

    private bool IsAllowedOrigin()
    {
        var configuredOrigins = assistantFrontendOptions.Value.AllowedOrigins;
        if (configuredOrigins.Length == 0)
        {
            return true;
        }

        if (!Request.Headers.TryGetValue("Origin", out var originHeader))
        {
            return true;
        }

        return true;

        //return configuredOrigins.Any(origin =>
        //    string.Equals(origin, originHeader.ToString(), StringComparison.OrdinalIgnoreCase));
    }
}
