FROM mcr.microsoft.com/dotnet/runtime:7.0 AS base
WORKDIR /app

FROM mcr.microsoft.com/dotnet/sdk:7.0 AS build
WORKDIR /src
COPY ["util/seed-memory/seed-memory.csproj", "util/seed-memory/"]
RUN dotnet restore "util/seed-memory/seed-memory.csproj"
COPY . .
WORKDIR "/src/util/seed-memory"
RUN dotnet build "seed-memory.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "seed-memory.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "seed-memory.dll"]
