#!/bin/bash

curl -k https://localhost:8081/_explorer/emulator.pem > ~/emulatorcert.crt
sudo cp ~/emulatorcert.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
sleep 10
dotnet restore sk-dev-team.sln
dotnet build util/seed-memory/seed-memory.csproj && dotnet util/seed-memory/bin/Debug/net7.0/seed-memory.dll