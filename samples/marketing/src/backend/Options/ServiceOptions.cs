using System.ComponentModel.DataAnnotations;

namespace Marketing.Options;
public class ServiceOptions
{
    private string _ingesterUrl;

    [Required]
    public string IngesterUrl { get; set; }
}