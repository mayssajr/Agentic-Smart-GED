namespace MiniGED.API.Models;

public class User : BaseModel
{
    public string Username { get; set; } = null!;
    public string FullName { get; set; } = null!;
    public string Email { get; set; } = null!;
    public string PasswordHashed { get; set; } = null!;
    public string PhoneNumber { get; set; } = null!;

    public ICollection<Document> Documents { get; set; } = new List<Document>();
    public ICollection<UserRole> UserRoles { get; set; } = new List<UserRole>();

}
