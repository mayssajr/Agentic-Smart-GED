using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MiniGED.API.Data;
using MiniGED.API.Dtos;
using MiniGED.API.Models;

namespace MiniGED.API.Controllers
{

    [Authorize]
    [ApiController]
    [Route("/api/[controller]")]
    public class UserController : ControllerBase
    {

        private readonly ApplicationDbContext _context;

        public UserController(ApplicationDbContext context)
        {
            _context = context;
        }

        [HttpGet]
        public ActionResult GetAllUsers()
        {
            var users = _context.Users
                        .Select(u => new UserDto
                        {
                            Id = u.Id,
                            Username = u.Username,
                            FullName = u.FullName,
                            Email = u.Email,
                            Role = u.UserRoles
                                      .Select(ur => ur.Role.Name)
                                      .FirstOrDefault(),
                            PhoneNumber = u.PhoneNumber
                        })
                        .ToList();
            return Ok(users);
        }

        [HttpGet("{id}")]
        public ActionResult GetUser(int id)
        {
var user = _context.Users.FirstOrDefault(x => x.Id == id);
            if (user == null) return NotFound();
            var documents = _context.Documents
                .Where(x => x.UserId == user.Id)
                
                .ToList();
            int filesUploaded = 0;
            var userDocuments = new List<UserDocumentDto>();
            foreach(Document document in documents)
            {
                filesUploaded += document.Files.Count;
                userDocuments.Add(new UserDocumentDto
                {
                    Title = document.Title,
                    UploadedAt = document.UploadedAt,
                });
            }
            var userdto = new UserDetailsDto
            {
                Id = user.Id,
                Username = user.Username,
                FullName = user.FullName,
                Email = user.Email,
                PhoneNumber  = user.PhoneNumber,
                CreatedDate = user.CreateDate,
                Userdocuments = userDocuments,
                FileUploadCount = filesUploaded
                
            };
            return Ok(userdto);
        }


        [HttpGet("search")]
        public ActionResult SearchUsers([FromQuery] string query)
        {
            if (string.IsNullOrWhiteSpace(query))
                return BadRequest("Search query cannot be empty.");

            var normalizedQuery = query.ToLower();

            var users = _context.Users
                .Where(u =>
                    u.Username.ToLower().Contains(normalizedQuery) ||
                    u.FullName.ToLower().Contains(normalizedQuery) ||
                    u.Email.ToLower().Contains(normalizedQuery) ||
                    u.PhoneNumber.ToLower().Contains(normalizedQuery))
                .Select(u => new UserDto
                {
                    Id = u.Id,
                    Username = u.Username,
                    FullName = u.FullName,
                    Email = u.Email,
                    Role = u.UserRoles
                              .Select(ur => ur.Role.Name)
                              .FirstOrDefault(),
                    PhoneNumber = u.PhoneNumber
                })
                .ToList();

            return Ok(users);
        }

    }
}
