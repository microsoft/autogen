namespace Microsoft.AutoGen.Abstractions;

public interface IHandle<T>
{
    Task Handle(T item);
}
