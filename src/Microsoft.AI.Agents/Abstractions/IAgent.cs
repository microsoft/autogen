namespace Microsoft.AI.Agents.Abstractions;

public interface IAgent
{
    Task HandleEvent(Event item);
    Task PublishEvent(string ns, string id, Event item);
}