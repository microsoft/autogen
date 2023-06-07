using System.Text.Json.Serialization;

public class Subtask
{
    [JsonPropertyName("subtask")]
    public string Name { get; set; }
    [JsonPropertyName("LLM_prompt")]
    public string LLMPrompt { get; set; }
}

public class Step
{
    [JsonPropertyName("step")]
    public string Name { get; set; }
    [JsonPropertyName("description")]
    public string Description { get; set; }
    [JsonPropertyName("subtasks")]
    public List<Subtask> Subtasks { get; set; }
}

public class DevLeadPlanResponse
{
    [JsonPropertyName("steps")]
    public List<Step> Steps { get; set; }
}