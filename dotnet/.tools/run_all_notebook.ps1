# cd to the directory of this script
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$rootPath = Split-Path -Parent $scriptPath
$outputFolder = "$rootPath/output"
if (Test-Path $outputFolder) {
    Remove-Item $outputFolder -Recurse -Force
}
New-Item -ItemType Directory -Path $outputFolder

Set-Location $rootPath

# list all notebooks under notebook folder
$notebooks = Get-ChildItem -Path "$rootPath/notebook" -Recurse -Include *.ipynb | ForEach-Object { $_.FullName }
# skip those notebooks with the same name as the following
$skip_notebooks = @(
    'TwoAgentChat_UserProxy.ipynb' # require user input
)

# for each notebook, run it using dotnet perl. Check the exit code and print out the result
# if the exit code is not 0, exit the script with exit code 1
$failNotebooks = @()
$exitCode = 0
$LASTEXITCODE = 0
foreach ($notebook in $notebooks) {
    Write-Host "Running $notebook"
    # get notebook name with extension
    $name = Split-Path -Leaf $notebook

    if ($skip_notebooks -contains $name) {
        Write-Host "Skipping $name"
        continue
    }
    Write-Host "Name: $name"
    $notebookFolder = Split-Path -Parent $notebook
    $outputPath = "$outputFolder\$notebookFolder"
    Set-Location $notebookFolder
    $proc = Start-Process -FilePath dotnet -ArgumentList "repl --run $name --exit-after-run" -PassThru -NoNewWindow
    $timeout = $null
    $proc | Wait-Process -Timeout 180 -ErrorAction SilentlyContinue -ErrorVariable $timeout
    if ($timeout) {
        Write-Host "Timeout when running $notebook"
        $LASTEXITCODE = 1
    }
    else {
        $LASTEXITCODE = $proc.ExitCode
    }
    Write-Host "Exit code: $LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to run $notebook"
        $failNotebooks += $notebook
        $exitCode = 1
    }
    else{
        Write-Host "Successfully ran $notebook"
    }
    Set-Location $rootPath
}

Write-Host "Failed notebooks:"
foreach ($notebook in $failNotebooks) {
    Write-Host $notebook
}

$failNotebooks | Should -BeNullOrEmpty