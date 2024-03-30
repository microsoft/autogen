namespace Microsoft.SKDevTeam;
public static class DevLead {
    public static SemanticFunctionConfig Plan = new SemanticFunctionConfig
    {
        PromptTemplate = """
        You are a Dev Lead for an application team, building the application described below. 
        Please break down the steps and modules required to develop the complete application, describe each step in detail.
        Make prescriptive architecture, language, and frameowrk choices, do not provide a range of choices. 
        For each step or module then break down the steps or subtasks required to complete that step or module.
        For each subtask write an LLM prompt that would be used to tell a model to write the coee that will accomplish that subtask.  If the subtask involves taking action/running commands tell the model to write the script that will run those commands. 
        In each LLM prompt restrict the model from outputting other text that is not in the form of code or code comments. 
        Please output a JSON array data structure, in the precise schema shown below, with a list of steps and a description of each step, and the steps or subtasks that each requires, and the LLM prompts for each subtask. 
        Example: 
            {
                "steps": [
                    {
                        "step": "1",
                        "description": "This is the first step",
                        "subtasks": [
                            {
                            "subtask": "Subtask 1",
                                "description": "This is the first subtask",
                                "prompt": "Write the code to do the first subtask"
                            },
                            {
                                "subtask": "Subtask 2",
                                "description": "This is the second subtask",
                                "prompt": "Write the code to do the second subtask"
                            }
                        ]
                    }
                ]
            }
        Do not output any other text. 
        Input: {{$input}}
        {{$wafContext}}
        """,
        Name = nameof(Plan),
        SkillName = nameof(DevLead),
        Description = "From a simple description of an application output a development plan for building the application.",
        MaxTokens = 6500,
        Temperature = 0.0,
        TopP = 0.0,
        PPenalty = 0.0,
        FPenalty = 0.0
    };
}