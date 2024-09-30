namespace DevTeam;
public class DevLeadPlan
{
    public required List<StepDescription> Steps { get; set; }
}

public class StepDescription
{
    public string? Description { get; set; }
    public string? Step { get; set; }
    public List<SubtaskDescription>? Subtasks { get; set; }
}

public class SubtaskDescription
{
    public string? Subtask { get; set; }
    public string? Prompt { get; set; }
}