namespace Microsoft.AI.DevTeam.Skills;
public static class Chat
{
   public static SemanticFunctionConfig ChatCompletion = new SemanticFunctionConfig
   {
       PromptTemplate = """
        You are a helpful assistant. Please complete the prompt as instructed in the Input. 
        Provide as many references and links as needed to support the accuracy of your answer.
        Input: {{$input}}
       """,
       Name = nameof(ChatCompletion),
       SkillName = nameof(Chat),
       Description = "Use the Model as a Chatbot.",
        MaxTokens = 6500,
        Temperature = 0.0,
        TopP = 0.0,
        PPenalty = 0.0,
        FPenalty = 0.0
   };
  
}
