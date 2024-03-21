namespace Microsoft.SKDevTeam;

public class SemanticFunctionConfig
{
    public string PromptTemplate { get; set; }
    public string Name { get; set; }
    public string SkillName { get; set; }
    public string Description { get; set; }
    public int MaxTokens { get; set; }
    public double Temperature { get; set; }
    public double TopP { get; set; }
    public double PPenalty { get; set; }
    public double FPenalty { get; set; }
    public static SemanticFunctionConfig ForSkillAndFunction(string skillName, string functionName) => 
    (skillName, functionName) switch
    {
        (nameof(PM), nameof(PM.Readme)) => PM.Readme,
        (nameof(DevLead), nameof(DevLead.Plan)) => DevLead.Plan,
        (nameof(Developer), nameof(Developer.Implement)) => Developer.Implement,
        (nameof(Developer), nameof(Developer.Improve)) => Developer.Improve,
        _ => throw new ArgumentException($"Unable to find {skillName}.{functionName}")
    };
}