namespace Microsoft.AI.DevTeam.Skills;
public static class PM
{
   public static SemanticFunctionConfig BootstrapProject = new SemanticFunctionConfig
   {
       PromptTemplate = """
       Please write a bash script with the commands that would be required to generate applications as described in the following input.
        You may add comments to the script and the generated output but do not add any other text except the bash script. 
        You may include commands to build the applications but do not run them. 
        Do not include any git commands.
        Input: {{$input}}
        {{$wafContext}}
       """,
       Name = nameof(BootstrapProject),
       SkillName = nameof(PM),
       Description = "Bootstrap a new project",
        MaxTokens = 6500,
        Temperature = 0.0,
        TopP = 0.0,
        PPenalty = 0.0,
        FPenalty = 0.0
   };
   public static SemanticFunctionConfig Readme = new SemanticFunctionConfig
   {
       PromptTemplate = """
       You are a program manager on a software development team. You are working on an app described below. 
        Based on the input below, and any dialog or other context, please output a raw README.MD markdown file documenting the main features of the app and the architecture or code organization. 
        Do not describe how to create the application. 
        Write the README as if it were documenting the features and architecture of the application. You may include instructions for how to run the application. 
        Input: {{$input}}
        {{$wafContext}}
       """,
       Name = nameof(Readme),
       SkillName = nameof(PM),
       Description = "From a simple description output a README.md file for a GitHub repository.",
        MaxTokens = 6500,
        Temperature = 0.0,
        TopP = 0.0,
        PPenalty = 0.0,
        FPenalty = 0.0
   };
}
