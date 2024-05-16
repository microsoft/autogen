using System.ComponentModel.DataAnnotations;

namespace Microsoft.AI.DevTeam;

public class AzureOptions
{
    [Required]
    public string SubscriptionId { get; set; }
    [Required]
    public string Location { get; set; }
    [Required]
    public string ContainerInstancesResourceGroup { get; set; }
    [Required]
    public string FilesShareName { get; set; }
    [Required]
    public string FilesAccountName { get; set; }
    [Required]
    public string FilesAccountKey { get; set; }
    [Required]
    public string SandboxImage { get; set; }
    public string ManagedIdentity { get; set; }
    public string CosmosConnectionString { get; set; }
}