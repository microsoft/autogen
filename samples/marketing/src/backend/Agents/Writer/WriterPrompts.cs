
namespace Marketing.Agents;
public static class WriterPrompts
{
    public static string Write = """
        You are a Marketing writer. 
        Write up to three paragraphs for a campain to promote what it is described bellow.
        Bellow are a series of inputs from the user that you can use to create the campain.
        If the input talks about twitter or images, dismiss it and return the same as before.
        Input: {{$input}}
        """;
}