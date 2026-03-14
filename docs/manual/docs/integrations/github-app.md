# GitHub App Integration

Sahayakan uses GitHub App authentication for all GitHub connectivity. GitHub Apps provide fine-grained permissions, short-lived auto-refreshing tokens, and built-in webhook support.

## Creating a GitHub App

1. Go to **[GitHub Settings > Developer settings > GitHub Apps > New GitHub App](https://github.com/settings/apps/new)**

2. Configure the app:

    | Field | Value |
    |-------|-------|
    | **App name** | e.g., `Sahayakan` |
    | **Homepage URL** | Your Sahayakan instance URL |
    | **Webhook URL** | `https://your-domain.com/api/webhooks/github` |
    | **Webhook secret** | Generate with `openssl rand -hex 20` |

3. Set **Repository permissions**:

    | Permission | Access |
    |-----------|--------|
    | Issues | Read & Write |
    | Pull requests | Read & Write |
    | Contents | Read |
    | Metadata | Read |

4. Click **Create GitHub App**

## Generating a Private Key

1. On the app settings page, scroll to **Private keys**
2. Click **Generate a private key**
3. A `.pem` file will download — keep this secure

## Installing the App

1. On the app settings page, click **Install App**
2. Choose the organization or account
3. Select which repositories to grant access to
4. Note the **installation ID** from the URL after installation (e.g., `https://github.com/settings/installations/12345678` → ID is `12345678`)

## Configuring in Sahayakan

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
# Add GitHub App
curl -X POST http://localhost:8000/github-app \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": 123456,
    "app_name": "Sahayakan",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
    "webhook_secret": "your-webhook-secret"
  }'

# Add installation
curl -X POST http://localhost:8000/github-app/1/installations \
  -H "Content-Type: application/json" \
  -d '{
    "installation_id": 12345678,
    "account_login": "myorg",
    "account_type": "Organization"
  }'

# Test connection
curl -X POST http://localhost:8000/github-app/1/test
```

## Webhooks

When configured with a webhook URL, GitHub sends events to Sahayakan automatically:

- **issues.opened** — Can trigger Issue Triage agent
- **pull_request.opened** — Can trigger PR Context agent
- **push** — General repository events

The webhook secret is verified on every incoming request for security.

Set `GITHUB_WEBHOOK_SECRET` in your environment for the shared webhook secret, or configure per-app secrets via the Settings UI.
