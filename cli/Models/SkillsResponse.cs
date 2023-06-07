using System.Text.Json.Serialization;

public class SkillsResponse
{
   [JsonPropertyName("response")]
    public string? Response { get; set; }
}