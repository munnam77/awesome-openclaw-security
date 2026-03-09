# Gateway Hardening Guide

The OpenClaw WebSocket gateway is the primary attack surface. CVE-2026-25253 (CVSS 8.8) demonstrated that a compromised gateway enables full remote code execution. This guide covers every hardening step.

---

## Table of Contents

- [Bind Address](#bind-address)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Session Timeouts](#session-timeouts)
- [Disable Unused Endpoints](#disable-unused-endpoints)
- [TLS Configuration](#tls-configuration)
- [Connection Limits](#connection-limits)
- [Verification](#verification)

---

## Bind Address

**Risk**: By default, OpenClaw binds the gateway to `0.0.0.0:8765`, making it accessible from any network interface. This is the #1 reason 30,000+ instances are exposed on the internet.

**Fix**: Bind to localhost only.

Edit `config/gateway.yml`:

```yaml
# BEFORE (dangerous default)
gateway:
  host: "0.0.0.0"
  port: 8765

# AFTER (localhost only)
gateway:
  host: "127.0.0.1"
  port: 8765
```

If using environment variables:

```bash
OPENCLAW_GATEWAY_HOST=127.0.0.1
OPENCLAW_GATEWAY_PORT=8765
```

If using Docker, do NOT use `--network host`. Instead, map the port explicitly:

```bash
# WRONG: exposes to all interfaces
docker run --network host openclaw/openclaw

# RIGHT: bind to localhost only
docker run -p 127.0.0.1:8765:8765 openclaw/openclaw
```

**Verify**: After restarting, confirm the bind address:

```bash
ss -tlnp | grep 8765
# Should show 127.0.0.1:8765, NOT 0.0.0.0:8765 or :::8765
```

---

## Authentication

**Risk**: The default gateway has no authentication. Anyone who can reach the port can connect and execute skills.

**Fix**: Enable token-based authentication.

Edit `config/gateway.yml`:

```yaml
gateway:
  auth:
    enabled: true
    method: "token"
    # Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
    token: "${OPENCLAW_AUTH_TOKEN}"
    # Reject connections without valid token
    reject_unauthenticated: true
```

Generate a strong token:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: k7Bx9Qm2Ld4Fp1Rn8Ht5Wv3Yj6Cs0Az
```

Store the token securely (see [Credential Management](credential-management.md)):

```bash
# Using Docker secrets (recommended)
echo "k7Bx9Qm2Ld4Fp1Rn8Ht5Wv3Yj6Cs0Az" | docker secret create openclaw_auth_token -

# Or using a secrets file (chmod 600)
echo "k7Bx9Qm2Ld4Fp1Rn8Ht5Wv3Yj6Cs0Az" > /etc/openclaw/auth_token
chmod 600 /etc/openclaw/auth_token
```

Client connection with token:

```python
import websockets

async def connect():
    uri = "ws://127.0.0.1:8765"
    headers = {"Authorization": "Bearer k7Bx9Qm2Ld4Fp1Rn8Ht5Wv3Yj6Cs0Az"}
    async with websockets.connect(uri, extra_headers=headers) as ws:
        await ws.send('{"action": "ping"}')
```

---

## Rate Limiting

**Risk**: Without rate limiting, an attacker can brute-force tokens, flood the gateway with requests, or cause denial of service.

**Fix**: Configure per-IP rate limits.

Edit `config/gateway.yml`:

```yaml
gateway:
  rate_limit:
    enabled: true
    # Maximum requests per minute per IP
    requests_per_minute: 60
    # Maximum new connections per minute per IP
    connections_per_minute: 10
    # Burst allowance (short spikes above limit)
    burst: 20
    # Ban duration for IPs exceeding limits (seconds)
    ban_duration: 300
```

If using nginx as a reverse proxy (recommended), configure rate limiting there as well:

```nginx
# In http block
limit_req_zone $binary_remote_addr zone=openclaw:10m rate=60r/m;

# In server/location block
location /ws {
    limit_req zone=openclaw burst=20 nodelay;
    proxy_pass http://127.0.0.1:8765;
}
```

See [nginx-proxy.conf](../configs/nginx-proxy.conf) for a complete configuration.

---

## Session Timeouts

**Risk**: Indefinite sessions allow abandoned connections to be hijacked, especially in shared environments.

**Fix**: Configure idle and absolute timeouts.

```yaml
gateway:
  sessions:
    # Close idle connections after 30 minutes
    idle_timeout: 1800
    # Force reconnection after 8 hours regardless of activity
    absolute_timeout: 28800
    # Ping interval to detect dead connections (seconds)
    ping_interval: 30
    # Close connection if no pong received within (seconds)
    pong_timeout: 10
```

---

## Disable Unused Endpoints

**Risk**: OpenClaw exposes several API endpoints by default. Each enabled endpoint is an attack surface.

**Fix**: Disable everything you don't use.

```yaml
gateway:
  endpoints:
    # Core functionality (usually keep enabled)
    skill_execute: true
    conversation: true

    # Management endpoints (disable in production)
    skill_install: false      # Install skills via gateway
    skill_uninstall: false    # Uninstall skills via gateway
    config_read: false        # Read configuration
    config_write: false       # Modify configuration
    debug: false              # Debug information
    metrics: false            # Internal metrics (expose via separate monitoring if needed)
    health: true              # Keep for load balancer health checks
```

If you need management endpoints, restrict them to a separate port bound to localhost:

```yaml
gateway:
  management:
    enabled: true
    host: "127.0.0.1"
    port: 8766
    auth:
      enabled: true
      method: "token"
      token: "${OPENCLAW_ADMIN_TOKEN}"
```

---

## TLS Configuration

**Risk**: Unencrypted WebSocket connections (`ws://`) expose tokens and data in transit.

**Fix**: Enable TLS (`wss://`) on the gateway or terminate TLS at the reverse proxy.

### Option A: TLS at gateway (simpler, fewer components)

```yaml
gateway:
  tls:
    enabled: true
    cert_path: "/etc/openclaw/tls/cert.pem"
    key_path: "/etc/openclaw/tls/key.pem"
    # Minimum TLS version
    min_version: "TLSv1.2"
```

### Option B: TLS at reverse proxy (recommended for production)

Terminate TLS at nginx and proxy to the gateway over localhost:

```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    location /ws {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Connection Limits

**Risk**: Unlimited concurrent connections enable resource exhaustion attacks.

**Fix**: Set per-IP and global connection limits.

```yaml
gateway:
  connections:
    # Maximum concurrent connections total
    max_total: 100
    # Maximum concurrent connections per IP
    max_per_ip: 5
    # Maximum pending (unauthed) connections
    max_pending: 20
    # Timeout for completing authentication handshake (seconds)
    auth_timeout: 10
```

---

## Verification

After applying all changes, verify your hardening:

```bash
# 1. Check bind address
ss -tlnp | grep 8765
# Expected: 127.0.0.1:8765

# 2. Test unauthenticated connection (should be rejected)
python3 -c "
import asyncio, websockets
async def test():
    try:
        async with websockets.connect('ws://127.0.0.1:8765') as ws:
            print('FAIL: Connected without authentication')
    except Exception as e:
        print(f'PASS: Connection rejected ({e})')
asyncio.run(test())
"

# 3. Test from external interface (should fail to connect)
curl -s --connect-timeout 3 http://YOUR_PUBLIC_IP:8765 && echo "FAIL: Port accessible externally" || echo "PASS: Port not accessible externally"

# 4. Run the security scanner
python3 scanner/scan.py --demo
```

---

**Next**: [Skill Vetting Guide](skill-vetting.md) | [Back to README](../README.md)
