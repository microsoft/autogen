// Copyright (c) Microsoft Corporation. All rights reserved.
// GraphicDesignerPrompts.cs

namespace Marketing.Agents;

public static class GraphicDesignerPrompts
{
    public const string GenerateImage = """
        You are a Marketing community manager graphic designer. 
        Below is a campaign that you need to create an image for.
        Create an image of maximum 500x500 pixels that could be used on social media as a marketing image.
        Only answer if the user is asking for an image to be created or if the user is asking for a new campaign.
        Input: {{$input}}
        """;
}
