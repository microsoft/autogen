// Copyright (c) Microsoft Corporation. All rights reserved.
// GetSubscriptionsRequest.cs

using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Orleans.Surrogates;

[GenerateSerializer]
public struct GetSubscriptionsRequestSurrogate
{
    [Id(0)]
    public string RequestId;
    [Id(1)]
    public Subscription Subscription;
}

[RegisterConverter]
public sealed class GetSubscriptionsRequestSurrogateConverter :
    IConverter<GetSubscriptionsRequest, GetSubscriptionsRequestSurrogate>
{
    public GetSubscriptionsRequest ConvertFromSurrogate(
        in GetSubscriptionsRequestSurrogate surrogate)
    {
        var request = new GetSubscriptionsRequest()
        {
        };
        return request;
    }

    public GetSubscriptionsRequestSurrogate ConvertToSurrogate(
        in GetSubscriptionsRequest value) =>
        new GetSubscriptionsRequestSurrogate
        {
        };
}
