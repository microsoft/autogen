// Copyright (c) Microsoft Corporation. All rights reserved.
// GithubAuthService.cs

using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using DevTeam.Options;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;
using Octokit;

namespace DevTeam.Backend.Services;
public class GithubAuthService
{
    private readonly GithubOptions _githubSettings;
    private readonly ILogger<GithubAuthService> _logger;

    public GithubAuthService(IOptions<GithubOptions> ghOptions, ILogger<GithubAuthService> logger)
    {
        ArgumentNullException.ThrowIfNull(ghOptions);
        ArgumentNullException.ThrowIfNull(logger);
        _githubSettings = ghOptions.Value;
        _logger = logger;
    }

    public string GenerateJwtToken(string appId, string appKey, int minutes)
    {
        using var rsa = RSA.Create();
        rsa.ImportFromPem(appKey);
        var securityKey = new RsaSecurityKey(rsa);

        var credentials = new SigningCredentials(securityKey, SecurityAlgorithms.RsaSha256);

        var now = DateTime.UtcNow;
        var iat = new DateTimeOffset(now).ToUnixTimeSeconds();
        var exp = new DateTimeOffset(now.AddMinutes(minutes)).ToUnixTimeSeconds();

        var claims = new[] {
            new Claim(JwtRegisteredClaimNames.Iat, iat.ToString(), ClaimValueTypes.Integer64),
            new Claim(JwtRegisteredClaimNames.Exp, exp.ToString(), ClaimValueTypes.Integer64)
        };

        var token = new JwtSecurityToken(
            issuer: appId,
            claims: claims,
            expires: DateTime.Now.AddMinutes(10),
            signingCredentials: credentials
        );

        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    public GitHubClient GetGitHubClient()
    {
        try
        {
            var jwtToken = GenerateJwtToken(_githubSettings.AppId.ToString(), _githubSettings.AppKey, 10);
            var appClient = new GitHubClient(new ProductHeaderValue("SK-DEV-APP"))
            {
                Credentials = new Credentials(jwtToken, AuthenticationType.Bearer)
            };
            var response = appClient.GitHubApps.CreateInstallationToken(_githubSettings.InstallationId).Result;
            return new GitHubClient(new ProductHeaderValue($"SK-DEV-APP-Installation{_githubSettings.InstallationId}"))
            {
                Credentials = new Credentials(response.Token)
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting GitHub client");
            throw;
        }
    }
}
