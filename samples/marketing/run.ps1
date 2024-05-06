function New-MarketingBackendSettings {
    param(

    )
    if(Test-Path src/backend/appsettings.json) {
        Write-Host "appsettings.json already exists"
        return
    }

    Copy-Item src/backend/appsettings.local.template.json src/backend/appsettings.json
    Write-Host "appsettings.json created"

    if((Get-Content .\src\backend\appsettings.local.template.json -Raw | Select-String "<mandatory>") -ne $null) { 
        Write-Error "Please update the appsettings.json file with the correct values" -ErrorAction Stop
    }
}

$backendProc = Start-Process powershell -ArgumentList '-NoExit', '-Command cd src/backend/; dotnet run'
$frontendProc = Start-Process powershell -ArgumentList '-NoExit', '-Command cd src/frontend/; npm run dev'

