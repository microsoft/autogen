### Current version:

[![NuGet version](https://badge.fury.io/nu/AutoGen.Core.svg)](https://badge.fury.io/nu/AutoGen.Core)

AutoGen.Net provides the following packages, you can choose to install one or more of them based on your needs:

- `AutoGen`: The one-in-all package. This package has dependencies over `AutoGen.Core`, `AutoGen.OpenAI`, `AutoGen.LMStudio`, `AutoGen.SemanticKernel` and `AutoGen.SourceGenerator`.
- `AutoGen.Core`: The core package, this package provides the abstraction for message type, agent and group chat.
- `AutoGen.OpenAI`: This package provides the integration agents over openai models.
- `AutoGen.Mistral`: This package provides the integration agents for Mistral.AI models.
- `AutoGen.Ollama`: This package provides the integration agents for [Ollama](https://ollama.com/).
- `AutoGen.Anthropic`: This package provides the integration agents for [Anthropic](https://www.anthropic.com/api)
- `AutoGen.LMStudio`: This package provides the integration agents from LM Studio.
- `AutoGen.SemanticKernel`: This package provides the integration agents over semantic kernel.
- `AutoGen.Gemini`: This package provides the integration agents from [Google Gemini](https://gemini.google.com/).
- `AutoGen.AzureAIInference`: This package provides the integration agents for [Azure AI Inference](https://www.nuget.org/packages/Azure.AI.Inference).
- `AutoGen.SourceGenerator`: This package carries a source generator that adds support for type-safe function definition generation.
- `AutoGen.DotnetInteractive`: This packages carries dotnet interactive support to execute code snippets. The current supported language is C#, F#, powershell and python.

>[!Note]
> Help me choose
> - If you just want to install one package and enjoy the core features of AutoGen, choose `AutoGen`.
> - If you want to leverage AutoGen's abstraction only and want to avoid introducing any other dependencies, like `Azure.AI.OpenAI` or `Semantic Kernel`, choose `AutoGen.Core`. You will need to implement your own agent, but you can still use AutoGen core features like group chat, built-in message type, workflow and middleware.
>- If you want to use AutoGen with openai, choose `AutoGen.OpenAI`, similarly, choose `AutoGen.LMStudio` or `AutoGen.SemanticKernel` if you want to use agents from LM Studio or semantic kernel.
>- If you just want the type-safe source generation for function call and don't want any other features, which even include the AutoGen's abstraction, choose `AutoGen.SourceGenerator`.

Then, install the package using the following command:

```bash
dotnet add package AUTOGEN_PACKAGES
```

### Consume nightly build
To consume nightly build, you can add one of the following feeds to your `NuGet.config` or global nuget config:
- ![Static Badge](https://img.shields.io/badge/public-blue?style=flat) ![Static Badge](https://img.shields.io/badge/github-grey?style=flat): https://nuget.pkg.github.com/microsoft/index.json
- ![Static Badge](https://img.shields.io/badge/public-blue?style=flat) ![Static Badge](https://img.shields.io/badge/myget-grey?style=flat): https://www.myget.org/F/agentchat/api/v3/index.json
- ![Static Badge](https://img.shields.io/badge/internal-blue?style=flat) ![Static Badge](https://img.shields.io/badge/azure_devops-grey?style=flat) : https://devdiv.pkgs.visualstudio.com/DevDiv/_packaging/AutoGen/nuget/v3/index.json

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

Once you have added the feed, you can install the nightly-build package using the following command:
```bash
dotnet add package AUTOGEN_PACKAGES VERSION
```


