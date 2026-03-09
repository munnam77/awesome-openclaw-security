# Network Isolation Guide

30,000+ OpenClaw instances were discovered exposed to the internet without authentication. This guide ensures your instance is never one of them.

---

## Table of Contents

- [Principle: Zero Open Ports](#principle-zero-open-ports)
- [UFW Firewall Rules](#ufw-firewall-rules)
- [iptables Rules](#iptables-rules)
- [Cloudflare Tunnel (Zero Open Ports)](#cloudflare-tunnel-zero-open-ports)
- [VPN-Only Access](#vpn-only-access)
- [Reverse Proxy with nginx](#reverse-proxy-with-nginx)
- [DNS-Level Blocking](#dns-level-blocking)
- [Outbound Connection Monitoring](#outbound-connection-monitoring)

---

## Principle: Zero Open Ports

The safest OpenClaw deployment exposes **zero** ports to the internet:

```
Internet -> Cloudflare Tunnel (outbound-only) -> nginx (localhost) -> OpenClaw (localhost)
```

No inbound firewall rules needed. No ports to scan. No attack surface.

If you must expose ports, use VPN + firewall rules to restrict access to known IPs only.

---

## UFW Firewall Rules

If your server uses UFW (Ubuntu/Debian):

```bash
# Reset to clean state (careful: disconnects SSH if you don't allow it first)
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (adjust port if non-standard)
sudo ufw allow 22/tcp

# Allow HTTPS (only if running reverse proxy on this server)
sudo ufw allow 443/tcp

# DO NOT allow the OpenClaw gateway port directly
# sudo ufw allow 8765  <-- NEVER DO THIS

# Enable firewall
sudo ufw enable

# Verify
sudo ufw status verbose
```

**Expected output**:

```
Status: active
Default: deny (incoming), allow (outgoing)

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
```

Notice: port 8765 is NOT listed. The gateway is only accessible via localhost.

---

## iptables Rules

For servers without UFW:

```bash
# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow loopback (required for localhost communication)
iptables -A INPUT -i lo -j ACCEPT

# Allow SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTPS
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Drop everything else
iptables -A INPUT -j DROP

# Block OpenClaw gateway from non-localhost
iptables -A INPUT -p tcp --dport 8765 ! -s 127.0.0.1 -j DROP

# Save rules (Debian/Ubuntu)
iptables-save > /etc/iptables/rules.v4
```

---

## Cloudflare Tunnel (Zero Open Ports)

The recommended approach for remote access. No ports need to be opened on your server.

### Setup

1. Install cloudflared:

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
```

2. Authenticate and create tunnel:

```bash
cloudflared tunnel login
cloudflared tunnel create openclaw-secure
```

3. Configure the tunnel (`~/.cloudflared/config.yml`):

```yaml
tunnel: openclaw-secure
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  # Route WebSocket traffic to OpenClaw gateway
  - hostname: openclaw.yourdomain.com
    service: ws://127.0.0.1:8765
    originRequest:
      noTLSVerify: false
      connectTimeout: 10s
      # Require Cloudflare Access authentication
      access:
        required: true
        teamName: your-team
  # Catch-all
  - service: http_status:404
```

4. Set up Cloudflare Access (authentication layer):

- Go to Cloudflare Zero Trust dashboard
- Create an Access Application for `openclaw.yourdomain.com`
- Configure authentication (email OTP, SSO, etc.)
- Only authorized users can reach the tunnel

5. Run as a system service:

```bash
cloudflared service install
systemctl enable cloudflared
systemctl start cloudflared
```

**Result**: Your OpenClaw instance is accessible at `wss://openclaw.yourdomain.com` with Cloudflare Access authentication, and your server has zero open ports (except SSH).

---

## VPN-Only Access

For team environments, restrict OpenClaw access to VPN users only.

### WireGuard setup

1. Install WireGuard:

```bash
sudo apt install wireguard
```

2. Generate server keys:

```bash
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
chmod 600 /etc/wireguard/server_private.key
```

3. Configure server (`/etc/wireguard/wg0.conf`):

```ini
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <server_private_key>

# Forward OpenClaw traffic only within VPN
PostUp = iptables -A FORWARD -i wg0 -o lo -p tcp --dport 8765 -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -o lo -p tcp --dport 8765 -j ACCEPT

[Peer]
# Team member 1
PublicKey = <client_public_key>
AllowedIPs = 10.0.0.2/32
```

4. Configure UFW to allow WireGuard + restrict OpenClaw to VPN:

```bash
sudo ufw allow 51820/udp
# Allow OpenClaw gateway from VPN subnet only
sudo ufw allow from 10.0.0.0/24 to any port 8765 proto tcp
```

---

## Reverse Proxy with nginx

Place nginx between the internet and OpenClaw for rate limiting, security headers, and TLS termination.

### Basic secure configuration

```nginx
# Rate limiting zone
limit_req_zone $binary_remote_addr zone=openclaw_api:10m rate=30r/m;
limit_conn_zone $binary_remote_addr zone=openclaw_conn:10m;

server {
    listen 443 ssl http2;
    server_name openclaw.yourdomain.com;

    # TLS
    ssl_certificate /etc/letsencrypt/live/openclaw.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/openclaw.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Request limits
    client_max_body_size 1m;
    client_body_timeout 10s;
    client_header_timeout 10s;

    # WebSocket proxy to OpenClaw
    location /ws {
        limit_req zone=openclaw_api burst=10 nodelay;
        limit_conn openclaw_conn 5;

        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Block everything else
    location / {
        return 444;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name openclaw.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

See [configs/nginx-proxy.conf](../configs/nginx-proxy.conf) for the complete configuration with IP allowlisting.

---

## DNS-Level Blocking

Block skills from communicating with known malicious domains.

### Using /etc/hosts (simple)

```bash
# Add known malicious C2 domains
echo "0.0.0.0 evil-c2-server.example.com" >> /etc/hosts
echo "0.0.0.0 crypto-pool.example.net" >> /etc/hosts
```

### Using Pi-hole or AdGuard Home

Run a local DNS server that blocks malicious domains:

```yaml
# Add to docker-compose.yml
services:
  adguard:
    image: adguard/adguardhome:latest
    ports:
      - "127.0.0.1:53:53/udp"
      - "127.0.0.1:3000:3000"
    volumes:
      - adguard-data:/opt/adguardhome/work
      - adguard-conf:/opt/adguardhome/conf
```

Configure OpenClaw's container to use this DNS:

```yaml
services:
  openclaw:
    dns:
      - 127.0.0.1
```

### Using iptables for outbound blocking

Block all outbound connections from the OpenClaw container except to specific IPs:

```bash
# Get OpenClaw container IP
CONTAINER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' openclaw-app)

# Allow outbound to specific APIs only
iptables -A FORWARD -s $CONTAINER_IP -d api.openweathermap.org -j ACCEPT
iptables -A FORWARD -s $CONTAINER_IP -d api.github.com -j ACCEPT

# Block all other outbound from container
iptables -A FORWARD -s $CONTAINER_IP -j DROP
```

---

## Outbound Connection Monitoring

Monitor what your OpenClaw instance is connecting to.

### Using ss/netstat

```bash
# Show all connections from the OpenClaw container
docker exec openclaw-app ss -tnp

# Watch in real-time
watch -n 5 "docker exec openclaw-app ss -tnp"
```

### Using tcpdump

```bash
# Capture all traffic from the OpenClaw container network
tcpdump -i docker0 -n -w /tmp/openclaw-traffic.pcap

# Filter for suspicious ports
tcpdump -i docker0 -n 'dst port 4444 or dst port 5555 or dst port 1337'
```

### Using conntrack

```bash
# List all tracked connections
conntrack -L -s $CONTAINER_IP
```

Set up alerts for unexpected outbound connections:

```bash
#!/bin/bash
# /opt/openclaw/monitor-connections.sh
# Run via cron every 5 minutes

ALLOWED_DOMAINS="api.openweathermap.org api.github.com"
CONNECTIONS=$(docker exec openclaw-app ss -tnp | grep ESTAB | awk '{print $5}' | cut -d: -f1)

for ip in $CONNECTIONS; do
    domain=$(dig +short -x $ip | head -1)
    if ! echo "$ALLOWED_DOMAINS" | grep -q "$domain"; then
        echo "ALERT: Unexpected outbound connection to $ip ($domain)" | mail -s "OpenClaw Security Alert" admin@yourdomain.com
    fi
done
```

---

**Next**: [Credential Management](credential-management.md) | **Previous**: [Secure Docker Deployment](docker-secure-deploy.md) | [Back to README](../README.md)
