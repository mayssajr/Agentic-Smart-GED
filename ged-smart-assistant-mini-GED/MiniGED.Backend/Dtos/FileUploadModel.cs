using System.ComponentModel.DataAnnotations;

namespace MiniGED.API.Dtos;
public class FileUploadModel
{
    [Required]
public List<IFormFile>? Files { get; set; }

    public int DocumentId { get; set; }
    
}