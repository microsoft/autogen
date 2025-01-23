// Copyright (c) Microsoft Corporation. All rights reserved.
// IRegistryGrain.cs

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

/// <summary>
/// Orleans specific interface, needed to mark the key
/// </summary>
[Alias("Microsoft.AutoGen.Runtime.Grpc.Abstractions.IRegistryGrain")]
public interface IRegistryGrain : IRegistry, IGrainWithIntegerKey
{ }
