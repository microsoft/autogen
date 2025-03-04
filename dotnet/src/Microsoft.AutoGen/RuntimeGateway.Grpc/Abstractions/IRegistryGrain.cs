// Copyright (c) Microsoft Corporation. All rights reserved.
// IRegistryGrain.cs

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;

/// <summary>
/// Orleans specific interface, needed to mark the key
/// </summary>
[Alias("Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions.IRegistryGrain")]
public interface IRegistryGrain : IGatewayRegistry, IGrainWithIntegerKey
{ }
