# GitHub App Integration

Sahayakan uses GitHub App authentication for all GitHub connectivity. GitHub Apps provide fine-grained permissions, short-lived auto-refreshing tokens, and built-in webhook support.

## Creating a GitHub App

### For an Organization

Go to `https://github.com/organizations/<YOUR_ORG>/settings/apps/new`

### For a Personal Account

Go to [GitHub Settings > Developer settings > GitHub Apps > New GitHub App](https://github.com/settings/apps/new)

### Basic Settings

| Field | Value |
|-------|-------|
| **GitHub App name** | e.g., `sahayakan` |
| **Homepage URL** | Your Sahayakan instance URL (e.g., `https://ai.helm-team.org`) |
| **Description** | Optional (e.g., "Autonomous agentic AI platform for software teams") |

### Webhook Configuration

| Field | Value |
|-------|-------|
| **Active** | Yes (checked) |
| **Webhook URL** | `https://<your-domain>/api/webhooks/github` |
| **Webhook secret** | Generate with `openssl rand -hex 32` — save this value |

### Permissions

Set the following **Repository permissions**:

| Permission | Access |
|-----------|--------|
| **Issues** | Read & Write |
| **Pull requests** | Read & Write |
| **Contents** | Read-only |
| **Metadata** | Read-only (auto-selected) |

No Account or Organization permissions are needed.

### Subscribe to Events

Check these boxes:

- **Issues** — triggers on issue open, edit, close, label, etc.
- **Pull request** — triggers on PR open, edit, synchronize, close, etc.
- **Issue comment** — triggers on new comments on issues and PRs

### Other Settings

| Setting | Value |
|---------|-------|
| **Expire user authorization tokens** | Leave unchecked (not used) |
| **Request user authorization (OAuth) during installation** | Leave unchecked (not used) |
| **Enable Device Flow** | Leave unchecked (not used) |
| **Callback URL** | Leave blank (not used) |
| **Enable SSL verification** | Yes (select this if your server has a valid TLS certificate) |
| **Where can this app be installed?** | "Only on this account" (recommended) or "Any account" |

Click **Create GitHub App**.

## Generating a Private Key

After creating the app:

1. On the app settings page, scroll to **Private keys**
2. Click **Generate a private key**
3. A `.pem` file will download automatically — keep this file secure
4. Note the **App ID** shown at the top of the settings page

## Installing the App

1. On the app settings page, click **Install App** in the left sidebar
2. Choose the organization or account to install on
3. Select **All repositories** or choose specific repositories
4. Click **Install**

!!! success "Auto-Registration & Repository Discovery"
    When someone installs the app, Sahayakan **automatically registers the installation** via webhook and **discovers all accessible repositories**. No manual step is needed — the installation, account details, and repositories are recorded automatically.

    The webhook also handles **uninstalls** (soft-deletes the installation), **suspends**/**unsuspends** (toggles active status), and **repository changes** (adds/removes repos when the installation's repository access is modified).

    You can manually re-discover repositories at any time via the API:

    ```bash
    curl -X POST https://<your-domain>/api/github-app/{app_id}/installations/{inst_id}/discover \
      -u "<basic-auth-user>:<basic-auth-pass>"
    ```

If auto-registration is not available (e.g., webhooks are not configured), you can register installations manually — see below.

## Registering in Sahayakan

### Automatic (via Webhook)

If webhooks are configured, installations are registered automatically when users install the app. You only need to register the **GitHub App credentials** (App ID, private key, webhook secret) — installations are handled by the webhook.

### Via CLI (Manual)

Use the registration script with the values from the steps above:

```bash
bash cli/register_github_app.sh \
  --app-id <APP_ID> \
  --app-name "<APP_NAME>" \
  --private-key-file /path/to/private-key.pem \
  --webhook-secret "<WEBHOOK_SECRET>" \
  --api-url "https://<your-domain>/api"
```

The script will:

1. Register the app credentials via `POST /github-app`
2. Prompt for installation details (installation ID, account login, account type)
3. Test the credentials via `POST /github-app/{id}/test`

Run `bash cli/register_github_app.sh --help` for all options.

### Via Web Dashboard

1. Go to **Settings > GitHub Integration**
2. Click **Add GitHub App**
3. Fill in:
   - **App ID** — From the app settings page
   - **App Name** — Display name
   - **Private Key** — Paste the entire contents of the `.pem` file
   - **Webhook Secret** — The secret you generated
4. Click **Save**
5. Click **Add Installation** and enter:
   - **Installation ID** — From the URL after installing the app
   - **Account Login** — The org or user name
   - **Account Type** — `Organization` or `User`
6. Click **Test** to verify the connection

### Via API

```bash
# Register the GitHub App
curl -X POST https://<your-domain>/api/github-app \
  -u "<basic-auth-user>:<basic-auth-pass>" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": 123456,
    "app_name": "sahayakan",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
    "webhook_secret": "your-webhook-secret"
  }'

# Register the installation
curl -X POST https://<your-domain>/api/github-app/1/installations \
  -u "<basic-auth-user>:<basic-auth-pass>" \
  -H "Content-Type: application/json" \
  -d '{
    "installation_id": 12345678,
    "account_login": "myorg",
    "account_type": "Organization"
  }'

# Test the connection
curl -X POST https://<your-domain>/api/github-app/1/test \
  -u "<basic-auth-user>:<basic-auth-pass>"
```

> **Note**: When Caddy basic auth is in front of the API, use `-u user:pass` (basic auth)
> only. Do not also send `Authorization: Bearer` — the explicit header overrides basic auth
> and Caddy will reject it.

## Server Configuration

### Webhook Secret Environment Variable

Set the webhook secret in your server's `.env` file as a fallback:

```
GITHUB_WEBHOOK_SECRET=<your-webhook-secret>
```

The webhook handler checks signatures against all configured secrets: the `GITHUB_WEBHOOK_SECRET` environment variable and any per-app secrets stored in the database.

### Caddy Configuration

The webhook endpoint (`/api/webhooks/*`) must be excluded from Caddy basic auth, since GitHub cannot send basic auth credentials with webhook deliveries. The Caddyfile matcher should look like:

```
@notHealthNotOptionsNotWebhook {
    not path /health
    not path /api/webhooks/*
    not method OPTIONS
}

basicauth @notHealthNotOptionsNotWebhook {
    admin <bcrypt-hash>
}
```

## Webhooks

When configured, GitHub sends events to Sahayakan in real time. The following events are processed:

| GitHub Event | Action | Sahayakan Event |
|-------------|--------|-----------------|
| `issues` | `opened` | `issue.ingested` |
| `issues` | `edited`, `labeled` | `issue.updated` |
| `pull_request` | `opened` | `pr.ingested` |
| `pull_request` | `synchronize`, `edited` | `pr.updated` |
| `issue_comment` | `created` | `issue.commented` |
| `installation` | `created` | Auto-registers installation + discovers repos |
| `installation` | `deleted` | Soft-deletes installation |
| `installation` | `suspend` | Deactivates installation |
| `installation` | `unsuspend` | Reactivates installation |
| `installation_repositories` | `added` | Discovers newly added repos |
| `installation_repositories` | `removed` | Deactivates removed repos |

### Webhook Flow

1. GitHub sends a POST request to the webhook URL
2. Caddy passes the request through (webhook paths skip basic auth)
3. The API auth middleware passes the request through (webhook routes are excluded)
4. The webhook handler verifies the HMAC-SHA256 signature against all configured secrets
5. Valid events are published to the `events` table for agent processing

### Monitoring Webhook Delivery

Check webhook delivery status in GitHub:

- **Organization app**: `https://github.com/organizations/<org>/settings/apps/<app-name>/advanced`
- **Personal app**: `https://github.com/settings/apps/<app-name>/advanced`

The "Recent Deliveries" section shows each webhook payload, response status, and timing. You can redeliver failed webhooks from this page.

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Webhook shows 401 in GitHub | Caddy basic auth blocking | Exclude `/api/webhooks/*` from basic auth in Caddyfile |
| Webhook shows 401 in API logs | Signature mismatch | Verify `GITHUB_WEBHOOK_SECRET` matches the secret configured in GitHub |
| Webhook shows 502 | API server not running | Check `docker compose logs api-server` |
| No delivery attempts | Webhook not active or wrong URL | Check app settings in GitHub |
