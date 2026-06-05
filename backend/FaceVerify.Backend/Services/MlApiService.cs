using System.Net.Http.Json;
using System.Text.Json;

namespace FaceVerify.Backend.Services;

public class PhotoDto
{
    public string Base64 { get; set; } = string.Empty;
    public string? Label { get; set; }
}

public class ChallengeFramesDto
{
    public string ChallengeType { get; set; } = string.Empty;
    public List<PhotoDto> Frames { get; set; } = new();
}

public class AnalyzeChallengeRequest
{
    public ChallengeFramesDto Challenge { get; set; } = new();
}

public class AnalyzeChallengeResponse
{
    public bool Passed { get; set; }
    public float Confidence { get; set; }
    public List<string> FailReasons { get; set; } = new();
    public PhotoDto? BestFrame { get; set; }
}

public class AnalyzeMatchRequest
{
    public PhotoDto BestFrame { get; set; } = new();
    public PhotoDto IdPhoto { get; set; } = new();
}

public class AnalyzeMatchResponse
{
    public float SimilarityScore { get; set; }
    public float LivenessScore { get; set; }
}

public class MlApiService
{
    private readonly HttpClient _httpClient;

    public MlApiService(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public async Task<AnalyzeChallengeResponse?> AnalyzeChallengeAsync(
        string challengeType,
        List<PhotoDto> frames)
    {
        var request = new AnalyzeChallengeRequest
        {
            Challenge = new ChallengeFramesDto
            {
                ChallengeType = challengeType,
                Frames = frames
            }
        };

        var options = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
        var response = await _httpClient.PostAsJsonAsync("/api/analyze/challenge", request, options);
        response.EnsureSuccessStatusCode();

        return await response.Content.ReadFromJsonAsync<AnalyzeChallengeResponse>(options);
    }

    public async Task<AnalyzeMatchResponse?> AnalyzeMatchAsync(
        PhotoDto bestFrame,
        PhotoDto idPhoto)
    {
        var request = new AnalyzeMatchRequest
        {
            BestFrame = bestFrame,
            IdPhoto = idPhoto
        };        
        var options = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
        var response = await _httpClient.PostAsJsonAsync("/api/analyze/match", request, options);
        response.EnsureSuccessStatusCode();

        return await response.Content.ReadFromJsonAsync<AnalyzeMatchResponse>(options);
    }
}