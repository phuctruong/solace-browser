#!/usr/bin/env bash
set -euo pipefail

PROJECT="solace-461818"
REGION="us-central1"
SERVICE="solace-browser-twin"
IMAGE="gcr.io/${PROJECT}/solace-browser-twin:latest"

gcloud builds submit --config cloudbuild-twin.yaml .

gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --port 8888 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 3 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "SOLACE_CLOUD_TWIN=true,SOLACE_HEAD_HIDDEN=true" \
  --no-cpu-throttling

echo "Deployed: $(gcloud run services describe "${SERVICE}" --region="${REGION}" --format='value(status.url)')"
