// Copyright (c) Microsoft Corporation. All rights reserved.
// RegisterAgentTypeResponseSurrogate.cs

using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct RegisterAgentTypeResponseSurrogate
{
    [Id(0)]
    public string RequestId;
    [Id(1)]
    public bool Success;
    [Id(2)]
    public string Error;
}

[RegisterConverter]
public sealed class RegisterAgentTypeResponseSurrogateConverter :
    IConverter<RegisterAgentTypeResponse, RegisterAgentTypeResponseSurrogate>
{
    public RegisterAgentTypeResponse ConvertFromSurrogate(
        in RegisterAgentTypeResponseSurrogate surrogate) =>
        new RegisterAgentTypeResponse { };

    public RegisterAgentTypeResponseSurrogate ConvertToSurrogate(
        in RegisterAgentTypeResponse value) =>
        new RegisterAgentTypeResponseSurrogate { };
}

