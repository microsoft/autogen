using System.ComponentModel.DataAnnotations;

namespace Microsoft.AI.DevTeam;
public class ServiceOptions
{
    [Required]
    public required Uri IngesterUrl { get; set; }
}