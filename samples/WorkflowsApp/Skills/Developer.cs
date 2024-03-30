namespace Microsoft.SKDevTeam;
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
        {{$wafContext}}
        """,
        Name = nameof(Implement),
        SkillName = nameof(Developer),
        Description = "From a description of a coding task out put the code or scripts necessary to complete the task.",
        MaxTokens = 6500,
        Temperature = 0.0,
        TopP = 0.0,
        PPenalty = 0.0,
        FPenalty = 0.0
    };

    public static SemanticFunctionConfig Improve = new SemanticFunctionConfig
    {
        PromptTemplate = """
        You are a Developer for an application. Your job is to imrove the code that you are given in the input below. 
        Please output a new version of code that fixes any problems with this version. 
        If there is an error message in the input you should fix that error in the code. 
        Wrap the code output up in a bash script that creates the necessary files by overwriting any previous files. 
        Do not use any IDE commands and do not build and run the code.
        Make specific choices about implementation. Do not offer a range of options.
        Use comments in the code to describe the intent. Do not include other text other than code and code comments.
        Input: {{$input}}
        {{$wafContext}}
        """,
        Name = nameof(Improve),
        SkillName = nameof(Developer),
        Description = "From a description of a coding task out put the code or scripts necessary to complete the task.",
        MaxTokens = 6500,
        Temperature = 0.0,
        TopP = 0.0,
        PPenalty = 0.0,
        FPenalty = 0.0
    };
}