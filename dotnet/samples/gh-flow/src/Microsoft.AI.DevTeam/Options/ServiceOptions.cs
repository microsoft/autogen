using System.ComponentModel.DataAnnotations;

namespace Microsoft.AI.DevTeam;
public class ServiceOptions
{
    private string _ingesterUrl;

    [Required]
    public string IngesterUrl { get; set; }
}