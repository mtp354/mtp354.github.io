# quantum-radar-starter

A GitHub Actions "orchestrator" repository for three unattended jobs:

1. **Daily repo health checks** across one or more repositories you own.
2. **Quantum publications + news digests** every 2 days.
3. **Quantum opportunities digests** every 3 days (grants, hackathons, summer schools/camps, internships, fellowships).

The workflows are designed to run on GitHub's hosted runners, so they keep running even when your laptop is off.

## Repository layout

```text
.
├── .github/workflows/
├── config/
├── reports/
├── scripts/
└── state/
```

## Quick start

1. Create a new GitHub repo, for example `quantum-radar`.
2. Copy these files into it.
3. Edit:
   - `config/monitored_repos.yaml`
   - `config/publications.yaml`
   - `config/opportunities.yaml`
4. In GitHub, add a repository secret named `MONITORED_REPOS_TOKEN` if you want to scan **private** repositories.
5. Push to your default branch.
6. In the Actions tab, manually run each workflow once using **Run workflow**.

## What gets written

- `reports/repo-health/latest.md`
- `reports/publications-news/latest.md`
- `reports/opportunities/latest.md`
- dated snapshots in matching subfolders
- lightweight dedupe state in `state/*.json`

## Notes

- The repo-health workflow can open an issue in this repository when one of your checks fails.
- The digests commit markdown files back into this repo so you get a persistent archive.
- The search side is intentionally simple and low-maintenance. Start here, then tighten the filters after seeing 1–2 weeks of output.

## Suggested first edits

Replace the sample repositories in `config/monitored_repos.yaml` with your own repos and commands.

Example checks you might use:
- `python -m pytest -q`
- `python -m compileall .`
- `ruff check .`
- `python -m pip check`
- `jupyter nbconvert --execute --to notebook --inplace notebook.ipynb`
