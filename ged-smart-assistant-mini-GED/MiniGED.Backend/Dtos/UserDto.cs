namespace MiniGED.API.Dtos
{
    public class UserDto 
    {
        public int  Id { get; set; }
        public string Username { get; set; } = null!;

        public string? Role { get; set; }
        public string FullName { get; set; } = null!;
        public string Email { get; set; } = null!;
        public string PhoneNumber { get; set; } = null!;
    }
}
