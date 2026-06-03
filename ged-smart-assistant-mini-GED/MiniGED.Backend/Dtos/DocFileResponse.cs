namespace MiniGED.API.Dtos
{
    public class DocFileResponse
    {
        public int Id { get; set; }
        public string FileName { get; set; } = null!;
        public string FilePath { get; set; } = null!;
        public long FileSize { get; set; }

       // public int DocumentId { get; set; }
    }
}
