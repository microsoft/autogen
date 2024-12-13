// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandle.cs

// Copyright (c) Microsoft Corporation. All rights reserved.
// IHandle.cs

<<<<<<<< HEAD:dotnet / src / Microsoft.AutoGen / Agents / IHandle.cs
namespace Microsoft.AutoGen.Agents;
========
namespace Microsoft.AutoGen.Contracts;
>>>>>>>> main:dotnet/src/Microsoft.AutoGen/Contracts/IHandle.cs

public interface IHandle
{
    Task HandleObject(object item);
}

public interface IHandle<T> : IHandle
{
    Task Handle(T item);
}
