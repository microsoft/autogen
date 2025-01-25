// Copyright (c) Microsoft Corporation. All rights reserved.
// DeveloperLeadPrompts.cs

namespace DevTeam.Backend.Agents.DeveloperLead;
public static class DevLeadSkills
{
    public const string Plan = """
        You are a Dev Lead for an application team, building the application described below. 
        Please break down the steps and modules required to develop the complete application, describe each step in detail.
        Make prescriptive architecture, language, and framework choices, do not provide a range of choices. 
        For each step or module then break down the steps or subtasks required to complete that step or module.
        For each subtask write an LLM prompt that would be used to tell a model to write the code that will accomplish that subtask.  If the subtask involves taking action/running commands tell the model to write the script that will run those commands. 
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
        Do not wrap the JSON in any other text, output the JSON format described above, making sure it's a valid JSON.
        Input: {{$input}}
        {{$waf}}
        """;

    public const string Explain = """
        You are a Dev Lead. 
        Please explain the code that is in the input below. You can include references or documentation links in your explanation. 
        Also where appropriate please output a list of keywords to describe the code or its capabilities.
        example:
        Keywords: Azure, networking, security, authentication

        If the code's purpose is not clear output an error:
        Error: The model could not determine the purpose of the code.
        
        --
        Input: {{$input}}
        """;
}
