// Copyright (c) Microsoft Corporation. All rights reserved.
// Constants.cs

namespace Microsoft.AutoGen.Core.Grpc;

public static class Constants
{
    public const string DATA_CONTENT_TYPE_PROTOBUF_VALUE = "application/x-protobuf";
    public const string DATA_CONTENT_TYPE_JSON_VALUE = "application/json";
    public const string DATA_CONTENT_TYPE_TEXT_VALUE = "text/plain";

    public const string DATA_CONTENT_TYPE_ATTR = "datacontenttype";
    public const string DATA_SCHEMA_ATTR = "dataschema";
    public const string AGENT_SENDER_TYPE_ATTR = "agagentsendertype";
    public const string AGENT_SENDER_KEY_ATTR = "agagentsenderkey";

    public const string MESSAGE_KIND_ATTR = "agmsgkind";
    public const string MESSAGE_KIND_VALUE_PUBLISH = "publish";
    public const string MESSAGE_KIND_VALUE_RPC_REQUEST = "rpc_request";
    public const string MESSAGE_KIND_VALUE_RPC_RESPONSE = "rpc_response";
}
