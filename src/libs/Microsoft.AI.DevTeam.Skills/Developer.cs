
namespace Microsoft.AI.DevTeam.Skills;
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

    public static SemanticFunctionConfig Explain = new SemanticFunctionConfig
    {
        PromptTemplate = """
        You are an experienced software developer, with strong experience in Azure and Microsoft technologies.
        Extract the key features and capabilities of the code file below, with the intent to build an understanding of an entire code repository.
        You can include references or documentation links in your explanation. Also where appropriate please output a list of keywords to describe the code or its capabilities.
        Example:
            Keywords: Azure, networking, security, authentication

        ===code===  
         {{$input}}
        ===end-code===
        Only include the points in a bullet point format and DON'T add anything outside of the bulleted list.
        Be short and concise. 
        If the code's purpose is not clear output an error:  
        Error: The model could not determine the purpose of the code.
        """,
        Name = nameof(Explain),
        SkillName = nameof(CodeExplainer),
        Description = "From a source file produce an explanation of what the code does",
        MaxTokens = 6500,
        Temperature = 0.0,
        TopP = 0.0,
        PPenalty = 0.0,
        FPenalty = 0.0
    };

    public static SemanticFunctionConfig ConsolidateUnderstanding = new SemanticFunctionConfig
    {
        PromptTemplate = """
        You are an experienced software developer, with strong experience in Azure and Microsoft technologies.
        You are trying to build an understanding of the codebase from code files. This is the current understanding of the project:
        ===current-understanding===
         {{$input}}
        ===end-current-understanding===
        and this is the new information that surfaced
        ===new-understanding===
         {{$newUnderstanding}}
        ===end-new-understanding===
        Your job is to update your current understanding with the new information.
        Only include the points in a bullet point format and DON'T add anything outside of the bulleted list.
        Be short and concise. 
        """,
        Name = nameof(Explain),
        SkillName = nameof(CodeExplainer),
        Description = "From a source file produce an explanation of what the code does",
        MaxTokens = 6500,
        Temperature = 0.0,
        TopP = 0.0,
        PPenalty = 0.0,
        FPenalty = 0.0
    };
}


