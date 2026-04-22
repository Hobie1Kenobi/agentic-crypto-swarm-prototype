# Google Cloud — machine-to-machine (workload) auth

## Swarm-Economy default (implemented in-repo)

**Use GitHub Actions + Workload Identity Federation (WIF)** for any GCP access from CI (Vertex, Secret Manager, Artifact Registry, etc.). It avoids service account JSON keys in GitHub and keeps MCPize (third-party host) free of GCP long-lived credentials.

| Step | Action |
|------|--------|
| 1 | In your GCP project, run **`scripts/gcp/bootstrap-wif-github.sh`** (Cloud Shell or local `gcloud` logged in as project admin). Set `GCP_PROJECT_ID`, `GITHUB_ORG`, `GITHUB_REPO`. |
| 2 | In GitHub: **Variables** — `GCP_WIF_ENABLED=true`, `GCP_PROJECT_ID=<id>`. **Secrets** — `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT_EMAIL` (values printed by the script). |
| 3 | Grant the new service account **least-privilege IAM roles** for what CI will do (example in script output: start with `roles/viewer` for a smoke test). |
| 4 | **Actions → “GCP WIF verify” → Run workflow** to confirm. |

Workflow file: [`.github/workflows/gcp-wif-verify.yml`](../../.github/workflows/gcp-wif-verify.yml).

Runtime on **MCPize** should not hold GCP keys; if agents need Gemini/Vertex from production, prefer **Ollama / existing LLM env** or a **small Cloud Run** service in your project (attached service account, Path B below).

---

Google does not sell a single product named “M2M platform.” For **service-to-service** auth you usually use one of these:

| Pattern | Use when |
|--------|-----------|
| **Workload Identity Federation (WIF)** | Workloads **outside** GCP (GitHub Actions, other clouds, on-prem) need to call GCP APIs **without** long‑lived service account JSON keys. |
| **Attached service accounts (ADC)** | Workloads **on** GCP: Cloud Run, GKE, Compute Engine — use the metadata server; no key files. |
| **Managed workload identities (preview)** | Strong **workload-to-workload mTLS** (SPIFFE-style certs via CA Service) for GCE/GKE; separate from “call the Storage API.” |

MCPize already builds on Google Cloud (e.g. Cloud Build, Artifact Registry) under **their** project. This doc is for **your** GCP project when **your** agents, CI, or APIs must call Vertex, Secret Manager, Logging, etc.

---

## Path A — Workload Identity Federation (recommended for GitHub / external hosts)

**Goal:** A workflow or server obtains **short-lived** GCP credentials by exchanging an **OIDC** token (e.g. from GitHub) for federated access, then optionally **impersonates** a dedicated service account.

**High-level steps**

1. In **your** GCP project, enable **IAM Credentials API** and any APIs you need (e.g. Vertex AI API, Secret Manager API).
2. Create a **service account** used only for automation (e.g. `swarm-ci-gcp@PROJECT_ID.iam.gserviceaccount.com`). Grant it least-privilege roles (e.g. `roles/aiplatform.user`, `roles/secretmanager.secretAccessor`).
3. Create a **workload identity pool** and **OIDC provider** (GitHub: issuer `https://token.actions.githubusercontent.com`, attribute mapping for `sub` / `attribute.repository`).
4. **Allow** the pool principal to **impersonate** that service account (`roles/iam.workloadIdentityUser` on the SA, principal like `principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/attribute.repository/OWNER/REPO`).
5. In GitHub Actions, use **`google-github-actions/auth`** with `workload_identity_provider` and `service_account` — no `GOOGLE_APPLICATION_CREDENTIALS` JSON in secrets.

**References**

- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GitHub → keyless with WIF](https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
- [Authenticate with auth libraries (ADC + WIF)](https://cloud.google.com/iam/docs/authenticate-with-auth-libraries)

---

## Path B — Running on GCP (Cloud Run / GKE / GCE)

**Goal:** No keys in the image; use the resource’s **attached service account**.

1. Create a service account with minimal roles.
2. Attach it to Cloud Run / GKE workload / GCE instance.
3. Use **Application Default Credentials** in code (`google.auth.default()` in Python, or client libraries with default credential chain).

**References**

- [ADC overview](https://cloud.google.com/docs/authentication/application-default-credentials)

---

## Path C — Managed workload identities (mTLS between workloads)

**Goal:** **Mutual TLS** between workloads (SPIFFE IDs, CA Service), not “get a bearer token for BigQuery.”

- [Managed workload identities overview](https://cloud.google.com/iam/docs/managed-workload-identity)
- [mTLS on Compute Engine](https://cloud.google.com/compute/docs/access/authenticate-workloads-over-mtls)

Use this when product/security requires **peer-verified** connections between services; it is heavier than WIF + IAM for typical API access.

---

## Env hints (local / CI)

| Variable | Meaning |
|----------|--------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to **JSON key** (avoid in production; prefer WIF or attached SA). |
| `GOOGLE_CLOUD_PROJECT` | Default project ID for many client libraries. |

For WIF outside GCP, tools usually use a **credential configuration JSON** from `gcloud iam workload-identity-pools create-cred-config` and set `GOOGLE_APPLICATION_CREDENTIALS` to that file **or** use Actions/auth that exports env for ADC.

---

## See also

The **default caller** for this repo is **GitHub Actions** (section at top). For **MCPize → GCP**, use Path B (Cloud Run) or avoid GCP in that process. For **local** Vertex/Gemini, `gcloud auth application-default login` is enough; do not commit keys.
