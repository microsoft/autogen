namespace skills;
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
}