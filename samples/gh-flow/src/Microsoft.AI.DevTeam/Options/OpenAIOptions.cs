namespace Microsoft.AI.DevTeam;
public class OpenAIOptions
{
    public string ServiceType { get; set; }
    public string ServiceId { get; set; }
    public string DeploymentOrModelId { get; set; }
    public string EmbeddingDeploymentOrModelId { get; set; }
    public string Endpoint { get; set; }
    public string ApiKey { get; set; }
}
