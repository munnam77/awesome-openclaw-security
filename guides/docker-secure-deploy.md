# Secure Docker Deployment Guide

Running OpenClaw in Docker is the recommended approach -- containers provide isolation, resource limits, and reproducibility. But Docker's defaults are permissive. This guide hardens every aspect.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Non-Root User](#non-root-user)
- [Read-Only Filesystem](#read-only-filesystem)
- [Network Isolation](#network-isolation)
- [Resource Limits](#resource-limits)
- [Volume Mount Security](#volume-mount-security)
- [Capability Dropping](#capability-dropping)
- [Health Checks](#health-checks)
- [Image Security](#image-security)
- [Complete Docker Compose](#complete-docker-compose)

---

## Quick Start

Use the provided secure Docker Compose file:

```bash
cp configs/docker-compose.secure.yml docker-compose.yml
cp configs/.env.example .env
# Edit .env with your values
docker compose up -d
```

---

## Non-Root User

**Why**: Running as root inside a container means a container escape gives the attacker root on the host.

**Fix**: Create a dedicated user in the Dockerfile or specify the user in Compose.

### In Docker Compose (easiest)

```yaml
services:
  openclaw:
    image: openclaw/openclaw:0.4.7
    user: "1001:1001"
```

### In a custom Dockerfile

```dockerfile
FROM openclaw/openclaw:0.4.7

# Create non-root user
RUN groupadd -g 1001 openclaw && \
    useradd -r -u 1001 -g openclaw openclaw && \
    chown -R openclaw:openclaw /app

USER openclaw
```

**Verify**:

```bash
docker exec openclaw-app whoami
# Should output: openclaw (or the UID like "1001")
# Should NOT output: root
```

---

## Read-Only Filesystem

**Why**: Prevents malicious skills from writing to the container filesystem, planting backdoors, or modifying application code.

```yaml
services:
  openclaw:
    read_only: true
    tmpfs:
      # Writable temp directory (size-limited, not persisted)
      - /tmp:size=64M,mode=1777
      - /app/tmp:size=32M,mode=1777
    volumes:
      # Only specific directories get write access
      - openclaw-data:/app/data
      - openclaw-logs:/app/logs
```

**Key principle**: Default deny (read-only), then allow specific writable paths via volumes and tmpfs.

---

## Network Isolation

**Why**: Prevents container-to-container attacks and limits blast radius of a compromised skill.

```yaml
services:
  openclaw:
    networks:
      - openclaw-internal
    # NEVER use this:
    # network_mode: host

  nginx:
    networks:
      - openclaw-internal
      - web-external
    ports:
      - "443:443"

networks:
  openclaw-internal:
    driver: bridge
    internal: true  # No outbound internet access
  web-external:
    driver: bridge
```

**Architecture**:

```
Internet -> nginx (web-external) -> openclaw (openclaw-internal)
                                         |
                                    No internet access
```

If a skill needs outbound internet (e.g., weather API), create a separate network with restricted egress:

```yaml
networks:
  skill-egress:
    driver: bridge
    # Use firewall rules to restrict to specific IPs/domains
```

---

## Resource Limits

**Why**: Prevents crypto miners, fork bombs, and denial-of-service from consuming all host resources.

```yaml
services:
  openclaw:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M
    # Also set these for Docker Compose v2 compatibility
    mem_limit: 512m
    memswap_limit: 512m  # Prevent swap usage
    cpu_quota: 100000     # Microseconds per cpu-period
    pids_limit: 100       # Prevent fork bombs
```

**Tuning**: Monitor actual usage for a week, then set limits at 2x observed peak:

```bash
docker stats openclaw-app --no-stream
```

---

## Volume Mount Security

**Why**: Overly permissive volume mounts can expose the host filesystem to the container.

### Rules

1. **Never mount `/` or `/home`** into a container
2. **Use named volumes** instead of bind mounts where possible
3. **Mount as read-only** unless writes are required
4. **Restrict bind mount paths** to the minimum needed

```yaml
services:
  openclaw:
    volumes:
      # Named volumes (Docker manages location)
      - openclaw-data:/app/data
      - openclaw-logs:/app/logs

      # Config file (read-only bind mount)
      - ./config/gateway.yml:/app/config/gateway.yml:ro

      # Skills directory (read-only -- install via management interface)
      - ./skills:/app/skills:ro

      # NEVER do this:
      # - /:/host  # Exposes entire host filesystem
      # - /var/run/docker.sock:/var/run/docker.sock  # Docker socket = root access
      # - ~/.ssh:/root/.ssh  # SSH keys
```

---

## Capability Dropping

**Why**: Linux capabilities give fine-grained permissions. Docker containers get a subset by default, but even that is too much for OpenClaw.

```yaml
services:
  openclaw:
    cap_drop:
      - ALL
    cap_add:
      # Only add back what's actually needed
      - NET_BIND_SERVICE  # If binding to ports < 1024
    security_opt:
      - no-new-privileges:true
```

The `no-new-privileges` flag prevents processes inside the container from gaining additional privileges via setuid binaries or similar mechanisms.

---

## Health Checks

**Why**: Detect when the gateway becomes unresponsive so Docker can restart it automatically.

```yaml
services:
  openclaw:
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    restart: unless-stopped
```

---

## Image Security

### Pin image versions

```yaml
# WRONG: mutable tag, could be replaced with malicious image
image: openclaw/openclaw:latest

# RIGHT: specific version
image: openclaw/openclaw:0.4.7

# BEST: pin by digest (immutable)
image: openclaw/openclaw@sha256:abc123...
```

### Scan images before deployment

```bash
# Using Docker Scout
docker scout cves openclaw/openclaw:0.4.7

# Using Trivy
trivy image openclaw/openclaw:0.4.7

# Using Grype
grype openclaw/openclaw:0.4.7
```

---

## Complete Docker Compose

See [configs/docker-compose.secure.yml](../configs/docker-compose.secure.yml) for the full production-ready configuration.

Key properties of the secure compose file:
- Non-root user (UID 1001)
- Read-only root filesystem with tmpfs for writable paths
- Internal-only network (no direct internet access)
- CPU and memory limits
- All capabilities dropped
- Health checks with auto-restart
- Secrets managed via Docker secrets
- Named volumes for persistent data
- Pinned image versions

---

**Next**: [Network Isolation](network-isolation.md) | **Previous**: [Skill Vetting](skill-vetting.md) | [Back to README](../README.md)
