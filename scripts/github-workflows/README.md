# Staged GitHub Actions for the settlement proof page

These workflow files could not be pushed to `.github/workflows/` from the
token used to open the proof-page PR (it lacks the `workflow` scope).

To enable automatic refresh:

1. Copy `proof-refresh.yml` to `.github/workflows/proof-refresh.yml`.
2. Apply `static.yml.patch` (or the equivalent generate step) to `.github/workflows/static.yml`.
3. Push with an account or token that has the `workflow` scope.

`proof-refresh.yml` generates `docs/proof/proof.json` every 6 hours, commits
it if it changed, and deploys GitHub Pages so the public page stays current
even when HOJO is down.
