### Install AutoGen

Firstly, select one of the following package feed to consume AutoGen packages:
> [!NOTE]
> There's only nightly-build feed available for now, the stable-version will be published to nuget once it's available

- ![Static Badge](https://img.shields.io/badge/public-blue?style=flat) ![Static Badge](https://img.shields.io/badge/nightly-yellow?style=flat) ![Static Badge](https://img.shields.io/badge/github-grey?style=flat): https://nuget.pkg.github.com/microsoft/index.json
- ![Static Badge](https://img.shields.io/badge/public-blue?style=flat) ![Static Badge](https://img.shields.io/badge/nightly-yellow?style=flat) ![Static Badge](https://img.shields.io/badge/myget-grey?style=flat): https://www.myget.org/F/agentchat/api/v3/index.json
- ![Static Badge](https://img.shields.io/badge/internal-blue?style=flat) ![Static Badge](https://img.shields.io/badge/nightly-yellow?style=flat) ![Static Badge](https://img.shields.io/badge/azure_devops-grey?style=flat) : https://devdiv.pkgs.visualstudio.com/DevDiv/_packaging/AutoGen/nuget/v3/index.json

Then, add the AutoGen feed to your project. You can do this by either adding a local `NuGet.config`(recommended) or adding the feed to your global `NuGet.config` file.

To add a local `NuGet.config`, create a file named `NuGet.config` in the root of your project and add the following content:
```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <!-- dotnet-tools contains Microsoft.DotNet.Interactive.VisualStudio package, which is used by AutoGen.DotnetInteractive -->
    <add key="dotnet-tools" value="https://pkgs.dev.azure.com/dnceng/public/_packaging/dotnet-tools/nuget/v3/index.json" />
    <add key="AutoGen" value="$(FEED_URL)" /> <!-- replace $(FEED_URL) with the feed url -->
    <!-- other feeds -->
  </packageSources>
  <disabledPackageSources />
</configuration>
```

To add the feed to your global nuget config. You can do this by running the following command in your terminal:
```bash
dotnet nuget add source FEED_URL --name AutoGen

# dotnet-tools contains Microsoft.DotNet.Interactive.VisualStudio package, which is used by AutoGen.DotnetInteractive
dotnet nuget add source https://pkgs.dev.azure.com/dnceng/public/_packaging/dotnet-tools/nuget/v3/index.json --name dotnet-tools
```

Once you finishing adding AutoGen feed, you can consume AutoGen packages in your project file by adding the following to your project file:
```xml
<ItemGroup>
    <PackageReference Include="AutoGen" Version="AUTOGEN_VERSION" /> <!-- replace AUTOGEN_VERSION with the version you want to use -->

    <!-- Optional: This package carries a source generator that adds support for type-safe function definition generation. -->
    <!-- For more information, please check out AutoGen.SourceGenerator README -->
    <PackageReference Include="AutoGen.SourceGenerator" Version="AUTOGEN_VERSION" />

    <!-- Optional: This packages carries dotnet interactive support to execute dotnet code snippet -->
    <PackageReference Include="AutoGen.DotnetInteractive" Version="AUTOGEN_VERSION" />
</ItemGroup>
```

### Package overview
AutoGen.Net provides the following packages, you can choose to install one or more of them based on your needs:

- `AutoGen`: The one-in-all package, which includes all the core features of AutoGen like `AssistantAgent` and `AutoGen.SourceGenerator`, plus intergration over popular platforms like openai, semantic kernel and LM Studio.
- `AutoGen.Core`: The core package, this package provides the abstraction for message type, agent and group chat.
- `AutoGen.OpenAI`: This package provides the integration agents over openai models.
- `AutoGen.LMStudio`: This package provides the integration agents from LM Studio.
- `AutoGen.SemanticKernel`: This package provides the integration agents over semantic kernel.
- `AutoGen.SourceGenerator`: This package carries a source generator that adds support for type-safe function definition generation.
- `AutoGen.DotnetInteractive`: This packages carries dotnet interactive support to execute dotnet code snippet.

#### Help me choose
- If you just want to install one package and enjoy the core features of AutoGen, choose `AutoGen`.
- If you want to leverage AutoGen's abstraction only and want to avoid introducing any other dependencies, like `Azure.AI.OpenAI` or `Semantic Kernel`, choose `AutoGen.Core`. You will need to implement your own agent, but you can still use AutoGen core features like group chat, built-in message type, workflow and middleware.
- If you want to use AutoGen with openai, choose `AutoGen.OpenAI`, similarly, choose `AutoGen.LMStudio` or `AutoGen.SemanticKernel` if you want to use agents from LM Studio or semantic kernel.
- If you just want the type-safe source generation for function call and don't want any other features, which even include the AutoGen's abstraction, choose `AutoGen.SourceGenerator`.
