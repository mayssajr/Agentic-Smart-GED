using System;
using MiniGED.API.Data;
using MiniGED.API.Interfaces;
using MiniGED.API.Models;

namespace MiniGED.API.Services
{
    public class FileService : IFileService
    {




        private readonly ApplicationDbContext _context;
        public FileService(ApplicationDbContext context)
        {
            _context = context;
        }
        public async Task<string> UploadFile(DocumentFile docFile, IFormFile file)
        {
            if (file == null || file.Length == 0)
            {
                return "File not selected";
            }

            var folderName = Path.Combine("Resource", "AllFiles");
            var pathToSave = Path.Combine(Directory.GetCurrentDirectory(), folderName);
            if (!Directory.Exists(pathToSave))
                Directory.CreateDirectory(pathToSave);
            var fileName = docFile.Id.ToString() +".pdf";
            var fullPath = Path.Combine(pathToSave, fileName);
            var dbPath = Path.Combine(folderName, fileName);

            if (System.IO.File.Exists(fullPath))
                return "file Already Exists";

            await using (var stream = new FileStream(fullPath, FileMode.Create))
            {
                await file.CopyToAsync(stream);
            }
            return dbPath;
        }
        
        public async Task<string> UpdateFile(IFormFile file)
        {
if (file == null || file.Length == 0)
            {
                return "file not selected";
            }

            var folderName = Path.Combine("Resource", "AllFiles");
            var pathToSave = Path.Combine(Directory.GetCurrentDirectory(), folderName);
            if (!Directory.Exists(pathToSave))
                Directory.CreateDirectory(pathToSave);
            var fileName = file.Name;
            var fullPath = Path.Combine(pathToSave, fileName);
            var dbPath = Path.Combine(folderName, fileName);

            if (System.IO.File.Exists(fullPath))
                return "file Already Exists";

            await using (var stream = new FileStream(fullPath, FileMode.Create))
            {
                await file.CopyToAsync(stream);
            }

            return dbPath;
        }

        /*public async Task PostMultiFileAsync(List<FileUploadModel> fileData)
        {
            try
            {
                foreach(FileUploadModel file in fileData)
                {
                    var fileDetails = new FileDetails()
                    {
                        ID = 0,
                        FileName = file.FileDetails.FileName,
                        FileType = file.FileType,
                    };

                    using (var stream = new MemoryStream())
                    {
                        file.FileDetails.CopyTo(stream);
                        fileDetails.FileData = stream.ToArray();
                    }

                    var result = dbContextClass.FileDetails.Add(fileDetails);
                }
                await dbContextClass.SaveChangesAsync();
            }
            catch (Exception)
            {
                throw;
            }
        }
       
        public async Task DownloadFileById(int Id)
        {
            try
            {
                var DOCfile =  _context.DocumentFiles.Where(x => x.Id == Id).FirstOrDefaultAsync();

                var content = new System.IO.MemoryStream(file.Result.FileData);
                var path = Path.Combine(
                    Directory.GetCurrentDirectory(), "FileDownloaded",
                    file.Result.FileName);

                await CopyStream(content, path);
            }
            catch (Exception)
            {
                throw;
            }
        }

        public async Task CopyStream(Stream stream, string downloadPath)
        {
            using (var fileStream = new FileStream(downloadPath, FileMode.Create, FileAccess.Write))
            {
                await stream.CopyToAsync(fileStream);
            }
        }*/


        // M�thode pour supprimer physiquement un fichier � partir de son chemin
        public  Boolean DeleteFile(int id)
        {
            var folderName = Path.Combine("Resource", "AllFiles");
            var pathToSave = Path.Combine(Directory.GetCurrentDirectory(), folderName);
            if (!Directory.Exists(pathToSave))
               return false;
            var fileName = id.ToString() + ".pdf";
            var fullPath = Path.Combine(pathToSave, fileName);
            if (!System.IO.File.Exists(fullPath))
                return false;

            try
            {
                System.IO.File.Delete(fullPath);
                return true;
            }
catch (Exception)
                {
                    // Log exception
                    return false;
                }
        }

       

        public void ChangeFileStatus(int fileId, FileProcessingStatus processing)
        {
            DocumentFile? documentFile = _context.DocumentFiles.Find(fileId);
            if (documentFile == null)
            {
                return;
            }

            documentFile.Status = processing;
            documentFile.UpdateDate = DateTime.UtcNow;
            _context.SaveChanges();
        }
    }
}
