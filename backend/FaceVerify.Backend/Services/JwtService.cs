using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using FaceVerify.Backend.Models;
using Microsoft.IdentityModel.Tokens;

namespace FaceVerify.Backend.Services;

public class JwtService
{
    private readonly IConfiguration _configuration;
    private readonly string _secret;
    private readonly int _expiryMinutes;

    public JwtService(IConfiguration configuration)
    {
        _configuration = configuration;
        _secret = configuration["Jwt:Secret"]!;
        _expiryMinutes = int.Parse(configuration["Jwt:ExpiryMinutes"]!);
    }

    public string GenerateToken(VerificationSession session)
    {
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_secret));
        var credentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new[]
        {
            new Claim("session_id", session.SessionId),
            new Claim("user_id", session.UserId),
            new Claim("challenges", JsonSerializer.Serialize(session.Challenges)),
            new Claim("completed", JsonSerializer.Serialize(session.Completed)),
            new Claim("attempt_counts", JsonSerializer.Serialize(session.AttemptCounts)),
            new Claim("challenge_confidences", JsonSerializer.Serialize(session.ChallengeConfidences)),
        };

        var token = new JwtSecurityToken(
            claims: claims,
            expires: DateTime.UtcNow.AddMinutes(_expiryMinutes),
            signingCredentials: credentials
        );

        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    public VerificationSession? ValidateAndExtract(string token)
    {
        try
        {
            var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_secret));
            var handler = new JwtSecurityTokenHandler();

            handler.ValidateToken(token, new TokenValidationParameters
            {
                ValidateIssuerSigningKey = true,
                IssuerSigningKey = key,
                ValidateIssuer = false,
                ValidateAudience = false,
                ClockSkew = TimeSpan.Zero
            }, out var validatedToken);

            var jwt = (JwtSecurityToken)validatedToken;

            return new VerificationSession
            {
                SessionId = jwt.Claims.First(c => c.Type == "session_id").Value,
                UserId = jwt.Claims.First(c => c.Type == "user_id").Value,
                Challenges = JsonSerializer.Deserialize<List<string>>(
                    jwt.Claims.First(c => c.Type == "challenges").Value)!,
                Completed = JsonSerializer.Deserialize<List<string>>(
                    jwt.Claims.First(c => c.Type == "completed").Value)!,
                AttemptCounts = JsonSerializer.Deserialize<Dictionary<string, int>>(
                    jwt.Claims.First(c => c.Type == "attempt_counts").Value)!,
                ChallengeConfidences = JsonSerializer.Deserialize<Dictionary<string, float>>(
                    jwt.Claims.First(c => c.Type == "challenge_confidences").Value)!,
            };
        }
        catch
        {
            return null;
        }
    }
}