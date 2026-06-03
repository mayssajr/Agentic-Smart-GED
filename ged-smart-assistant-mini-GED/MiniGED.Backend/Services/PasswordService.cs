using System.Security.Cryptography;
using System.Text;

namespace MiniGED.API.Services
{
    public  class PasswordService
    {
      

        public string HashPassword(string password)
        {
            using var sha = SHA256.Create();
            var bytes = Encoding.UTF8.GetBytes(password);
            var hash = sha.ComputeHash(bytes);
            return Convert.ToBase64String(hash);
        }
    }
}
