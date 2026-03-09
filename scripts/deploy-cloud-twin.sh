#!/usr/bin/env bash
set -euo pipefail

PROJECT="solace-461818"
REGION="us-central1"
SERVICE="solace-browser-twin"
IMAGE="gcr.io/${PROJECT}/solace-browser:phase2-v2"

gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --port 8888 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 3 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "SOLACE_CLOUD_TWIN=true,SOLACE_NO_GUI=true" \
  --no-cpu-throttling

echo "Deployed: $(gcloud run services describe "${SERVICE}" --region="${REGION}" --format='value(status.url)')"
