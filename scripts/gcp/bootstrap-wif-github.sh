#!/usr/bin/env bash
# One-time bootstrap: GitHub Actions -> GCP via Workload Identity Federation (no JSON keys).
# Run in Cloud Shell or any shell with gcloud authenticated to the target project.
# Usage:
#   export GCP_PROJECT_ID="your-project-id"
#   export GITHUB_ORG="Hobie1Kenobi"
#   export GITHUB_REPO="agentic-crypto-swarm-prototype"
#   ./scripts/gcp/bootstrap-wif-github.sh
#
# Optional overrides:
#   POOL_ID=github  PROVIDER_ID=github  SA_ID=github-actions-wif

set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
: "${GITHUB_ORG:?Set GITHUB_ORG}"
: "${GITHUB_REPO:?Set GITHUB_REPO}"

POOL_ID="${POOL_ID:-github}"
PROVIDER_ID="${PROVIDER_ID:-github}"
SA_ID="${SA_ID:-github-actions-wif}"
SA_EMAIL="${SA_ID}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
REPO_FULL="${GITHUB_ORG}/${GITHUB_REPO}"

echo "==> Resolving project number for ${GCP_PROJECT_ID}"
PROJECT_NUMBER="$(gcloud projects describe "${GCP_PROJECT_ID}" --format='value(projectNumber)')"
echo "    PROJECT_NUMBER=${PROJECT_NUMBER}"

echo "==> Enabling APIs"
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com --project="${GCP_PROJECT_ID}"

echo "==> Service account ${SA_EMAIL}"
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${GCP_PROJECT_ID}" &>/dev/null; then
  gcloud iam service-accounts create "${SA_ID}" \
    --project="${GCP_PROJECT_ID}" \
    --display-name="GitHub Actions (WIF)"
fi

echo "==> Workload identity pool ${POOL_ID}"
if ! gcloud iam workload-identity-pools describe "${POOL_ID}" --project="${GCP_PROJECT_ID}" --location=global &>/dev/null; then
  gcloud iam workload-identity-pools create "${POOL_ID}" \
    --project="${GCP_PROJECT_ID}" \
    --location=global \
    --display-name="GitHub Actions"
fi

echo "==> OIDC provider ${PROVIDER_ID}"
if ! gcloud iam workload-identity-pools providers describe "${PROVIDER_ID}" \
    --project="${GCP_PROJECT_ID}" --location=global --workload-identity-pool="${POOL_ID}" &>/dev/null; then
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
    --project="${GCP_PROJECT_ID}" \
    --location=global \
    --workload-identity-pool="${POOL_ID}" \
    --display-name="GitHub" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository=='${REPO_FULL}'"
fi

echo "==> Allow GitHub repo to impersonate ${SA_EMAIL}"
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${GCP_PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${GITHUB_ORG}/${GITHUB_REPO}"

WIP_RESOURCE="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"

echo ""
echo "=== Next steps (GitHub) ==="
echo "Option A — GitHub web UI:"
echo "  1) Variables: GCP_WIF_ENABLED=true, GCP_PROJECT_ID=${GCP_PROJECT_ID}"
echo "  2) Secrets: GCP_WORKLOAD_IDENTITY_PROVIDER, GCP_SERVICE_ACCOUNT_EMAIL"
echo ""
echo "Option B — from a Windows clone (gh auth login):"
echo "  pwsh scripts/gcp/push-wif-to-github.ps1 \\"
echo "    -GcpProjectId '${GCP_PROJECT_ID}' \\"
echo "    -WorkloadIdentityProvider '${WIP_RESOURCE}' \\"
echo "    -ServiceAccountEmail '${SA_EMAIL}' \\"
echo "    -RunVerify"
echo ""
echo "Values for copy/paste:"
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER=${WIP_RESOURCE}"
echo "  GCP_SERVICE_ACCOUNT_EMAIL=${SA_EMAIL}"
echo ""
echo "Grant this SA least-privilege roles, e.g.:"
echo "  gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \\"
echo "    --member=serviceAccount:${SA_EMAIL} \\"
echo "    --role=roles/viewer"
echo ""
echo "Then confirm: Actions -> 'GCP WIF verify' (or -RunVerify above)"
