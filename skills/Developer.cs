
namespace skills;
public static class Developer {
    public static SemanticFunctionConfig Implement = new SemanticFunctionConfig
    {
        PromptTemplate = """
        You are a Developer for an application. 
        Please output the code required to accomplish the task assigned to you below and wrap it in a bash script that creates the files.
        Do not use any IDE commands and do not build and run the code.
        Make specific choices about implementation. Do not offer a range of options.
        Use comments in the code to describe the intent. Do not include other text other than code and code comments.
        Input: {{$input}}
        """,
        Name = nameof(Implement),
        SkillName = nameof(Developer),
        Description = "From a description of a coding task out put the code or scripts necessary to complete the task.",
        MaxTokens = 4096,
        Temperature = 0.0,
        TopP = 0.0,
        PPenalty = 0.0,
        FPenalty = 0.0
    };
}
