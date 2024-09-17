namespace Microsoft.AI.Agents.Abstractions;

public interface IAgent
{
    Task HandleEvent(Event item);
    Task PublishEvent(Event item);
}
