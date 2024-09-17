using System.ComponentModel.DataAnnotations;

namespace DevTeam.Options;
public class QdrantOptions
{
    [Required]
    public required string Endpoint { get; set; }
    [Required]
    public required int VectorSize { get; set; }
    public string ApiKey { get; set; }  = "";
}