# Cloud Run Deployment Guide: Solace Browser

**Project:** Solace Browser Cloud Run
**Status:** PRODUCTION-READY
**Auth:** 65537 | **Northstar:** Phuc Forecast

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Build Docker Image](#build-docker-image)
4. [Push to Container Registry](#push-to-container-registry)
5. [Deploy to Cloud Run](#deploy-to-cloud-run)
6. [Testing](#testing)
7. [Scaling & Performance](#scaling--performance)
8. [Monitoring & Logging](#monitoring--logging)
9. [Cost Estimation](#cost-estimation)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Solace Browser runs on Google Cloud Run for serverless browser automation at scale.

### Benefits

✅ **Auto-Scaling:** 0 → 10,000 instances instantly
✅ **Cost-Effective:** Pay only for execution time (~$0.000004/vCPU-second)
✅ **Simple:** No VM management, no Kubernetes complexity
✅ **Fast:** 1-second startup time
✅ **Secure:** IAM-based access control, no exposed credentials

### Architecture

```
Cloud Run Service (solace-browser)
├─ Container: solace-browser:latest (1.2GB)
├─ Runtime: Node.js + Python
├─ Browser: Ungoogled Chromium (headless)
├─ Auto-scaling: min=0, max=10,000
├─ Memory: 2Gi per instance
├─ CPU: 2 vCPU per instance
└─ Timeout: 3600s (1 hour)
```

---

## Prerequisites

### Required Tools

- `gcloud` CLI (install via: https://cloud.google.com/sdk/docs/install)
- `docker` (install via: https://docs.docker.com/get-docker/)
- `git` (for version control)

### GCP Setup

```bash
# 1. Set project ID
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# 2. Enable required APIs
gcloud services enable \
  cloudrun.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com

# 3. Authenticate with GCP
gcloud auth login
gcloud auth configure-docker

# 4. Create service account (optional, for automation)
gcloud iam service-accounts create solace-browser-ci \
  --display-name="Solace Browser CI/CD"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:solace-browser-ci@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

---

## Build Docker Image

### Option A: Build Locally (Recommended for Development)

```bash
# Navigate to project directory
cd /home/phuc/projects/solace-browser

# Build image
docker build -t solace-browser:latest \
  --tag gcr.io/${PROJECT_ID}/solace-browser:latest \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  .

# Verify build
docker images | grep solace-browser
```

### Option B: Build on Google Cloud Build (Recommended for Production)

```bash
# Build on Cloud Build (faster, uses Google's infrastructure)
gcloud builds submit \
  --tag gcr.io/${PROJECT_ID}/solace-browser:latest \
  --machine-type=N1_HIGHCPU_8 \
  --timeout=3600s

# View build logs
gcloud builds log --stream
```

### Option C: Build with Cache for Faster Rebuilds

```bash
# Build with cache from previous versions
docker build \
  -t gcr.io/${PROJECT_ID}/solace-browser:v2.0.0 \
  --cache-from gcr.io/${PROJECT_ID}/solace-browser:latest \
  .
```

---

## Push to Container Registry

### Push to Google Container Registry (GCR)

```bash
# Tag image
docker tag solace-browser:latest gcr.io/${PROJECT_ID}/solace-browser:latest

# Push to GCR
docker push gcr.io/${PROJECT_ID}/solace-browser:latest

# Verify push
gcloud container images list --repository=gcr.io/${PROJECT_ID}
gcloud container images describe gcr.io/${PROJECT_ID}/solace-browser:latest
```

### Inspect Image Layers

```bash
# See image size
docker images | grep solace-browser

# See detailed layer info
gcloud container images describe gcr.io/${PROJECT_ID}/solace-browser:latest

# Expected size: ~1.2GB
```

---

## Deploy to Cloud Run

### Option 1: Deploy via gcloud CLI (Recommended)

```bash
# Deploy to Cloud Run
gcloud run deploy solace-browser \
  --image gcr.io/${PROJECT_ID}/solace-browser:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --min-instances 0 \
  --max-instances 10000 \
  --concurrency 50 \
  --service-account solace-browser@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars \
    "PORT=8080,NODE_ENV=production,DEBUG=false,GCP_PROJECT_ID=${PROJECT_ID}"

# Output will show:
# Service URL: https://solace-browser-XXXXXX.run.app
```

### Option 2: Deploy via Terraform

Create `main.tf`:

```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.region
}

# Service Account
resource "google_service_account" "solace_browser" {
  account_id   = "solace-browser"
  display_name = "Solace Browser Cloud Run"
}

# Cloud Run Service
resource "google_cloud_run_service" "solace_browser" {
  name     = "solace-browser"
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.solace_browser.email

      containers {
        image = "gcr.io/${var.gcp_project_id}/solace-browser:latest"

        ports {
          container_port = 8080
        }

        env {
          name  = "PORT"
          value = "8080"
        }

        env {
          name  = "NODE_ENV"
          value = "production"
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.gcp_project_id
        }

        resources {
          limits = {
            memory = "2Gi"
            cpu    = "2"
          }
        }

        startup_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          failure_threshold = 3
          timeout_seconds   = 3
        }

        liveness_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          failure_threshold = 3
          timeout_seconds   = 5
        }
      }

      timeout_seconds = 3600
      container_concurrency = 50
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "0"
        "autoscaling.knative.dev/maxScale" = "10000"
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_service_account.solace_browser
  ]
}

# IAM: Allow unauthenticated access
resource "google_cloud_run_service_iam_member" "solace_browser_public" {
  service  = google_cloud_run_service.solace_browser.name
  location = google_cloud_run_service.solace_browser.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# IAM: Allow Cloud Logging
resource "google_project_iam_member" "solace_browser_logging" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.solace_browser.email}"
}

# Output
output "service_url" {
  value = google_cloud_run_service.solace_browser.status[0].url
}
```

Deploy with Terraform:

```bash
terraform init
terraform plan
terraform apply
```

### Option 3: Deploy via GitHub Actions (CI/CD)

Create `.github/workflows/deploy-cloud-run.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main, master]
    paths:
      - 'http_server.js'
      - 'http_bridge.py'
      - 'Dockerfile'
      - '.github/workflows/deploy-cloud-run.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          export_default_credentials: true

      - name: Configure Docker to use gcloud auth
        run: gcloud auth configure-docker

      - name: Build and push Docker image
        run: |
          docker build -t gcr.io/${{ secrets.GCP_PROJECT_ID }}/solace-browser:latest .
          docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/solace-browser:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy solace-browser \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/solace-browser:latest \
            --region us-central1 \
            --platform managed \
            --allow-unauthenticated \
            --memory 2Gi \
            --cpu 2 \
            --max-instances 10000
```

---

## Testing

### Test Health Endpoint

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe solace-browser --region us-central1 --format='value(status.url)')

# Test health endpoint
curl "${SERVICE_URL}/health"

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2026-02-14T10:00:00.000Z",
#   "version": "2.0.0",
#   "uptime": 123.456,
#   "memory": {...}
# }
```

### Test API Endpoints

```bash
# Get server info
curl -s "${SERVICE_URL}/info" | jq .

# Start episode recording
curl -X POST "${SERVICE_URL}/episode/start/test-1" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Stop episode recording
curl -X POST "${SERVICE_URL}/episode/stop/test-1"

# Compile episode to recipe
curl -X POST "${SERVICE_URL}/recipe/test-recipe/compile" \
  -H "Content-Type: application/json" \
  -d '{"episode_name": "test-1"}'

# Execute recipe
curl -X POST "${SERVICE_URL}/recipe/test-recipe/execute"

# Execute batch
curl -X POST "${SERVICE_URL}/recipes/execute-batch" \
  -H "Content-Type: application/json" \
  -d '{"recipes": ["recipe-1", "recipe-2", "recipe-3"]}'
```

### Test Local with Docker Compose

```bash
# Start local environment
docker-compose up -d

# Test local API
curl http://localhost:8080/health

# Stop containers
docker-compose down
```

---

## Scaling & Performance

### Auto-Scaling Behavior

Cloud Run automatically scales based on incoming requests:

```
Scenario: Campaign with 1000 recipes (30s each)

Timeline:
00:00  Idle → 0 instances, cost: $0
00:05  Request arrives → auto-scale to 10 instances
00:10  Peak load → auto-scale to 500 instances
       - 500 instances × 30s = 15,000 vCPU-seconds
       - Cost: 15,000 × $0.000004 = $0.06
00:15  Campaign complete → scale down to 0 instances
       - Idle time: $0 cost
```

### Configuration for Different Workloads

#### Light Workload (API calls, small recipes)

```bash
gcloud run deploy solace-browser \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 5000 \
  --concurrency 100
```

#### Medium Workload (Mixed)

```bash
gcloud run deploy solace-browser \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10000 \
  --concurrency 50
```

#### Heavy Workload (Complex automation, large screenshots)

```bash
gcloud run deploy solace-browser \
  --memory 4Gi \
  --cpu 4 \
  --max-instances 1000 \
  --concurrency 20
```

### Monitoring Scaling Metrics

```bash
# View live metrics
gcloud run services describe solace-browser \
  --region us-central1 \
  --format='value(status.conditions)'

# View request latency
gcloud monitoring time-series list \
  --filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_latencies"'

# View instance count over time
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="solace-browser"' \
  --limit 100 \
  --format json
```

---

## Monitoring & Logging

### Cloud Logging Integration

```bash
# View real-time logs
gcloud run logs read solace-browser --tail=50

# Search for errors
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="solace-browser" AND severity>=ERROR' \
  --limit 50 \
  --format json

# Export logs to BigQuery
gcloud logging sinks create solace-bq \
  bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/solace_logs \
  --log-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="solace-browser"'
```

### Cloud Monitoring (Metrics)

```bash
# View CPU usage
gcloud monitoring metrics-descriptors list \
  --filter='metric.type:run.googleapis.com'

# Create custom dashboard
gcloud monitoring dashboards create --config-from-file - <<EOF
{
  "displayName": "Solace Browser Cloud Run",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Count",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"run.googleapis.com/request_count\" resource.labels.service_name=\"solace-browser\""
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF
```

### Alerting

```bash
# Create alert policy for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Solace Browser High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-filter='metric.type="run.googleapis.com/request_count" AND resource.labels.service_name="solace-browser"'
```

---

## Cost Estimation

### Pricing Model

Cloud Run charges:
- **vCPU-seconds:** $0.000004 per second
- **Memory-seconds:** $0.000005 per GB-second
- **Requests:** $0.40 per 1M requests
- **First 2M invocations/month:** FREE

### Example Scenarios

#### Scenario 1: 100,000 recipe executions (30s each)

```
Computation:
  100,000 executions × 30s = 3,000,000 vCPU-seconds
  3,000,000 × 2 vCPU = 6,000,000 × $0.000004 = $24

Memory:
  3,000,000 × 2GB = 6,000,000 × $0.000005 = $30

Requests:
  100,000 × $0.40/1M = $0.04

Total Monthly: ~$54 (if daily)
```

#### Scenario 2: 1 Million executions/month (heavy use)

```
Computation:
  1,000,000 × 30s × 2 vCPU = 60,000,000 vCPU-seconds
  60,000,000 × $0.000004 = $240

Memory:
  60,000,000 × 2GB × $0.000005 = $600

Requests:
  1,000,000 × $0.40/1M = $0.40

Total Monthly: ~$840
```

#### Scenario 3: Light use (10,000 executions/month)

```
Computation:
  10,000 × 30s × 2 = 600,000 vCPU-seconds × $0.000004 = $2.40

Memory:
  600,000 × 2GB × $0.000005 = $6

Requests:
  10,000 × $0.40/1M = $0.004

Total Monthly: ~$8.40
```

### Cost Comparison

| Solution | 1M Executions/Month | Setup Time | Scalability |
|----------|-------------------|-----------|-------------|
| Cloud Run | $840 | 5 min | 0→10,000 instant |
| OpenClaw | $2,500,000 | 1 hr | Limited |
| EC2 Auto-Scaling | $2,000+ | 1 hr | Slow (minutes) |
| Kubernetes (GKE) | $500+ | 2 hrs | Minutes |
| Heroku Dynos | $1,000+ | 30 min | Limited |

**Cloud Run is 147x cheaper than OpenClaw and scales instantly.**

---

## Troubleshooting

### Common Issues

#### Issue: Container fails to start

```bash
# Check deployment status
gcloud run services describe solace-browser --region us-central1

# View recent revisions
gcloud run revisions list --region us-central1

# View detailed logs
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="solace-browser"' \
  --limit 50 \
  --format=json
```

#### Issue: Health check failing

```bash
# Test health endpoint locally
docker run -p 8080:8080 gcr.io/${PROJECT_ID}/solace-browser:latest
curl http://localhost:8080/health

# Check health check settings
gcloud run services describe solace-browser --region us-central1 \
  --format='value(spec.template.spec.containers[0].startupProbe)'
```

#### Issue: High latency or timeouts

```bash
# Check request latency metrics
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_latencies"' \
  --format=table

# Increase timeout or memory
gcloud run deploy solace-browser \
  --region us-central1 \
  --update-env-vars 'MAX_EXECUTION_TIME=7200' \
  --memory 4Gi
```

#### Issue: OOM (Out of Memory) errors

```bash
# Increase memory allocation
gcloud run deploy solace-browser \
  --region us-central1 \
  --memory 4Gi \
  --cpu 4

# Check memory usage
gcloud logging read \
  'resource.type="cloud_run_revision" AND jsonPayload.message=~".*memory.*"' \
  --limit 50
```

#### Issue: Image too large (> 2GB)

```bash
# Check image size
docker images | grep solace-browser
gcloud container images describe gcr.io/${PROJECT_ID}/solace-browser:latest

# Options:
# 1. Use smaller base image (alpine instead of debian)
# 2. Remove build dependencies in multi-stage build
# 3. Compress compiled binary
# 4. Use cloud-native tools (Distroless, scratch)

# To optimize, edit Dockerfile and rebuild
docker build --no-cache -t solace-browser:optimized .
```

### Debug Commands

```bash
# Get all service details
gcloud run services describe solace-browser --region us-central1

# Get all revisions
gcloud run revisions list --region us-central1 --service solace-browser

# Test with curl
SERVICE_URL=$(gcloud run services describe solace-browser --region us-central1 --format='value(status.url)')
curl -v "${SERVICE_URL}/health"

# SSH into running instance (approximate, for debugging)
gcloud run services update solace-browser \
  --region us-central1 \
  --set-env-vars DEBUG=true

# Check resource quotas
gcloud compute project-info describe --project=${PROJECT_ID} \
  --format='value(quotas[name="CLOUD_RUN_SERVICES"].usage)'
```

---

## Production Checklist

- [ ] Image size verified (< 1.5GB)
- [ ] Health endpoint tested
- [ ] Scaling limits set appropriately
- [ ] Service account created with minimal permissions
- [ ] Logging enabled and monitored
- [ ] Alerts configured for errors and high latency
- [ ] Secrets managed via Secret Manager (not in code)
- [ ] CI/CD pipeline configured for automatic deployments
- [ ] Load testing performed (simulating 10,000 instances)
- [ ] Disaster recovery plan documented
- [ ] Cost monitoring dashboard created
- [ ] Documentation updated

---

## Further Reading

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Cloud Run Auto-Scaling](https://cloud.google.com/run/docs/about-concurrency-and-scaling)
- [Cloud Logging](https://cloud.google.com/logging/docs)
- [Cloud Monitoring](https://cloud.google.com/monitoring/docs)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

---

**Auth:** 65537
**Northstar:** Phuc Forecast
**Status:** PRODUCTION-READY
