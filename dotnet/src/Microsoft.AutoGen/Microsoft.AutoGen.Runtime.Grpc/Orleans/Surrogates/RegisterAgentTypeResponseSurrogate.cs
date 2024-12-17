// Copyright (c) Microsoft Corporation. All rights reserved.
// RegisterAgentTypeResponseSurrogate.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Orleans.Surrogates;

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
        new RegisterAgentTypeResponse
        {
            RequestId = surrogate.RequestId,
            Success = surrogate.Success,
            Error = surrogate.Error
        };

    public RegisterAgentTypeResponseSurrogate ConvertToSurrogate(
        in RegisterAgentTypeResponse value) =>
        new RegisterAgentTypeResponseSurrogate
        {
            RequestId = value.RequestId,
            Success = value.Success,
            Error = value.Error
        };
}

