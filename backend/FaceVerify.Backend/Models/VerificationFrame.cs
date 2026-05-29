namespace FaceVerify.Backend.Models;

public class VerificationFrame
{
    public Guid SessionId { get; set; }
    public string BestFrame { get; set; } = string.Empty;  // base64
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime ExpiresAt { get; set; }
}