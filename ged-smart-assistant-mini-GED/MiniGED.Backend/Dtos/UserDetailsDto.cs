using MiniGED.API.Models;

namespace MiniGED.API.Dtos
{
    public class UserDetailsDto : UserDto
    {
        public DateTime CreatedDate { get; set; } 

        public int FileUploadCount { get; set; }

public List<UserDocumentDto>? Userdocuments { get; set; }


    }
}
