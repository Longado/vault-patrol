#!/usr/bin/env bash
# 闸 3: deploy vault-patrol to Cloud Run and wire the demo repo's push webhook.
# Vertex mode: the model is reached through the runtime service account (ADC), not an API key.
# Idempotent: safe to re-run. Reads secrets from .env, never prints them.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-vault-patrol}"
DEMO_REPO="${DEMO_REPO:-Longado/vault-patrol-demo}"

export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"

if [ -f .env ]; then set -a; source ./.env; set +a; fi
: "${GITHUB_TOKEN:=$(gh auth token 2>/dev/null || true)}"
: "${GITHUB_TOKEN:?set GITHUB_TOKEN in .env or log in with gh}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.5-flash}"
VERTEX_PROJECT="${GOOGLE_CLOUD_PROJECT:-${PROJECT:-}}"
# gemini-3.5-flash is only served from the `global` Vertex endpoint; this is not the Cloud Run region.
VERTEX_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"
if [ -z "${PROJECT:-}" ] || [ "$PROJECT" = "(unset)" ]; then
  echo "PROJECT is unset: PROJECT=<gcp-project-id> bash scripts/deploy.sh" >&2; exit 1
fi

echo "==> project=$PROJECT region=$REGION service=$SERVICE"
echo "==> vertex: project=$VERTEX_PROJECT location=$VERTEX_LOCATION model=$GEMINI_MODEL"
gcloud config set project "$PROJECT" >/dev/null

echo "==> enabling services (no-op if already enabled)"
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com aiplatform.googleapis.com --project "$PROJECT"

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
put_secret github-token "$GITHUB_TOKEN"
put_secret webhook-secret "$WEBHOOK_SECRET"

echo "==> iam for the runtime service account"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format 'value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
# cloudbuild.builds.builder: since 2024 the compute SA needs it explicitly to run `--source` builds
for role in roles/secretmanager.secretAccessor roles/aiplatform.user roles/cloudbuild.builds.builder; do
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:${RUNTIME_SA}" --role "$role" --condition=None >/dev/null
done

echo "==> deploying (Cloud Build from source; --no-cpu-throttling keeps background patrols alive)"
gcloud run deploy "$SERVICE" --source . --region "$REGION" --project "$PROJECT" --quiet \
  --allow-unauthenticated --no-cpu-throttling --timeout 600 --memory 1Gi \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=${VERTEX_PROJECT},GOOGLE_CLOUD_LOCATION=${VERTEX_LOCATION},GEMINI_MODEL=${GEMINI_MODEL}" \
  --set-secrets "GITHUB_TOKEN=github-token:latest,GITHUB_WEBHOOK_SECRET=webhook-secret:latest"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format 'value(status.url)')"
echo "==> service url: $URL"
echo -n "==> health: "; curl -sS "$URL/health"; echo   # /healthz is intercepted by the Cloud Run frontend

echo "==> github webhook on $DEMO_REPO"
HOOK_URL="$URL/webhook"
# match our own hook even if it still points at a previous revision's URL
HOOK_ID="$(gh api "repos/$DEMO_REPO/hooks" --jq '.[] | select(.config.url | endswith("/webhook")) | .id' | head -n1)"
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
echo "  cd ../vault-patrol-demo && echo '- 2026-08-30: patrol wired to Cloud Run' >> notes/changelog.md && git commit -qam 'seed rot' && git push"
echo "  gcloud run services logs read $SERVICE --region $REGION --limit 30"
