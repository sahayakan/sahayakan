#!/usr/bin/env bash
# Register a GitHub App with the Sahayakan platform.
#
# Usage:
#   bash cli/register_github_app.sh \
#     --app-id 123456 \
#     --app-name "Sahayakan" \
#     --private-key-file /path/to/sahayakan.pem \
#     --webhook-secret "whsec_..." \
#     --api-url "https://ai.helm-team.org/api"
#
# Requires: curl, jq (or python3 as fallback)
# Reads SAHAYAKAN_ADMIN_API_KEY from .env.local if present.

set -euo pipefail

# --- Defaults ---
APP_ID=""
APP_NAME=""
PEM_FILE=""
WEBHOOK_SECRET=""
API_URL=""
CADDY_USER="admin"
CADDY_PASS="sahayakan2026"

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Register a GitHub App and its installation with Sahayakan.

Required options:
  --app-id ID              GitHub App ID (numeric)
  --app-name NAME          GitHub App name
  --private-key-file PATH  Path to the .pem private key file
  --api-url URL            Sahayakan API base URL (e.g. https://ai.helm-team.org/api)

Optional:
  --webhook-secret SECRET  Webhook secret (if configured)
  --caddy-user USER        Caddy basic auth username (default: admin)
  --caddy-pass PASS        Caddy basic auth password (default: sahayakan2026)
  -h, --help               Show this help message

Environment:
  SAHAYAKAN_ADMIN_API_KEY  API key (auto-read from .env.local if present)
EOF
    exit 0
}

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --app-id)       APP_ID="$2"; shift 2 ;;
        --app-name)     APP_NAME="$2"; shift 2 ;;
        --private-key-file) PEM_FILE="$2"; shift 2 ;;
        --webhook-secret)   WEBHOOK_SECRET="$2"; shift 2 ;;
        --api-url)      API_URL="$2"; shift 2 ;;
        --caddy-user)   CADDY_USER="$2"; shift 2 ;;
        --caddy-pass)   CADDY_PASS="$2"; shift 2 ;;
        -h|--help)      usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# --- Validate required args ---
missing=()
[[ -z "$APP_ID" ]]   && missing+=("--app-id")
[[ -z "$APP_NAME" ]] && missing+=("--app-name")
[[ -z "$PEM_FILE" ]] && missing+=("--private-key-file")
[[ -z "$API_URL" ]]  && missing+=("--api-url")

if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Error: missing required options: ${missing[*]}"
    echo "Run with --help for usage."
    exit 1
fi

if [[ ! -f "$PEM_FILE" ]]; then
    echo "Error: private key file not found: $PEM_FILE"
    exit 1
fi

# --- Load API key ---
if [[ -z "${SAHAYAKAN_ADMIN_API_KEY:-}" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
    ENV_LOCAL="$SCRIPT_DIR/.env.local"
    if [[ -f "$ENV_LOCAL" ]]; then
        SAHAYAKAN_ADMIN_API_KEY="$(grep '^SAHAYAKAN_ADMIN_API_KEY=' "$ENV_LOCAL" | cut -d= -f2- | tr -d '"' | tr -d "'")"
    fi
fi

if [[ -z "${SAHAYAKAN_ADMIN_API_KEY:-}" ]]; then
    echo "Error: SAHAYAKAN_ADMIN_API_KEY not set and not found in .env.local"
    exit 1
fi

# --- JSON extraction helper ---
json_get() {
    local json="$1" field="$2"
    if command -v jq &>/dev/null; then
        echo "$json" | jq -r ".$field"
    else
        echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('$field',''))"
    fi
}

# --- Read and escape PEM file for JSON ---
PRIVATE_KEY=$(awk '{printf "%s\\n", $0}' "$PEM_FILE")

# --- Auth headers ---
# When Caddy basic auth is in front, we cannot send both Basic and Bearer in
# the Authorization header (curl -u sets Basic, but an explicit header overrides
# it).  Basic auth alone passes through both Caddy and the API middleware, so
# we only add Bearer when basic auth is not configured.
AUTH_ARGS=()
if [[ -n "$CADDY_USER" && -n "$CADDY_PASS" ]]; then
    AUTH_ARGS+=(-u "$CADDY_USER:$CADDY_PASS")
else
    AUTH_ARGS+=(-H "Authorization: Bearer $SAHAYAKAN_ADMIN_API_KEY")
fi

# --- Step 1: Register the GitHub App ---
echo "==> Registering GitHub App '$APP_NAME' (ID: $APP_ID)..."

WEBHOOK_JSON="null"
if [[ -n "$WEBHOOK_SECRET" ]]; then
    WEBHOOK_JSON="\"$WEBHOOK_SECRET\""
fi

PAYLOAD=$(cat <<EOF
{
  "app_id": $APP_ID,
  "app_name": "$APP_NAME",
  "private_key": "$PRIVATE_KEY",
  "webhook_secret": $WEBHOOK_JSON
}
EOF
)

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_URL/github-app" \
    -H "Content-Type: application/json" \
    "${AUTH_ARGS[@]}" \
    -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" -lt 200 || "$HTTP_CODE" -ge 300 ]]; then
    echo "Error: POST /github-app returned HTTP $HTTP_CODE"
    echo "$BODY"
    exit 1
fi

DB_ID=$(json_get "$BODY" "id")
echo "    Registered! DB ID: $DB_ID"
echo ""

# --- Step 2: Register installation ---
echo "==> Now register the GitHub App installation."
echo "    (Find installation ID at: https://github.com/organizations/<org>/settings/installations)"
echo ""

read -rp "Installation ID: " INSTALL_ID
read -rp "Account login (org/user name, e.g. sahayakan): " ACCOUNT_LOGIN
read -rp "Account type [Organization]: " ACCOUNT_TYPE
ACCOUNT_TYPE="${ACCOUNT_TYPE:-Organization}"

echo ""
echo "==> Registering installation $INSTALL_ID for $ACCOUNT_LOGIN..."

INST_PAYLOAD=$(cat <<EOF
{
  "installation_id": $INSTALL_ID,
  "account_login": "$ACCOUNT_LOGIN",
  "account_type": "$ACCOUNT_TYPE"
}
EOF
)

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_URL/github-app/$DB_ID/installations" \
    -H "Content-Type: application/json" \
    "${AUTH_ARGS[@]}" \
    -d "$INST_PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" -lt 200 || "$HTTP_CODE" -ge 300 ]]; then
    echo "Error: POST /github-app/$DB_ID/installations returned HTTP $HTTP_CODE"
    echo "$BODY"
    exit 1
fi

INST_DB_ID=$(json_get "$BODY" "id")
echo "    Installation registered! DB ID: $INST_DB_ID"
echo ""

# --- Step 3: Test credentials ---
echo "==> Testing GitHub App credentials..."

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_URL/github-app/$DB_ID/test" \
    "${AUTH_ARGS[@]}")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" -lt 200 || "$HTTP_CODE" -ge 300 ]]; then
    echo "Error: POST /github-app/$DB_ID/test returned HTTP $HTTP_CODE"
    echo "$BODY"
    exit 1
fi

STATUS=$(json_get "$BODY" "status")
SLUG=$(json_get "$BODY" "app_slug")

echo "    Status: $STATUS"
echo "    App slug: $SLUG"
echo ""
echo "==> GitHub App registration complete!"
