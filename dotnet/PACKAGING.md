# Packaging AutoGen.NET

This document describes the steps to pack the `AutoGen.NET` project.

## Prerequisites

- .NET SDK

## Create Package

1. **Restore and Build the Project**
```bash
dotnet restore
dotnet build --configuration Release --no-restore
```


2. **Create the NuGet Package**
```bash
dotnet pack --configuration Release --no-build
```

This will generate both the `.nupkg` file and the `.snupkg` file in the `./artifacts/package/release` directory.

For more details, refer to the [official .NET documentation](https://docs.microsoft.com/en-us/dotnet/core/tools/dotnet-pack).

## Add new project to package list.
By default, when you add a new project to `AutoGen.sln`, it will not be included in the package list. To include the new project in the package, you need to add the following line to the new project's `.csproj` file

e.g.

```xml
<Import Project="$(RepoRoot)/nuget/nuget-package.props" />
```

The `nuget-packages.props` enables `IsPackable` to `true` for the project, it also sets nenecessary metadata for the package.

For more details, refer to the [NuGet folder](./nuget/README.md).

## Package versioning
The version of the package is defined by `VersionPrefix` and `VersionPrefixForAutoGen0_2` in [MetaInfo.props](./eng/MetaInfo.props). If the name of your project starts with `AutoGen.`, the version will be set to `VersionPrefixForAutoGen0_2`, otherwise it will be set to `VersionPrefix`.
