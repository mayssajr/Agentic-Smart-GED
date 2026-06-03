using MiniGED.API.Models;

namespace MiniGED.API.Interfaces
{
    public interface IFileService
    {
        public Task<string> UploadFile(DocumentFile docFile, IFormFile file);

        public Task<string> UpdateFile(IFormFile file);

        public bool DeleteFile(int id);
        void ChangeFileStatus(int fileId, FileProcessingStatus processing);
    }
}
