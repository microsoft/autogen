namespace Microsoft.AutoGen.Agents.Abstractions;

public interface IHandle<T>
{
    Task Handle(T item);
}