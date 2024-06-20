using System.ComponentModel.DataAnnotations;

namespace Marketing.Options;
public class QdrantOptions
{
    [Required]
    public required string Endpoint { get; set; }
    [Required]
    public required int VectorSize { get; set; }
}
