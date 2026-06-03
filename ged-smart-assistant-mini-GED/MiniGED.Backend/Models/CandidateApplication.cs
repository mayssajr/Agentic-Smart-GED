namespace MiniGED.API.Models;
 
public class CandidateApplication : BaseModel
{
    public string CandidateName  { get; set; } = string.Empty;
    public string CandidateEmail { get; set; } = string.Empty;
    public string CandidatePhone { get; set; } = string.Empty;
    public string Position       { get; set; } = string.Empty;
 
    public int       DocumentId { get; set; }
    public Document? Document   { get; set; }
 
    public CandidateStatus Status { get; set; } = CandidateStatus.Recu;
    public string?          Notes  { get; set; }

    public int?    AiScore          { get; set; } 
    public string? AiRecommendation { get; set; }
}
 

public enum CandidateStatus
{
    Recu          = 0,   // dossier uploadé, en attente d'analyse
    EnAnalyse     = 1,   // IA en cours de traitement
    ATraiter      = 2,   // analysé, en attente décision RH
    Entretien     = 3,   // entretien planifié
    Accepte       = 4,   // candidature retenue
    Refuse        = 5,   // candidature rejetée
    ListeAttente  = 6,   // profil intéressant, pas de poste maintenant
}