FROM mcr.microsoft.com/dotnet/aspnet:7.0 AS base
WORKDIR /app
EXPOSE 5274
EXPOSE 11111
EXPOSE 30000

ENV ASPNETCORE_URLS=http://+:5274

FROM mcr.microsoft.com/dotnet/sdk:7.0 AS build
ARG configuration=Release
COPY . .
RUN dotnet restore "src/apps/gh-flow/gh-flow.csproj"
WORKDIR "/src/apps/gh-flow"
RUN dotnet build "gh-flow.csproj" -c $configuration -o /app/build

FROM build AS publish
ARG configuration=Release
RUN dotnet publish "gh-flow.csproj" -c $configuration -o /app/publish

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "gh-flow.dll"]