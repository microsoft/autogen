public class AzureOptions
{
    public string SubscriptionId { get; set; }
    public string Location { get; set; }
    public string ContainerInstancesResourceGroup { get; set; }
    public string FilesShareName { get; set; }
    public string FilesAccountName { get; set; }
    public string FilesAccountKey { get; set; }
    public string CosmosConnectionString { get; set; }
    public string SandboxImage { get; set; }
    public string ManagedIdentity { get; set; }
}