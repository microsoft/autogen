# Installation

## Add via `<ProjectReference>`

```
  <ProjectReference Include="<path>/<to>/Contracts/Microsoft.AutoGen.Contracts.csproj" />
  <ProjectReference Include="<path>/<to>/Core/Microsoft.AutoGen.Core.csproj" />
```

<!-- (TODO: Move to bottom) -->

## These will only work after we release the package:

## Install via `.NET cli`

```
> dotnet add package Microsoft.AutoGen.Contracts --version 0.4.0
> dotnet add package Microsoft.AutoGen.Core --version 0.4.0
```

## Install via `Package Manager`

```
PM> NuGet\Install-Package Microsoft.AutoGen.Contracts -Version 0.4.0
PM> NuGet\Install-Package Microsoft.AutoGen.Core -Version 0.4.0
```

## Add via `<PackageReference>`

```
  <PackageReference Include="Microsoft.AutoGen.Contracts" Version="0.2.1" />
  <PackageReference Include="Microsoft.AutoGen.Core" Version="0.2.1" />
```
