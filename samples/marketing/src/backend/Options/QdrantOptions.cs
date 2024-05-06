using System.ComponentModel.DataAnnotations;

namespace Marketing.Options;
public class QdrantOptions
{
    [Required]
    public string Endpoint { get; set; }
    [Required]
    public int VectorSize { get; set; }
}