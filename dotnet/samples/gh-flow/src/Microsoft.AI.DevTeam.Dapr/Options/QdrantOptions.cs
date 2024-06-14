using System.ComponentModel.DataAnnotations;

namespace Microsoft.AI.DevTeam.Dapr;
public class QdrantOptions
{
    [Required]
    public string Endpoint { get; set; }
    [Required]
    public int VectorSize { get; set; }
}