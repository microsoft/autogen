// Copyright (c) Microsoft. All rights reserved.

namespace Microsoft.AutoGen.Abstractions;

public interface IHandle<T>
{
    Task Handle(T item);
}
