// Copyright (c) Microsoft Corporation. All rights reserved.
// AuditorPrompts.cs

namespace Marketing.Agents;

public static class AuditorPrompts
{
    public const string AuditText = """
        You are an Auditor in a Marketing team.
        Audit the text below and make sure we do not give discounts larger than 50%.
        If the text talks about a larger than 50% discount, reply with a message to the user saying that the discount is too large, and by company policy we are not allowed.
        If the message says who wrote it, add that information in the response as well.
        In any other case, reply with NOTFORME
        ---
        Input: {{$input}}
        ---
        """;
}
