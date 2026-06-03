using System;
using Microsoft.AspNetCore.Mvc;
using MiniGED.API.Data;
using MiniGED.API.Models;

namespace MiniGED.API.Controllers
{

    [ApiController]
    [Route("api/[controller]")]
    public class RolesController : ControllerBase
    {
        private readonly ApplicationDbContext _db;
        public RolesController(ApplicationDbContext db) => _db = db;

        [HttpPost("create")]
        public async Task<IActionResult> Create(string name)
        {
            if (_db.Roles.Any(r => r.Name == name))
                return BadRequest("Role exists.");
            _db.Roles.Add(new Role {  Name = name });
            await _db.SaveChangesAsync();
            return Ok();
        }

        [HttpPost("assign")]
        public async Task<IActionResult> Assign(Guid userId, string roleName)
        {
            var user = _db.Users.Find(userId);
            var role = _db.Roles.FirstOrDefault(r => r.Name == roleName);
            if (user == null || role == null) return NotFound();

            _db.UserRoles.Add(new UserRole { UserId = user.Id, RoleId = role.Id });
            await _db.SaveChangesAsync();
            return Ok();
        }
    }

}
