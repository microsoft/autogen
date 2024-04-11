FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
WORKDIR /app
EXPOSE 5274
EXPOSE 11111
EXPOSE 30000

ENV ASPNETCORE_URLS=http://+:5274

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
ARG configuration=Release
COPY . .
RUN dotnet restore "samples/gh-flow/src/Microsoft.AI.DevTeam/Microsoft.AI.DevTeam.csproj"
WORKDIR "samples/gh-flow/src/Microsoft.AI.DevTeam"
RUN dotnet build "Microsoft.AI.DevTeam.csproj" -c $configuration -o /app/build

FROM build AS publish
ARG configuration=Release
RUN dotnet publish "Microsoft.AI.DevTeam.csproj" -c $configuration -o /app/publish

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "Microsoft.AI.DevTeam.dll"]