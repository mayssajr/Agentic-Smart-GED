using Microsoft.EntityFrameworkCore;
using MiniGED.API.Data;
using MiniGED.API.Models;
using MiniGED.API.Services;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Routing;

namespace MiniGED.API.Config
{
    internal sealed class LoginUserWithRefreshToken(ApplicationDbContext _context, TokenService _tokenService)
    {
        public sealed record Request(string RefreshToken);
        public sealed record Response(string AccessToken, string RefreshToken);

        public async Task<Response> Handle(Request request)
        {
            RefreshToken? refreshToken = await _context.RefreshTokens
                .Include(r => r.User)
                .FirstOrDefaultAsync(r => r.Token == request.RefreshToken);

            if (refreshToken == null || refreshToken.ExpiresOnUtc < DateTime.UtcNow)
            {
                throw new ApplicationException("Refresh Token Has Expired");
            }

            var roles = _context.UserRoles
                .Where(ur => ur.UserId == refreshToken.User.Id)
                .Select(ur => ur.Role.Name)
                .ToList();

            var accessToken = _tokenService.CreateToken(refreshToken.User, roles);

            refreshToken.Token = _tokenService.GenerateRefreshToken();
            refreshToken.ExpiresOnUtc = DateTime.UtcNow.AddDays(7);

            await _context.SaveChangesAsync();

            return new Response(accessToken, refreshToken.Token);
        }

        internal sealed class Endpoint : IEndpoint
        {
            public void MapEndpoint(IEndpointRouteBuilder app)
            {
                app.MapPost("users/refresh-token", async (Request request, LoginUserWithRefreshToken useCase) =>
                    await useCase.Handle(request))
                    .WithTags(UserEndpoints.Tag)
                    .WithName("RefreshToken") // Add a name for OpenAPI
                    .Produces<LoginUserWithRefreshToken.Response>(StatusCodes.Status200OK)
                    .Produces(StatusCodes.Status400BadRequest);
            }
        }
        public static class UserEndpoints
        {
            public const string Tag = "Users";
        }
        public interface IEndpoint
        {
            void MapEndpoint(IEndpointRouteBuilder app);
        }
    }
}