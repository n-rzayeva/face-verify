using FaceVerify.Backend.Data;
using FaceVerify.Backend.Models;

namespace FaceVerify.Backend.Services;

public class VerificationService
{
    private readonly JwtService _jwtService;
    private readonly MlApiService _mlApiService;
    private readonly AppDbContext _dbContext;
    private readonly IConfiguration _configuration;

    public VerificationService(
        JwtService jwtService,
        MlApiService mlApiService,
        AppDbContext dbContext,
        IConfiguration configuration)
    {
        _jwtService = jwtService;
        _mlApiService = mlApiService;
        _dbContext = dbContext;
        _configuration = configuration;
    }

    public string Start(string userId)
    {
        var challenges = _configuration
            .GetSection("Verification:Challenges")
            .Get<List<string>>()!;

        // Randomise challenge order
        challenges = challenges.OrderBy(_ => Guid.NewGuid()).ToList();

        var session = new VerificationSession
        {
            SessionId = Guid.NewGuid().ToString(),
            UserId = userId,
            Challenges = challenges,
            Completed = new List<string>(),
            AttemptCounts = challenges.ToDictionary(c => c, c => 0)
        };

        return _jwtService.GenerateToken(session);
    }

    public async Task<(bool passed, List<string> failReasons, string? nextChallenge, bool allComplete, string token)>
        ProcessChallengeAsync(string token, List<PhotoDto> frames)
    {
        var session = _jwtService.ValidateAndExtract(token);
        if (session is null)
            return (false, new List<string> { "INVALID_OR_EXPIRED_TOKEN" }, null, false, token);

        var challengeType = session.Challenges.FirstOrDefault(c => !session.Completed.Contains(c));
        if (challengeType is null)
            return (false, new List<string> { "ALL_CHALLENGES_ALREADY_COMPLETED" }, null, false, token);

        var maxAttempts = int.Parse(_configuration["Verification:MaxAttemptsPerChallenge"]!);
        session.AttemptCounts[challengeType]++;

        if (session.AttemptCounts[challengeType] > maxAttempts)
            return (false, new List<string> { "MAX_ATTEMPTS_EXCEEDED" }, null, false, token);

        var result = await _mlApiService.AnalyzeChallengeAsync(challengeType, frames);
        if (result is null)
            return (false, new List<string> { "ML_API_ERROR" }, null, false, token);

        if (!result.Passed)
        {
            var updatedToken = _jwtService.GenerateToken(session);
            return (false, result.FailReasons, challengeType, false, updatedToken);
        }

        // Challenge passed
        session.Completed.Add(challengeType);

        // Store best frame if BLINK
        if (challengeType == "BLINK" && result.BestFrame is not null)
        {
            var expiryMinutes = int.Parse(_configuration["Jwt:ExpiryMinutes"]!);
            var frame = new VerificationFrame
            {
                SessionId = Guid.Parse(session.SessionId),
                BestFrame = result.BestFrame.Base64,
                ExpiresAt = DateTime.UtcNow.AddMinutes(expiryMinutes)
            };
            _dbContext.VerificationFrames.Add(frame);
            await _dbContext.SaveChangesAsync();
        }

        var allComplete = session.Challenges.All(c => session.Completed.Contains(c));
        var next = session.Challenges.FirstOrDefault(c => !session.Completed.Contains(c));
        var newToken = _jwtService.GenerateToken(session);

        return (true, new List<string>(), next, allComplete, newToken);
    }

    public async Task<(bool passed, float similarityScore, float livenessScore, string? failReason)>
        CompleteAsync(string token)
    {
        var session = _jwtService.ValidateAndExtract(token);
        if (session is null)
            return (false, 0, 0, "INVALID_OR_EXPIRED_TOKEN");

        if (!session.Challenges.All(c => session.Completed.Contains(c)))
            return (false, 0, 0, "NOT_ALL_CHALLENGES_COMPLETED");

        var frame = await _dbContext.VerificationFrames.FindAsync(Guid.Parse(session.SessionId));
        if (frame is null || frame.ExpiresAt < DateTime.UtcNow)
            return (false, 0, 0, "SESSION_EXPIRED");

        var idPhoto = LoadIdPhoto(session.UserId);
        if (idPhoto is null)
            return (false, 0, 0, "ID_PHOTO_NOT_FOUND");

        var matchResult = await _mlApiService.AnalyzeMatchAsync(
            new PhotoDto { Base64 = frame.BestFrame, Label = "best_frame" },
            new PhotoDto { Base64 = idPhoto, Label = "id_photo" }
        );

        if (matchResult is null)
            return (false, 0, 0, "ML_API_ERROR");

        _dbContext.VerificationFrames.Remove(frame);
        await _dbContext.SaveChangesAsync();

        var passed = matchResult.SimilarityScore >= float.Parse(
            _configuration["Verification:SimilarityThreshold"] ?? "0.75");

        return (passed, matchResult.SimilarityScore, matchResult.LivenessScore, null);
    }

    private string? LoadIdPhoto(string userId)
    {
        var basePath = _configuration["Verification:StaticPhotosPath"]!;
        var extensions = new[] { ".jpg", ".jpeg" };

        foreach (var ext in extensions)
        {
            var path = Path.Combine(basePath, $"{userId}{ext}");
            if (File.Exists(path))
                return Convert.ToBase64String(File.ReadAllBytes(path));
        }

        return null;
    }
}