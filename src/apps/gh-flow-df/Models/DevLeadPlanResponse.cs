public class Subtask
{
    public string subtask { get; set; }
    public string prompt { get; set; }
}

public class Step
{
    public string description { get; set; }
    public string step { get; set; }
    public List<Subtask> subtasks { get; set; }
}

public class DevLeadPlanResponse
{
    public List<Step> steps { get; set; }
}