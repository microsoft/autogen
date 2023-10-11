using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.SkillDefinition;

namespace MS.AI.DevTeam;

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
        // (nameof(CodeExplainer), nameof(CodeExplainer.Explain)) => CodeExplainer.Explain,
        (nameof(Dev), nameof(Dev.Implement)) => Dev.Implement,
        // (nameof(Developer), nameof(Developer.Improve)) => Developer.Improve,
        _ => throw new ArgumentException($"Unable to find {skillName}.{functionName}")
    };
}

public static class SemanticKernelExtensions
{
    public static ISKFunction LoadFunction(this IKernel kernel, string skill, string function)
   {
       var skillConfig = SemanticFunctionConfig.ForSkillAndFunction(skill, function);
       return kernel.CreateSemanticFunction(skillConfig.PromptTemplate, skillConfig.Name, skillConfig.SkillName,
                                                   skillConfig.Description, skillConfig.MaxTokens, skillConfig.Temperature,
                                                   skillConfig.TopP, skillConfig.PPenalty, skillConfig.FPenalty);
   }
}