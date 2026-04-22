#Requires -Version 5.1
<#
.SYNOPSIS
  Writes WIF-related GitHub Actions variables and secrets after scripts/gcp/bootstrap-wif-github.sh completes.

.DESCRIPTION
  Requires GitHub CLI (gh) authenticated with repo + workflow scopes.
  Run from repo root after Cloud Shell printed GCP_WORKLOAD_IDENTITY_PROVIDER and SA email.

.EXAMPLE
  .\scripts\gcp\push-wif-to-github.ps1 `
    -GcpProjectId "my-gcp-project" `
    -WorkloadIdentityProvider "projects/123456789/locations/global/workloadIdentityPools/github/providers/github" `
    -ServiceAccountEmail "github-actions-wif@my-gcp-project.iam.gserviceaccount.com" `
    -RunVerify
#>
param(
    [Parameter(Mandatory = $true)]
    [string] $GcpProjectId,
    [Parameter(Mandatory = $true)]
    [string] $WorkloadIdentityProvider,
    [Parameter(Mandatory = $true)]
    [string] $ServiceAccountEmail,
    [string] $Repo = "Hobie1Kenobi/agentic-crypto-swarm-prototype",
    [switch] $RunVerify
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "Install GitHub CLI from https://cli.github.com and run: gh auth login"
}

gh variable set GCP_WIF_ENABLED -b "true" -R $Repo
gh variable set GCP_PROJECT_ID -b $GcpProjectId -R $Repo
gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER -b $WorkloadIdentityProvider -R $Repo
gh secret set GCP_SERVICE_ACCOUNT_EMAIL -b $ServiceAccountEmail -R $Repo

Write-Host "Updated Actions variables/secrets on $Repo" -ForegroundColor Green

if ($RunVerify) {
    gh workflow run "GCP WIF verify" -R $Repo
    Write-Host "Dispatched workflow 'GCP WIF verify'. Check Actions tab." -ForegroundColor Cyan
}
