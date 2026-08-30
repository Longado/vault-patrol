#!/usr/bin/env bash
# R3: deploy vault-patrol to Cloud Run and wire the demo repo's push webhook.
# Idempotent: safe to re-run. Reads secrets from .env, never prints them.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-vault-patrol}"
DEMO_REPO="${DEMO_REPO:-Longado/vault-patrol-demo}"

export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"

if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${GEMINI_API_KEY:?set GEMINI_API_KEY in .env}"
: "${GITHUB_TOKEN:=$(gh auth token 2>/dev/null || true)}"
: "${GITHUB_TOKEN:?set GITHUB_TOKEN in .env or log in with gh}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.5-flash}"
if [ -z "${PROJECT:-}" ] || [ "$PROJECT" = "(unset)" ]; then
  echo "PROJECT is unset: PROJECT=<gcp-project-id> bash scripts/deploy.sh" >&2; exit 1
fi

echo "==> project=$PROJECT region=$REGION service=$SERVICE model=$GEMINI_MODEL"
gcloud config set project "$PROJECT" >/dev/null

echo "==> enabling services (no-op if already enabled)"
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com --project "$PROJECT"

# create-or-update a secret from stdin
put_secret() {
  local name="$1" value="$2"
  if gcloud secrets describe "$name" --project "$PROJECT" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=- --project "$PROJECT" >/dev/null
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- --project "$PROJECT" >/dev/null
  fi
}

echo "==> secrets"
# The webhook secret must stay stable across runs, otherwise the GitHub hook breaks.
if gcloud secrets versions access latest --secret=webhook-secret --project "$PROJECT" >/dev/null 2>&1; then
  WEBHOOK_SECRET="$(gcloud secrets versions access latest --secret=webhook-secret --project "$PROJECT")"
else
  WEBHOOK_SECRET="$(openssl rand -hex 20)"
fi
put_secret gemini-api-key "$GEMINI_API_KEY"
put_secret github-token "$GITHUB_TOKEN"
put_secret webhook-secret "$WEBHOOK_SECRET"

echo "==> iam for the runtime service account"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format 'value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for role in roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:${RUNTIME_SA}" --role "$role" --condition=None >/dev/null
done

echo "==> deploying (Cloud Build from source; --no-cpu-throttling keeps background patrols alive)"
gcloud run deploy "$SERVICE" --source . --region "$REGION" --project "$PROJECT" \
  --allow-unauthenticated --no-cpu-throttling --timeout 600 --memory 1Gi \
  --set-env-vars "GEMINI_MODEL=${GEMINI_MODEL}" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,GITHUB_TOKEN=github-token:latest,GITHUB_WEBHOOK_SECRET=webhook-secret:latest"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format 'value(status.url)')"
echo "==> service url: $URL"
echo -n "==> healthz: "; curl -sS "$URL/healthz"; echo

echo "==> github webhook on $DEMO_REPO"
HOOK_URL="$URL/webhook"
HOOK_ID="$(gh api "repos/$DEMO_REPO/hooks" --jq ".[] | select(.config.url == \"$HOOK_URL\") | .id" | head -n1)"
if [ -n "$HOOK_ID" ]; then
  gh api -X PATCH "repos/$DEMO_REPO/hooks/$HOOK_ID" -F active=true -f 'events[]=push' \
    -f "config[url]=$HOOK_URL" -f config[content_type]=json -f "config[secret]=$WEBHOOK_SECRET" >/dev/null
  echo "    updated hook $HOOK_ID"
else
  HOOK_ID="$(gh api "repos/$DEMO_REPO/hooks" -f name=web -F active=true -f 'events[]=push' \
    -f "config[url]=$HOOK_URL" -f config[content_type]=json -f "config[secret]=$WEBHOOK_SECRET" --jq .id)"
  echo "    created hook $HOOK_ID"
fi

echo
echo "done. trigger a patrol with:"
echo "  cd ../vault-patrol-demo && echo '- [Retired planner notes](notes/planner_2025.md)' >> MEMORY.md && git commit -qam 'seed rot' && git push"
echo "  gcloud run services logs read $SERVICE --region $REGION --limit 30"
