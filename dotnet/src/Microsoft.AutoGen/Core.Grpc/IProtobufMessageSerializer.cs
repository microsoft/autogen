// Copyright (c) Microsoft Corporation. All rights reserved.
// IProtobufMessageSerializer.cs

namespace Microsoft.AutoGen.Core.Grpc;

public interface IProtobufMessageSerializer
{
    Google.Protobuf.WellKnownTypes.Any Serialize(object input);
    object Deserialize(Google.Protobuf.WellKnownTypes.Any input);
}
