# Installation

Install via `.NET cli`

```sh
dotnet add package Microsoft.AutoGen.Contracts --version 0.4.0-dev.1
dotnet add package Microsoft.AutoGen.Core --version 0.4.0-dev.1
```

Or, install via `Package Manager`

```pwsh
PM> NuGet\Install-Package Microsoft.AutoGen.Contracts -Version 0.4.0-dev.1
PM> NuGet\Install-Package Microsoft.AutoGen.Core -Version 0.4.0-dev.1
```

Or, add via `<PackageReference>`

```xml
<PackageReference Include="Microsoft.AutoGen.Contracts" Version="0.4.0-dev.1" />
<PackageReference Include="Microsoft.AutoGen.Core" Version="0.4.0-dev.1" />
```

# Additional Packages

The *Core* and *Contracts* packages will give you what you need for writing and running agents using the Core API within a single process. 

- *Microsoft.AutoGen.AgentChat* - An implementation of the AgentChat package for building chat-centric agent orchestration on top of the Core SDK
- *Microsoft.AutoGen.Agents* - a package that has a small number of default agents you can use.

```sh
dotnet add package Microsoft.AutoGen.AgentChat --version 0.4.0-dev.1
dotnet add package Microsoft.AutoGen.Agents --version 0.4.0-dev.1
```

## Extension Packages

Extensions to support closely related projects:

- *Microsoft.AutoGen.Extensions.Aspire* - Extensions for .NET Aspire integration
- *Microsoft.AutoGen.Extensions.MEAI* - Extensions for Microsoft.Extensions.AI integration
- *Microsoft.AutoGen.Extensions.SemanticKernel* - Extensions for Semantic Kernel integration

```sh
dotnet add package Microsoft.AutoGen.Extensions.Aspire --version 0.4.0-dev.1
dotnet add package Microsoft.AutoGen.Extensions.MEAI --version 0.4.0-dev.1
dotnet add package Microsoft.AutoGen.Extensions.SemanticKernel --version 0.4.0-dev.1
```

## Distributed System Packages

To enable running a system with agents in different processes that allows for x-language communication between python and .NET agents, there are additional packages:

- *Microsoft.AutoGen.Core.Grpc* - the .NET client runtime for agents in a distributed system. It has the same API as *Microsoft.AutoGen.Core*. 
- *Microsoft.AutoGen.RuntimeGateway.Grpc* - the .NET server side of the distributed system that allows you to run multiple gateways to manage fleets of agents and enables x-language interoperability.
- *Microsoft.AutoGen.AgentHost* - A .NET Aspire project that hosts the Grpc Service

```sh
dotnet add package Microsoft.AutoGen.Core.Grpc --version 0.4.0-dev.1
dotnet add package Microsoft.AutoGen.RuntimeGateway.Grpc --version 0.4.0-dev.1
dotnet add package Microsoft.AutoGen.AgentHost --version 0.4.0-dev.1
```