using Microsoft.Extensions.Options;
using Octokit;

[System.Diagnostics.CodeAnalysis.SuppressMessage("Usage", "CA2007: Do not directly await a Task", Justification = "Durable functions")]
public class GithubService
{
    private readonly GithubOptions _githubSettings;

    public GithubService(IOptions<GithubOptions> ghOptions)
    {
        _githubSettings = ghOptions.Value;
    }
    public async Task<GitHubClient> GetGitHubClient()
    {
        // Use GitHubJwt library to create the GitHubApp Jwt Token using our private certificate PEM file
        var generator = new GitHubJwt.GitHubJwtFactory(
            new GitHubJwt.StringPrivateKeySource(_githubSettings.AppKey),
            new GitHubJwt.GitHubJwtFactoryOptions
            {
                AppIntegrationId = _githubSettings.AppId, // The GitHub App Id
                ExpirationSeconds = 600 // 10 minutes is the maximum time allowed
            }
        );

        var jwtToken = generator.CreateEncodedJwtToken();
        var appClient = new GitHubClient(new ProductHeaderValue("SK-DEV-APP"))
        {
            Credentials = new Credentials(jwtToken, AuthenticationType.Bearer)
        };
        var response = await appClient.GitHubApps.CreateInstallationToken(_githubSettings.InstallationId);
        return new GitHubClient(new ProductHeaderValue($"SK-DEV-APP-Installation{_githubSettings.InstallationId}"))
        {
            Credentials = new Credentials(response.Token)
        };
    }
}