### Install AutoGen

First, select an AutoGen feed from the following to consume.

> ![NOTE]
> The nightly build feed is the only available feed for now and it's for Microsoft internal use only. We will provide a public feed on github package soon.
- Nightly Build feed(Internal only): https://devdiv.pkgs.visualstudio.com/DevDiv/_packaging/AutoGen/nuget/v3/index.json

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