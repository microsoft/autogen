// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandle.cs

namespace Microsoft.AutoGen.Core;

public interface IHandle<T>
{
    Task Handle(T item);
}
