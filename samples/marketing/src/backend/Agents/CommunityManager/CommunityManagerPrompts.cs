namespace Marketing.Agents;

public static class CommunityManagerPrompts
{
    public static string WritePost = """
        You are a Marketing community manager writer. 
        Write a tweet to promote what it is described bellow.
        The tweet cannot be longer than 280 characters
        Input: {{$input}}
        """;
}