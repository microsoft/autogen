// Copyright (c) Microsoft Corporation. All rights reserved.
// RegisterAgentTypeRequestSurrogate.cs

using Google.Protobuf.Collections;
using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Runtime.Grpc.Tests.Helpers.Orleans.Surrogates;

[GenerateSerializer]
public struct RegisterAgentTypeRequestSurrogate
{
    [Id(0)]
    public string RequestId;
    [Id(1)]
    public string Type;
    [Id(2)]
    public RepeatedField<string> Events;
}

[RegisterConverter]
public sealed class RegisterAgentTypeRequestSurrogateConverter :
    IConverter<RegisterAgentTypeRequest, RegisterAgentTypeRequestSurrogate>
{
    public RegisterAgentTypeRequest ConvertFromSurrogate(
        in RegisterAgentTypeRequestSurrogate surrogate) =>
        new RegisterAgentTypeRequest()
        {
            RequestId = surrogate.RequestId,
            Type = surrogate.Type,
            // TODO : Map Events
        };

    public RegisterAgentTypeRequestSurrogate ConvertToSurrogate(
        in RegisterAgentTypeRequest value) =>
        new RegisterAgentTypeRequestSurrogate
        {
            RequestId = value.RequestId,
            Type = value.Type,
            Events = value.Events
        };
}
