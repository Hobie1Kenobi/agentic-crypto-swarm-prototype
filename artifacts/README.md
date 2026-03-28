# Artifacts

Generated outputs from soak tests, demos, and report scripts. **Not** a substitute for versioned documentation in `documentation/` — these files are often large, overwritten each run, or machine-specific.

| Path | Role |
|------|------|
| `reports/` | `*_report.json`, `*_report.md`, cycle logs, checkpoints, manifests |
| `communication/` | Latest `communication_trace.json` / `.md` (per-cycle copies may be archived under `traces/`) |
| `proof_bundle/` | Realism / proof runs: `run-summary.json`, `cycles.csv`, `exceptions.csv`, `evidence/` |
| `traces/soak-24h/` | Archived per-cycle communication traces from 24h soak |
| `traces/realism/` | Archived traces from realism soak |

Retention is up to the operator; add large or sensitive runs to `.gitignore` if needed.
