#!/bin/bash

if [ -f src/backend/appsettings.json ]; then
    echo "appsettings.json already exists"
else
    cp src/backend/appsettings.local.template.json src/backend/appsettings.json
    echo "appsettings.json created"
fi

if grep -q "<mandatory>" src/backend/appsettings.local.template.json; then
    echo "Please update the appsettings.json file with the correct values" >&2
    exit 1
fi

gnome-terminal -- bash -c "cd src/backend/ && dotnet run; exec bash"
gnome-terminal -- bash -c "cd src/frontend/ && npm run dev; exec bash"