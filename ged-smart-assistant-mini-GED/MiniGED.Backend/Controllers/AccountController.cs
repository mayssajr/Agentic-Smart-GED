using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using MiniGED.API.Data;
using MiniGED.API.Dtos;
using MiniGED.API.Models;
using MiniGED.API.Services;
using Microsoft.AspNetCore.Cors;

namespace MiniGED.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AccountController : ControllerBase
{
    private readonly ApplicationDbContext _context;
    private readonly TokenService _tokenService;
    private readonly PasswordService _passwordService;
public new sealed record Response (string AccessToken, string RefreshToken);
    public AccountController(ApplicationDbContext context, TokenService tokenService, PasswordService passwordService)
    {
        _context = context;
        _tokenService = tokenService;
        _passwordService = passwordService;
    }
    [EnableCors("AllowAll")]
    [HttpPost("register")]
    public async Task<IActionResult> Register(UserRegisterDto dto)
    {
        if (await _context.Users.AnyAsync(u => u.Email == dto.Email))
            return BadRequest("Email déjà utilisé.");

        var user = new User
        {
            Username = dto.Username,
            FullName = dto.FullName,
            Email = dto.Email,
            PasswordHashed = _passwordService.HashPassword(dto.Password),
            PhoneNumber = dto.PhoneNumber
        };

        _context.Users.Add(user);
        await _context.SaveChangesAsync();
        // Assign default User role
        var userRole = await _context.Roles.FirstAsync(r => r.Name == "User");
        _context.UserRoles.Add(new UserRole { UserId = user.Id, RoleId = userRole.Id });
        await _context.SaveChangesAsync();
        return Ok("Utilisateur enregistré avec succès.");
    }

    [HttpPost("login")]
    public async Task<IActionResult> Login(UserLoginDto dto)
    {
        var user = await _context.Users.FirstOrDefaultAsync(u => u.Email == dto.Email);
        if (user == null || user.PasswordHashed != _passwordService.HashPassword(dto.Password))
            return Unauthorized("Email ou mot de passe incorrect.");
        var roles = _context.UserRoles
            .Where(ur => ur.UserId == user.Id)
            .Select(ur => ur.Role.Name)
            .ToList();
        var token = _tokenService.CreateToken(user,roles);
        var refreshToken = new RefreshToken
        {
            UserId = user.Id,
            Token = _tokenService.GenerateRefreshToken(),
            ExpiresOnUtc = DateTime.UtcNow.AddMonths(1)
        };
        _context.RefreshTokens.Add(refreshToken);

        await _context.SaveChangesAsync();
        return Ok( new Response(  token,refreshToken.Token));
    }

    [Authorize]
    [HttpGet("me")]
    public async Task<IActionResult> Me()
    {
        var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);
        var user = await _context.Users.FindAsync(userId);
        if (user == null) return NotFound();

        return Ok(new
        {   
            user.Id,
            user.Username,
            user.FullName,
            user.Email,
            user.PhoneNumber
        });
    }

 
}
