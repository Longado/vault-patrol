# vault-patrol

**Your second brain rots. Every note tool helps you add; none helps you delete.**

vault-patrol is an event-driven agent for markdown knowledge vaults (Obsidian, Claude Code memory dirs, team wikis). On every push it audits the vault for *rot* — text that will mislead a future reader into acting on something no longer true — and opens **one subtraction-only pull request**. It never creates notes or tasks.

Built for the All Things Agentic Hackathon (Taskmaster track). Runs on Cloud Run with Gemini 3.5 via the Google GenAI SDK; secrets live in Secret Manager.

## What it catches

| Layer | Category | Detected by |
|---|---|---|
| mechanical | `broken_link` — index points at a missing file (**auto-deleted in the PR**) | code |
| mechanical | `orphan` — file nothing in the vault links to | code |
| mechanical | `dangling_wikilink` — `[[note]]` that does not exist | code |
| semantic | `stale_active_reference` — "use X" when another note says X was retired | Gemini, verified by code |
| semantic | `pinned_old_version` — boilerplate hard-coding a superseded model id / path | Gemini, verified by code |
| semantic | `overlap_cluster` — ≥3 notes saying the same thing | Gemini, verified by code |
| semantic | `hard_conflict` — two notes giving opposite instructions | Gemini, verified by code |
| semantic | `falsified_claim` — "used daily" next to a log showing 1 use in 17 days | Gemini, verified by code |

Every semantic finding must carry an `evidence_quote` that is a verbatim substring of the file. If it is not, code drops it. The PR shows how many were dropped.

Example PR: https://github.com/Longado/vault-patrol-demo/pull/1

## Architecture

See [docs/architecture.md](docs/architecture.md) (mermaid diagram + design rationale).

`GitHub push → Cloud Run (FastAPI) → code: mechanical checks → Gemini 3.5 (one structured call) → code: verify every quote → GitHub PR`. Every report records the model version and prompt version, so a change in either is traceable.

## Run locally (no cloud needed)

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest -q                                   # 11 passed
.venv/bin/python -m patrol run demo-vault --no-model  # mechanical layer only
cp .env.example .env                                  # add GEMINI_API_KEY
set -a && source .env && set +a
.venv/bin/python -m patrol run demo-vault             # + semantic layer
.venv/bin/python -m patrol repo owner/name            # clone → patrol → open PR (needs GITHUB_TOKEN)
.venv/bin/python -m patrol repo owner/name --ref <sha> # replay a specific sha locally
```

## Deploy to Google Cloud

```bash
PROJECT=<your-project>; REGION=us-central1
gcloud config set project $PROJECT
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
printf '%s' "$GITHUB_TOKEN"   | gcloud secrets create github-token --data-file=-
printf '%s' "$(openssl rand -hex 20)" | gcloud secrets create webhook-secret --data-file=-
gcloud run deploy vault-patrol --source . --region $REGION --allow-unauthenticated \
  --no-cpu-throttling --timeout 600 --memory 1Gi \
  --set-env-vars GEMINI_MODEL=gemini-3.5-flash \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest,GITHUB_TOKEN=github-token:latest,GITHUB_WEBHOOK_SECRET=webhook-secret:latest
```

Or just `PROJECT=<your-project> bash scripts/deploy.sh`, which does all of the above idempotently and wires the webhook.

Then add a GitHub webhook on your vault repo: payload URL `https://<service>.run.app/webhook`, content type JSON, secret = the `webhook-secret` value, event = push. Push to the default branch and a PR appears.

`--no-cpu-throttling` matters: the webhook returns 202 immediately and the patrol runs as a background task.

## Configuration

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio key (or set `GOOGLE_GENAI_USE_VERTEXAI=true` + `GOOGLE_CLOUD_PROJECT`) |
| `GEMINI_MODEL` | default `gemini-3.5-flash` |
| `GITHUB_TOKEN` | clone private vaults, push branch, open PR |
| `GITHUB_WEBHOOK_SECRET` | HMAC signature check for `/webhook` |

## Layout

```
patrol/vault.py        load vault → immutable snapshot (NFC-normalised paths)
patrol/mechanical.py   deterministic checks
patrol/models.py       Finding / SemanticReport / PatrolResult (reasoning first; subtraction-only Action enum)
patrol/semantic.py     the single Gemini call; prompt lives in prompts/semantic.md with a version stamp
patrol/adjudicate.py   code-level verification of every model finding
patrol/report.py       PATROL_REPORT.md + the one auto-applied edit (dead index lines)
patrol/github_ops.py   clone / push / open-or-update PR
patrol/runner.py       control flow: narrow retries, "clean vault → no PR"
app/main.py            Cloud Run service: /webhook (HMAC), /healthz
scripts/deploy.sh      one-command idempotent deploy + webhook wiring
demo-vault/            sample vault with every rot category planted
```

## Disclosure

All code was written during the submission period. The five semantic categories come from a manual checklist the author had been running by hand on their own notes; that checklist is prose, not code.
