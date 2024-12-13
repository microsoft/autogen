// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandle.cs
namespace Microsoft.AutoGen.Core;
public interface IHandle
{
    Task HandleObject(object item);
}

public interface IHandle<T> : IHandle
{
    Task Handle(T item);
}
