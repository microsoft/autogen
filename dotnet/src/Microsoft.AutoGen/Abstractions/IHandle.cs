namespace Microsoft.AutoGen.Abstractions;

public interface IHandle
{
    Task Handle(object item);
}

public interface IHandle<T> : IHandle
{
    Task Handle(T item);
}
