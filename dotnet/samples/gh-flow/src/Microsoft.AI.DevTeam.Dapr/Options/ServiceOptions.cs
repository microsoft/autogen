using System.ComponentModel.DataAnnotations;

namespace Microsoft.AI.DevTeam.Dapr;
public class ServiceOptions
{
    private string _ingesterUrl;

    [Required]
    public string IngesterUrl { get; set; }
}