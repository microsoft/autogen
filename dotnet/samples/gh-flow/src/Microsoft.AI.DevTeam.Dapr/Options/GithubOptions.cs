using System.ComponentModel.DataAnnotations;

namespace Microsoft.AI.DevTeam.Dapr;
public class GithubOptions
{
    [Required]
    public string AppKey { get; set; }
    [Required]
    public int AppId { get; set; }
    [Required]
    public long InstallationId { get; set; }
    [Required]
    public string WebhookSecret { get; set; }
}