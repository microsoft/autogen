# Defining Message Types

Messages are currently required to be Protocol Buffers. To define them, it is necessary to include the Protocol Buffers compiler, through the `Grpc.Tools` package. In your `.csproj` file, add/edit:

```xml
    <PackageReference Include="Grpc.Tools" PrivateAssets="All" />
```

Then create an include a `.proto` file in the project:

```xml
<ItemGroup>
  <Protobuf Include="messages.proto" GrpcServices="Client;Server" Link="messages.proto" />
</ItemGroup>
```

Then define your messages as specified in the [Protocol Buffers Language Guide](https://protobuf.dev/programming-guides/proto3/)

```proto
syntax = "proto3";

package HelloAgents;

option csharp_namespace = "AgentsProtocol";

message TextMessage {
    string Source = 1;
    string Content = 2;
}
```