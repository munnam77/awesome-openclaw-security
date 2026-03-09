# Credential Management Guide

CVE-2026-22847 demonstrated that OpenClaw leaks credentials through skill error messages. Beyond patching, you need a defense-in-depth approach to credential storage, access, and rotation.

---

## Table of Contents

- [The Problem with Environment Variables](#the-problem-with-environment-variables)
- [Docker Secrets](#docker-secrets)
- [HashiCorp Vault Integration](#hashicorp-vault-integration)
- [Rotating API Keys](#rotating-api-keys)
- [Per-Skill Credential Isolation](#per-skill-credential-isolation)
- [Audit Trails](#audit-trails)
- [Emergency Credential Rotation](#emergency-credential-rotation)

---

## The Problem with Environment Variables

Environment variables are the most common way to pass credentials to containers. They are also the least secure:

1. **Visible in process listings**: `cat /proc/1/environ` shows all env vars
2. **Logged in crash dumps**: Application crashes often dump the full environment
3. **Leaked in error messages**: CVE-2026-22847 exploits this
4. **Visible in Docker inspect**: `docker inspect container_name` shows all env vars
5. **Inherited by child processes**: Malicious skills executed as subprocesses inherit all env vars
6. **Stored in shell history**: `docker run -e API_KEY=secret ...` is in your `.bash_history`

**Rule**: Never store credentials in environment variables or plain text files in production.

---

## Docker Secrets

Docker secrets are the simplest upgrade from environment variables. Secrets are mounted as files inside the container and are only available to services that explicitly request them.

### Creating secrets

```bash
# From a string
echo "your-api-key-here" | docker secret create openclaw_api_key -

# From a file
docker secret create openclaw_api_key ./api-key.txt
rm ./api-key.txt  # Delete the source file

# Generate a random token
python3 -c "import secrets; print(secrets.token_urlsafe(32))" | docker secret create openclaw_auth_token -
```

### Using secrets in Docker Compose

```yaml
version: "3.8"

services:
  openclaw:
    image: openclaw/openclaw:0.4.7
    secrets:
      - openclaw_api_key
      - openclaw_auth_token
      - openclaw_db_password
    environment:
      # Point to secret files instead of embedding values
      OPENCLAW_API_KEY_FILE: /run/secrets/openclaw_api_key
      OPENCLAW_AUTH_TOKEN_FILE: /run/secrets/openclaw_auth_token
      DB_PASSWORD_FILE: /run/secrets/openclaw_db_password

secrets:
  openclaw_api_key:
    external: true
  openclaw_auth_token:
    external: true
  openclaw_db_password:
    external: true
```

### Reading secrets in application code

Most applications need modification to read from files instead of environment variables:

```python
import os

def get_secret(name):
    """Read a Docker secret, falling back to environment variable."""
    secret_file = os.environ.get(f"{name}_FILE")
    if secret_file and os.path.exists(secret_file):
        with open(secret_file, 'r') as f:
            return f.read().strip()
    return os.environ.get(name)

api_key = get_secret("OPENCLAW_API_KEY")
```

### File-based secrets (non-Swarm alternative)

If you are not using Docker Swarm, use file-based secrets:

```yaml
services:
  openclaw:
    volumes:
      - ./secrets:/run/secrets:ro
    environment:
      OPENCLAW_API_KEY_FILE: /run/secrets/openclaw_api_key
```

```bash
# Create secrets directory with strict permissions
mkdir -p ./secrets
chmod 700 ./secrets

# Create secret files
echo "your-api-key" > ./secrets/openclaw_api_key
chmod 600 ./secrets/openclaw_api_key
```

---

## HashiCorp Vault Integration

For production environments with multiple services and credential rotation requirements.

### Setup

1. Deploy Vault (using Docker for simplicity):

```yaml
services:
  vault:
    image: hashicorp/vault:1.15
    cap_add:
      - IPC_LOCK
    ports:
      - "127.0.0.1:8200:8200"
    volumes:
      - vault-data:/vault/data
    environment:
      VAULT_ADDR: "http://127.0.0.1:8200"
```

2. Initialize and unseal:

```bash
docker exec -it vault vault operator init -key-shares=3 -key-threshold=2
# Save the unseal keys and root token securely (offline, not in a file)

docker exec -it vault vault operator unseal <key1>
docker exec -it vault vault operator unseal <key2>
```

3. Store OpenClaw credentials:

```bash
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=<root_token>

# Enable KV secrets engine
vault secrets enable -path=openclaw kv-v2

# Store credentials
vault kv put openclaw/gateway \
    auth_token="your-gateway-auth-token" \
    admin_token="your-admin-token"

vault kv put openclaw/skills/weather \
    api_key="your-openweathermap-key"

vault kv put openclaw/database \
    host="127.0.0.1" \
    port="5432" \
    username="openclaw" \
    password="strong-db-password"
```

4. Create a policy for OpenClaw:

```hcl
# openclaw-policy.hcl
path "openclaw/data/gateway" {
  capabilities = ["read"]
}

path "openclaw/data/skills/*" {
  capabilities = ["read"]
}

path "openclaw/data/database" {
  capabilities = ["read"]
}
```

```bash
vault policy write openclaw openclaw-policy.hcl
vault token create -policy=openclaw -period=24h
```

### Retrieving credentials at startup

Create a startup script that fetches credentials from Vault:

```bash
#!/bin/bash
# /opt/openclaw/start.sh

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"

# Fetch gateway credentials
GATEWAY_CREDS=$(curl -s -H "X-Vault-Token: ${VAULT_TOKEN}" \
    "${VAULT_ADDR}/v1/openclaw/data/gateway" | python3 -c "
import sys, json
data = json.load(sys.stdin)['data']['data']
for k, v in data.items():
    print(f'{k}={v}')
")

# Write to temporary secrets directory (tmpfs)
echo "$GATEWAY_CREDS" > /tmp/secrets/gateway.env

# Start OpenClaw
exec /app/openclaw --config /app/config/gateway.yml
```

---

## Rotating API Keys

Regular rotation limits the window of exposure if a key is compromised.

### Rotation schedule

| Credential Type | Rotation Frequency | Method |
|----------------|-------------------|--------|
| Gateway auth tokens | Every 90 days | Generate new token, update clients, revoke old |
| Skill API keys | Every 90 days | Re-provision from provider |
| Database passwords | Every 180 days | ALTER USER in database |
| TLS certificates | Before expiry (Let's Encrypt auto-renews) | certbot renew |

### Rotation script

```bash
#!/bin/bash
# /opt/openclaw/rotate-keys.sh
# Run via cron: 0 2 1 */3 * (first of every 3rd month at 2am)

set -e

echo "[$(date)] Starting credential rotation..."

# 1. Generate new gateway token
NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. Store in Vault
vault kv put openclaw/gateway auth_token="$NEW_TOKEN"

# 3. Update the running service
docker exec openclaw-app /app/update-token.sh "$NEW_TOKEN"

# 4. Verify the new token works
sleep 5
HEALTH=$(curl -s -H "Authorization: Bearer $NEW_TOKEN" http://127.0.0.1:8765/health)
if echo "$HEALTH" | grep -q "ok"; then
    echo "[$(date)] Rotation successful. New token active."
else
    echo "[$(date)] ROTATION FAILED. Rolling back..."
    # Retrieve previous version from Vault
    OLD_TOKEN=$(vault kv get -version=-1 -field=auth_token openclaw/gateway)
    docker exec openclaw-app /app/update-token.sh "$OLD_TOKEN"
    exit 1
fi

echo "[$(date)] Credential rotation complete."
```

---

## Per-Skill Credential Isolation

Never give all skills access to all credentials. Each skill should only access the credentials it needs.

### Configuration

```yaml
skills:
  weather:
    credentials:
      - name: WEATHER_API_KEY
        source: vault
        path: openclaw/skills/weather
        field: api_key
  calendar:
    credentials:
      - name: GOOGLE_CALENDAR_TOKEN
        source: vault
        path: openclaw/skills/calendar
        field: oauth_token
```

### Vault policies per skill

```hcl
# weather-skill-policy.hcl
path "openclaw/data/skills/weather" {
  capabilities = ["read"]
}
# Cannot access any other credentials
```

```hcl
# calendar-skill-policy.hcl
path "openclaw/data/skills/calendar" {
  capabilities = ["read"]
}
```

---

## Audit Trails

Track who accessed what credentials and when.

### Vault audit logging

```bash
vault audit enable file file_path=/var/log/vault/audit.log
```

Audit log entries include:
- Timestamp
- Client token (hashed)
- Operation (read, write, delete)
- Path accessed
- Source IP

### Monitoring for suspicious access

```bash
# Alert on credential access outside normal hours
grep '"operation":"read"' /var/log/vault/audit.log | \
    python3 -c "
import sys, json
for line in sys.stdin:
    entry = json.loads(line)
    hour = int(entry['time'].split('T')[1].split(':')[0])
    if hour < 6 or hour > 22:
        print(f'ALERT: Off-hours credential access: {entry[\"request\"][\"path\"]} at {entry[\"time\"]}')
"
```

---

## Emergency Credential Rotation

If you suspect a credential has been compromised:

### Immediate actions (within 15 minutes)

```bash
# 1. Revoke the compromised token immediately
vault token revoke <compromised_token>

# 2. Generate and deploy new credentials
NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
vault kv put openclaw/gateway auth_token="$NEW_TOKEN"

# 3. Restart OpenClaw to pick up new credentials
docker restart openclaw-app

# 4. Check for unauthorized access in logs
grep "401\|403\|unauthorized" /var/log/openclaw/access.log | tail -100

# 5. Rotate ALL related credentials (assume lateral movement)
./rotate-keys.sh --all --force
```

### Post-incident

1. Review Vault audit logs for the compromised credential
2. Identify the source of the compromise
3. Patch the vulnerability that allowed the compromise
4. Rotate all credentials that could have been accessed
5. Document the incident and update your security procedures

---

**Previous**: [Network Isolation](network-isolation.md) | [Back to README](../README.md)
