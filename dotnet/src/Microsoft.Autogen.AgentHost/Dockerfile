# This stage is used when running from VS in fast mode (Default for Debug configuration)
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
USER $APP_UID
WORKDIR /app
EXPOSE 8080
EXPOSE 8081

# This stage is used to build the service project
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
ARG BUILD_CONFIGURATION=Release
WORKDIR /src
COPY ["dotnet/Directory.Packages.props", "."]
COPY ["dotnet/Directory.Build.props", "."]
COPY ["dotnet/Directory.Build.targets", "."]
COPY ["dotnet/NuGet.config", "."]
COPY ["dotnet/src/Microsoft.AutoGen/Microsoft.Autogen.AgentHost/Microsoft.Autogen.AgentHost.csproj", "src/Microsoft.AutoGen/Microsoft.Autogen.AgentHost/"]
COPY ["dotnet/src/Microsoft.AutoGen/Microsoft.AutoGen.Runtime.Grpc/Microsoft.AutoGen.Runtime.Grpc.csproj", "src/Microsoft.AutoGen/Microsoft.AutoGen.Runtime.Grpc/"]
COPY ["dotnet/src/Microsoft.AutoGen/Microsoft.AutoGen.Contracts/Microsoft.AutoGen.Contracts.csproj", "src/Microsoft.AutoGen/Microsoft.AutoGen.Contracts/"]
RUN dotnet restore "./src/Microsoft.AutoGen/Microsoft.Autogen.AgentHost/Microsoft.Autogen.AgentHost.csproj"
COPY . .
WORKDIR "/src/src/Microsoft.AutoGen/Microsoft.Autogen.AgentHost"
RUN dotnet build "./Microsoft.Autogen.AgentHost.csproj" -c $BUILD_CONFIGURATION -o /app/build

# This stage is used to publish the service project to be copied to the final stage
FROM build AS publish
ARG BUILD_CONFIGURATION=Release
RUN dotnet publish "./Microsoft.Autogen.AgentHost.csproj" -c $BUILD_CONFIGURATION -o /app/publish /p:UseAppHost=false

# This stage is used in production or when running from VS in regular mode (Default when not using the Debug configuration)
FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "Microsoft.Autogen.AgentHost.dll"]
