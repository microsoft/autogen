namespace Microsoft.AutoGen.Agents.Abstractions;

public interface IAgent
{
    Task HandleEvent(Event item);
    Task PublishEvent(Event item);
}
