# Google Cloud — machine-to-machine (workload) auth

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

## Suggested next step for this repo

1. Decide **which caller** needs GCP (GitHub Actions only vs. MCP server runtime vs. long-running agent on Cloud Run).
2. If **GitHub → GCP**: implement **Path A** and store only the WIF provider + SA email in GitHub secrets.
3. If **MCPize container → your GCP**: prefer **Path B** (deploy a small proxy or worker on Cloud Run with an attached SA) or expose only **public HTTPS APIs** with your own auth — feeding SA keys into a third-party host is high risk.

For Vertex / Gemini from **local** dev, `gcloud auth application-default login` is enough; do not commit keys.
