namespace FaceVerify.Backend.Models;

public class VerificationSession
{
    public string SessionId { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public List<string> Challenges { get; set; } = new();
    public List<string> Completed { get; set; } = new();
    public Dictionary<string, int> AttemptCounts { get; set; } = new();
    public Dictionary<string, float> ChallengeConfidences { get; set; } = new();
}