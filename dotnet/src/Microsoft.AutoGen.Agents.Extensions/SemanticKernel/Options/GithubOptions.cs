using System.ComponentModel.DataAnnotations;

namespace Microsoft.AutoGen.Agents.Extensions.SemanticKernel;
public class GithubOptions
{
    [Required]
    public required string AppKey { get; set; }
    [Required]
    public int AppId { get; set; }
    [Required]
    public long InstallationId { get; set; }
    [Required]
    public required string WebhookSecret { get; set; }
}