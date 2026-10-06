# How We Work on GitHub

## 1. Every piece of work is an issue
- Pick an issue from the Project board, assign yourself, move it to **In Progress**.
- No issue for what you're doing? Create one with the *Task* template first.
- Each issue has an `area:` label and a milestone (phase).

## 2. Branches
- `main` is protected: no direct pushes.
- Branch from `main` and name it `<area>/<issue-number>-<short-description>`, e.g. `ingestion/12-inspections-dag`, `dbt/18-stg-inspections`.

```bash
git checkout main && git pull
git checkout -b ingestion/12-inspections-dag
```

## 3. Commits
Small, focused commits with a clear message in the imperative:

```
Add incremental load for food inspections DAG
Fix null license numbers in stg_licenses
```

## 4. Pull requests
- Open a PR into `main` and fill in the template.
- Link the issue with `Closes #12` so it closes automatically on merge.
- Request **one reviewer** (a teammate who isn't the author). Ideally the owner of the area you touched, or the backup.
- CI must pass. The reviewer approves, then the **author** merges (squash merge).
- Keep PRs small: under ~400 changed lines where possible.

## 5. Reviews
- Review within 48 hours of being requested.
- Check: does it run, is it tested, does it match the issue, no secrets committed.
- Use "Request changes" for blockers and plain comments for suggestions.

## 6. Secrets and data
- Never commit `.env`, service-account JSON keys, API keys or raw data files.
- Use `gcloud auth application-default login` locally and Secret Manager / Astronomer environment variables in deployment.

## 7. Weekly rhythm
| When | What |
|---|---|
| Tuesday after class | Standup: review board, assign the week's issues |
| During the week | Branch → PR → review → merge |
| Sunday night | Everyone updates their issue status on the board |

## 8. AI-assistant use
The syllabus requires an appendix documenting the prompts and outputs that supported our work, plus the tool and version used. Add an entry to [docs/ai_usage_log.md](docs/ai_usage_log.md) whenever an AI tool meaningfully shaped code, analysis or writing, and fact-check what it gives you.
