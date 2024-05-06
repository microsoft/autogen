FROM mcr.microsoft.com/dotnet/aspnet:7.0 AS base
WORKDIR /app
EXPOSE 5274
EXPOSE 11111
EXPOSE 30000

ENV ASPNETCORE_URLS=http://+:5274

FROM mcr.microsoft.com/dotnet/sdk:7.0 AS build
ARG configuration=Release
COPY . .
RUN dotnet restore "src/apps/marketing/marketing.csproj"
WORKDIR "/src/apps/marketing"
RUN dotnet build "marketing.csproj" -c $configuration -o /app/build

FROM build AS publish
ARG configuration=Release
RUN dotnet publish "marketing.csproj" -c $configuration -o /app/publish

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "marketing.dll"]