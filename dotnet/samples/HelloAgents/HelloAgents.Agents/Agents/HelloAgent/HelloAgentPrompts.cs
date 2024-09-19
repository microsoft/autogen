namespace HelloAgents.Agents;
public static class HelloSkills
{
    public const string Greeting = """
        You are a Hello Agent. 
        Please output a greeting message that you would like to send to the user.
        Try to include a pun in your greeting.
        You may incorporate the user's input into your reply if you wish.
        Input: {{$input}}
        """;

    public const string Farewell = """
        You are a Hello Agent. 
        Please output a farewell message that you would like to send to the user.
        Try to include a quote related to goodbyes. 
        You may incorporate the user's input into your reply if you wish.
        Input: {{$input}}
        """;
}