
namespace Microsoft.AI.DevTeam.Skills;
public static class CodeExplainer {
    public static SemanticFunctionConfig Explain = new SemanticFunctionConfig
    {
        PromptTemplate = """
        You are a Software Developer. 
        Please explain the code that is in the input below. You can include references or documentation links in your explanation. 
        Also where appropriate please output a list of keywords to describe the code or its capabilities.
        example:
        Keywords: Azure, networking, security, authentication

        If the code's purpose is not clear output an error:
        Error: The model could not determine the purpose of the code.
        
        --
        Input: {{$input}}
        """,
        Name = nameof(Explain),
        SkillName = nameof(CodeExplainer),
        Description = "From a description of a coding task out put the code or scripts necessary to complete the task.",
        MaxTokens = 6500,
        Temperature = 0.0,
        TopP = 0.0,
        PPenalty = 0.0,
        FPenalty = 0.0
    };

}
