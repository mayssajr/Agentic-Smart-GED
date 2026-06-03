using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;
namespace GedSmartAssistant.Api.Dtos.Requests
{
    public class ChatRequest
    {
        [Required]
        [JsonPropertyName("message")]
        public string Message { get; set; } = string.Empty;

        [JsonPropertyName("documentId")]
        public string? DocumentId { get; set; }

        [JsonPropertyName("documentType")]
        public string? DocumentType { get; set; }

        [JsonPropertyName("filename")]
        public string? Filename { get; set; }
    }
}
