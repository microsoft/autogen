// Copyright (c) Microsoft Corporation. All rights reserved.
// IProtoMessageSerializer.cs

namespace Microsoft.AutoGen.Core.Grpc;

public interface IProtoMessageSerializer
{
    Google.Protobuf.WellKnownTypes.Any Serialize(object input);
    object Deserialize(Google.Protobuf.WellKnownTypes.Any input);
}