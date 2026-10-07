[CmdletBinding()]
param(
    [switch]$Initialize
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$stateDirectory = Join-Path $env:LOCALAPPDATA "QuebecHealthAnalytics"
$logsDirectory = Join-Path $stateDirectory "logs"
$configurationFile = Join-Path $stateDirectory "snowflake.json"
$credentialFile = Join-Path $stateDirectory "snowflake-credential.xml"

function Initialize-SnowflakeConfiguration {
    New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null

    $account = Read-Host "Identifiant du compte Snowflake (ex. GFHQBMQ-HM47234)"
    if ([string]::IsNullOrWhiteSpace($account)) {
        throw "L'identifiant du compte Snowflake est obligatoire."
    }

    $credential = Get-Credential -Message "Entrez votre utilisateur et votre mot de passe Snowflake"
    @{ account = $account.Trim() } |
        ConvertTo-Json |
        Set-Content -LiteralPath $configurationFile -Encoding utf8
    $credential | Export-Clixml -LiteralPath $credentialFile

    Write-Host "Configuration enregistrée de manière sécurisée pour l'utilisateur Windows actuel."
}

if ($Initialize) {
    Initialize-SnowflakeConfiguration
    exit 0
}

if (-not (Test-Path -LiteralPath $configurationFile) -or
    -not (Test-Path -LiteralPath $credentialFile)) {
    throw "Configuration absente. Exécutez d'abord : .\automation\run_hourly_pipeline.ps1 -Initialize"
}

$pythonExecutable = Join-Path $projectRoot "venv\Scripts\python.exe"
$dbtExecutable = Join-Path $projectRoot "venv\Scripts\dbt.exe"

if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw "Python est introuvable dans le venv du projet."
}
if (-not (Test-Path -LiteralPath $dbtExecutable)) {
    throw "dbt est introuvable dans le venv du projet."
}

New-Item -ItemType Directory -Path $logsDirectory -Force | Out-Null
$logFile = Join-Path $logsDirectory ("pipeline_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$configuration = Get-Content -LiteralPath $configurationFile -Raw | ConvertFrom-Json
$credential = Import-Clixml -LiteralPath $credentialFile
$plainPassword = $credential.GetNetworkCredential().Password

Start-Transcript -LiteralPath $logFile | Out-Null
try {
    $env:SNOWFLAKE_ACCOUNT = $configuration.account
    $env:SNOWFLAKE_USER = $credential.UserName
    $env:SNOWFLAKE_PASSWORD = $plainPassword
    $env:SNOWFLAKE_WAREHOUSE = "HEALTH_ELT_WH"
    $env:SNOWFLAKE_DATABASE = "QUEBEC_HEALTH_DWH"
    $env:SNOWFLAKE_ROLE = "QUEBEC_HEALTH_INGESTION"

    Push-Location $projectRoot
    try {
        & $pythonExecutable ".\ingestion\emergency_hourly.py"
        if ($LASTEXITCODE -ne 0) {
            throw "L'ingestion Python a échoué avec le code $LASTEXITCODE."
        }

        $env:SNOWFLAKE_ROLE = "QUEBEC_HEALTH_TRANSFORM"
        & $dbtExecutable build `
            --project-dir ".\dbt\quebec_health" `
            --profiles-dir ".\dbt\quebec_health"
        if ($LASTEXITCODE -ne 0) {
            throw "La transformation dbt a échoué avec le code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    $plainPassword = $null
    Remove-Item Env:SNOWFLAKE_PASSWORD -ErrorAction SilentlyContinue
    Stop-Transcript | Out-Null
}

