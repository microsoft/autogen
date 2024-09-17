namespace Microsoft.AI.Agents.Abstractions;

public interface IHandle<T>
{
    Task Handle(T item);
}