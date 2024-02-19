namespace Microsoft.AI.DevTeam.Skills;

public static class Skills
{
    public static string ForSkillAndFunction(string skillName, string functionName) => 
    (skillName, functionName) switch
    {
        (nameof(PM), nameof(PM.BootstrapProject)) => PM.BootstrapProject,
        (nameof(PM), nameof(PM.Readme)) => PM.Readme,
        (nameof(DevLead), nameof(DevLead.Plan)) => DevLead.Plan,
        (nameof(Developer), nameof(Developer.Implement)) => Developer.Implement,
        (nameof(Developer), nameof(Developer.Improve)) => Developer.Improve,
        _ => throw new ArgumentException($"Unable to find {skillName}.{functionName}")
    };
}

public interface IFunction
{
    string Name { get; }
    string Description { get; }
    string PluginName { get; }
    string DefaultValue { get; }
    string[] Parameters { get; }
}
