// Copyright (c) Microsoft Corporation. All rights reserved.
// RegisterAgentTypeRequestSurrogate.cs

using Google.Protobuf.Collections;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct RegisterAgentTypeRequestSurrogate
{
    [Id(0)]
    public string RequestId;
    [Id(1)]
    public string Type;
    [Id(2)]
    public RepeatedField<string> Events;
    [Id(3)]
    public RepeatedField<string> Topics;
}

[RegisterConverter]
public sealed class RegisterAgentTypeRequestSurrogateConverter :
    IConverter<RegisterAgentTypeRequest, RegisterAgentTypeRequestSurrogate>
{
    public RegisterAgentTypeRequest ConvertFromSurrogate(
        in RegisterAgentTypeRequestSurrogate surrogate)
    {
        var request = new RegisterAgentTypeRequest()
        {
            Type = surrogate.Type
        };
        /* future
        request.Events.Add(surrogate.Events);
        request.Topics.Add(surrogate.Topics);*/
        return request;
    }

    public RegisterAgentTypeRequestSurrogate ConvertToSurrogate(
        in RegisterAgentTypeRequest value) =>
        new RegisterAgentTypeRequestSurrogate
        {
            Type = value.Type,
            /* future
            Events = value.Events,
            Topics = value.Topics */
        };
}
