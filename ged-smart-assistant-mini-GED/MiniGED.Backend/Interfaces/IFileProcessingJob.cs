using MiniGED.API.Dtos;

namespace MiniGED.API.Interfaces;

public interface IFileProcessingJob
{
    Task ProcessFileAsync(FileProcessingPayload payload);
}
