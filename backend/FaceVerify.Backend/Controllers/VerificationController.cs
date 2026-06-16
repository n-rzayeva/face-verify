using FaceVerify.Backend.Services;
using Microsoft.AspNetCore.Mvc;

namespace FaceVerify.Backend.Controllers;

public class StartRequest
{
    public string UserId { get; set; } = string.Empty;
}

public class ChallengeRequest
{
    public string Token { get; set; } = string.Empty;
    public List<PhotoDto> Frames { get; set; } = new();
}

public class CompleteRequest
{
    public string Token { get; set; } = string.Empty;
}

[ApiController]
[Route("api/verification")]
public class VerificationController : ControllerBase
{
    private readonly VerificationService _verificationService;
    private readonly JwtService _jwtService;

    public VerificationController(VerificationService verificationService, JwtService jwtService)
    {
        _verificationService = verificationService;
        _jwtService = jwtService;
    }

    [HttpPost("start")]
    public IActionResult Start([FromBody] StartRequest request)
    {
        if (string.IsNullOrEmpty(request.UserId))
            return BadRequest(new { error = "user_id is required." });

        var token = _verificationService.Start(request.UserId);
        var session = _jwtService.ValidateAndExtract(token);

        return Ok(new
        {
            token,
            challenges = session!.Challenges
        });
    }

    [HttpPost("challenge")]
    public async Task<IActionResult> Challenge([FromBody] ChallengeRequest request)
    {
        if (string.IsNullOrEmpty(request.Token))
            return BadRequest(new { error = "token is required." });
        if (request.Frames is null || request.Frames.Count == 0)
            return BadRequest(new { error = "frames are required." });

        var (passed, failReasons, nextChallenge, allComplete, newToken) =
            await _verificationService.ProcessChallengeAsync(
                request.Token,
                request.Frames
            );

        if (!passed)
            return Ok(new
            {
                passed = false,
                fail_reasons = failReasons,
                next_challenge = (string?)null,
                all_complete = false,
                token = newToken
            });

        return Ok(new
        {
            passed = true,
            fail_reasons = new List<string>(),
            next_challenge = nextChallenge,
            all_complete = allComplete,
            token = newToken
        });
    }

    [HttpPost("complete")]
    public async Task<IActionResult> Complete([FromBody] CompleteRequest request)
    {
        if (string.IsNullOrEmpty(request.Token))
            return BadRequest(new { error = "token is required." });

        var (passed, similarityScore, livenessScore, failReason) =
            await _verificationService.CompleteAsync(request.Token);

        if (!passed && failReason is not null)
            return Ok(new
            {
                passed = false,
                fail_reason = failReason,
                similarity_score = 0f,
                liveness_score = 0f
            });

        return Ok(new
        {
            passed,
            fail_reason = (string?)null,
            similarity_score = similarityScore,
            liveness_score = livenessScore
        });
    }
}