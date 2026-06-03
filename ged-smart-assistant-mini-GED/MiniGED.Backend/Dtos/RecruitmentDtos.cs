namespace MiniGED.API.Dtos;
 
//POST /api/recruitment/apply 
public class ApplyRequest
{
    public string    CandidateName  { get; set; } = string.Empty;
    public string    CandidateEmail { get; set; } = string.Empty;
    public string    CandidatePhone { get; set; } = string.Empty;
    public string    Position       { get; set; } = string.Empty;
    public List<IFormFile> Files { get; set; } = new();
}
 
//PATCH /api/recruitment/application/{id}/status
public class UpdateCandidateStatusRequest
{
    public string Status     { get; set; } = "";
    public string Notes      { get; set; } = "";
    public List<RhNote> RhNotes { get; set; } = new();  
}
public class RhNote
{
    public string Sign { get; set; } = "+";  // "+" ou "-"
    public string Text { get; set; } = "";
}

public sealed class UpdateAiScoreRequest
{
    public int     AiScore          { get; set; }
    public string? AiRecommendation { get; set; }
}