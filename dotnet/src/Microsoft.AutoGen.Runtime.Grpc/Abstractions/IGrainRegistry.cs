// Copyright (c) Microsoft Corporation. All rights reserved.
// IGrainRegistry.cs

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

/// <summary>
/// Orleans specific interface, needed to mark the key
/// </summary>
public interface IGrainRegistry : IRegistry, IGrainWithIntegerKey
{ }
