// Copyright (c) Microsoft Corporation. All rights reserved.
// RemoveSubscriptionRequest.cs
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct RemoveSubscriptionRequestSurrogate
{
    [Id(0)]
    public string Id;
}

[RegisterConverter]
public sealed class RemoveSubscriptionRequestConverter :
    IConverter<RemoveSubscriptionRequest, RemoveSubscriptionRequestSurrogate>
{
    public RemoveSubscriptionRequest ConvertFromSurrogate(
        in RemoveSubscriptionRequestSurrogate surrogate)
    {
        var request = new RemoveSubscriptionRequest()
        {
            Id = surrogate.Id
        };
        return request;
    }

    public RemoveSubscriptionRequestSurrogate ConvertToSurrogate(
        in RemoveSubscriptionRequest value) =>
        new RemoveSubscriptionRequestSurrogate
        {
            Id = value.Id
        };
}
