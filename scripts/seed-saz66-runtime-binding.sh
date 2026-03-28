#!/usr/bin/env bash
# scripts/seed-saz66-runtime-binding.sh
set -e

API_URL="http://localhost:8888/api/v1/backoffice/solace-dev-manager"

echo "[Seeding SAZ66] Checking endpoint reachability..."
if ! curl -s "$API_URL/projects" > /dev/null; then
    echo "Error: solace-runtime not running at http://localhost:8888"
    exit 1
fi

echo "[Seeding SAZ66] Creating Project..."
PROJ_RESP=$(curl -s -X POST "$API_URL/projects" -H 'Content-Type: application/json' -d '{"name": "Solace Browser", "repository": "solace-browser", "description": "The Intelligence System Workspace"}')
PROJECT_ID=$(echo "$PROJ_RESP" | jq -r '.record.id')

if [ "$PROJECT_ID" == "null" ] || [ -z "$PROJECT_ID" ]; then
    echo "Failed to create project. Response: $PROJ_RESP"
    exit 1
fi

echo "[Seeding SAZ66] Creating Request..."
REQ_RESP=$(curl -s -X POST "$API_URL/requests" -H 'Content-Type: application/json' -d "{\"project_id\": \"$PROJECT_ID\", \"ticket_type\": \"feature\", \"title\": \"SAZ66 Runtime-Backed Dev Workflow Binding\", \"status\": \"assigned\"}")
REQUEST_ID=$(echo "$REQ_RESP" | jq -r '.record.id')

if [ "$REQUEST_ID" == "null" ] || [ -z "$REQUEST_ID" ]; then
    echo "Failed to create request. Response: $REQ_RESP"
    exit 1
fi

echo "[Seeding SAZ66] Creating active 'coder' Assignment..."
ASSGN_RESP=$(curl -s -X POST "$API_URL/assignments" -H 'Content-Type: application/json' -d "{\"request_id\": \"$REQUEST_ID\", \"target_role\": \"coder\", \"details\": \"Bind Hub UI assignment and inbox panels to /api/v1/backoffice/solace-dev-manager/... replacing role-derived mocks.\", \"status\": \"active\"}")
ASSGN_ID=$(echo "$ASSGN_RESP" | jq -r '.record.id')

echo "[Seeding SAZ66] Creating pending 'qa' Assignment..."
QA_RESP=$(curl -s -X POST "$API_URL/assignments" -H 'Content-Type: application/json' -d "{\"request_id\": \"$REQUEST_ID\", \"target_role\": \"qa\", \"details\": \"Verify coder implementation of SAZ66 binding.\", \"status\": \"pending\"}")

echo "[Seeding SAZ66] Creating assignment-linked Artifact..."
ARTIFACT_RESP=$(curl -s -X POST "$API_URL/artifacts" -H 'Content-Type: application/json' -d "{\"assignment_id\": \"$ASSGN_ID\", \"file_path\": \"/apps/solace-coder/outbox/runs/latest/evidence.json\", \"evidence_hash\": \"sac66-seeded-evidence\"}")

echo "[Seeding SAZ66] Creating assignment-linked Approval..."
APPROVAL_RESP=$(curl -s -X POST "$API_URL/approvals" -H 'Content-Type: application/json' -d "{\"assignment_id\": \"$ASSGN_ID\", \"approver_role\": \"manager\", \"status\": \"pending\", \"notes\": \"Awaiting manager review of runtime-backed binding.\"}")

echo "Seed complete! Check the Hub Dev workspace to see dynamic API data."
echo "Project ID: $PROJECT_ID"
echo "Request ID: $REQUEST_ID"
echo "Coder Assignment ID: $ASSGN_ID"
