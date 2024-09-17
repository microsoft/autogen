using System.ComponentModel.DataAnnotations;

namespace DevTeam.Options;

public class AzureOptions
{
    [Required]
    public required string SubscriptionId { get; set; }
    [Required]
    public required string Location { get; set; }
    [Required]
    public required string ContainerInstancesResourceGroup { get; set; }
    [Required]
    public required string FilesShareName { get; set; }
    [Required]
    public required string FilesAccountName { get; set; }
    [Required]
    public required string FilesAccountKey { get; set; }
    [Required]
    public required string SandboxImage { get; set; }
}