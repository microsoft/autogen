// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentState.cs
using Google.Protobuf;
using Microsoft.AutoGen.Protobuf;
namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;
public class AgentState
{
    public required AgentId AgentId { get; set; }
    public string ETag { get; set; } = Guid.NewGuid().ToString();
    public object? Data { get; set; }
    public string? TextData { get; set; }
    public ByteString? BinaryData { get; set; }
    public Google.Protobuf.WellKnownTypes.Any? ProtoData { get; set; }
}