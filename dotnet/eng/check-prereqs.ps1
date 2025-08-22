param (
    [switch]$InstallMissing
)

$ErrorActionPreference = "Stop"
$Missing = @()

function Check-Command {
    param ([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Host ("Missing: {0,-10} - not found in PATH" -f $Name)
        $script:Missing += $Name
    }
    else {
        Write-Host ("Found:   {0,-10}" -f $Name)
    }
}

function Install-Tool {
    param ([string]$Tool)
    Write-Host "Installing $Tool..."

    switch ($Tool) {
        "python" {
            if (Get-Command winget -ErrorAction SilentlyContinue) {
                winget install -e --id Python.Python.3
            }
            elseif (Get-Command choco -ErrorAction SilentlyContinue) {
                choco install python3 -y
            }
            else {
                Write-Host "No supported package manager (winget or choco) found."
                exit 1
            }
        }
        "uv" {
            Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing | Invoke-Expression
        }
        default {
            Write-Host "No install logic defined for: $Tool"
            exit 1
        }
    }
}

Write-Host "Checking for required tools..."
Check-Command python
Check-Command uv

if ($Missing.Count -gt 0) {
    Write-Host "`nMissing tools detected: $Missing"

    if ($InstallMissing) {
        foreach ($tool in $Missing) {
            Install-Tool $tool
        }
        Write-Host "`nAll missing tools installed."
    }
    else {
        Write-Host "`nSome required tools are missing. Re-run with '--install-missing' to install them."
        Write-Host ""
            Write-Host "For manual setup instructions, see:"
            Write-Host "https://github.com/microsoft/autogen/blob/main/python/README.md#setup"
        exit 1
    }
}
else {
    Write-Host "`nAll required tools are installed."
}
