### Install AutoGen

To use `AutoGen` and its related packages, simply add the following packages to your `.csproj` file:

```xml
<ItemGroup>
    <PackageReference Include="AutoGen" />

    <!-- Optional: This package carries a source generator that adds support for type-safe function definition generation. -->
    <!-- For more information, please check out AutoGen.SourceGenerator README -->
    <PackageReference Include="AutoGen.SourceGenerator" />

    <!-- Optional: This packages carries dotnet interactive support to execute dotnet code snippet -->
    <PackageReference Include="AutoGen.DotnetInteractive" />
</ItemGroup>
```

### Consume nightly build feed

You can also consume the nightly build AutoGen packages from the following feed:

> https://devdiv.pkgs.visualstudio.com/DevDiv/_packaging/AutoGen/nuget/v3/index.json
