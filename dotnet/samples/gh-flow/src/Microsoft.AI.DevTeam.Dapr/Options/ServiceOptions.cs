using System.ComponentModel.DataAnnotations;

namespace Microsoft.AI.DevTeam.Dapr;
public class ServiceOptions
{
    [Required]
    public required Uri IngesterUrl { get; set; }
}