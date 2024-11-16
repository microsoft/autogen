// Copyright (c) Microsoft Corporation. All rights reserved.
// PMPrompts.cs

namespace DevTeam.Agents;
public static class PMSkills
{
    public const string BootstrapProject = """
       Please write a bash script with the commands that would be required to generate applications as described in the following input.
        You may add comments to the script and the generated output but do not add any other text except the bash script. 
        You may include commands to build the applications but do not run them. 
        Do not include any git commands.
        Input: {{$input}}
        {{$waf}}
       """;
    public const string Readme = """
       You are a program manager on a software development team. You are working on an app described below. 
        Based on the input below, and any dialog or other context, please output a raw README.MD markdown file documenting the main features of the app and the architecture or code organization. 
        Do not describe how to create the application. 
        Write the README as if it were documenting the features and architecture of the application. You may include instructions for how to run the application. 
        Input: {{$input}}
        {{$waf}}
       """;

    public const string Explain = """
        You are a Product Manager. 
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
