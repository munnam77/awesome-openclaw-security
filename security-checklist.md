# OpenClaw Security Hardening Checklist

> Copy this checklist into your project tracker. Work through each item systematically.
> Items marked with **(CRITICAL)** address known exploited vulnerabilities.

---

## Gateway Security

- [ ] **(CRITICAL)** Change gateway bind address from `0.0.0.0` to `127.0.0.1` ([guide](guides/gateway-hardening.md#bind-address))
- [ ] **(CRITICAL)** Enable authentication tokens on WebSocket gateway ([guide](guides/gateway-hardening.md#authentication))
- [ ] Configure session timeout (recommended: 30 minutes idle) ([guide](guides/gateway-hardening.md#session-timeouts))
- [ ] Enable rate limiting on gateway connections (recommended: 60 req/min per IP) ([guide](guides/gateway-hardening.md#rate-limiting))
- [ ] Disable unused API endpoints ([guide](guides/gateway-hardening.md#disable-unused-endpoints))
- [ ] Enable TLS for all gateway connections
- [ ] Set maximum WebSocket message size (recommended: 1MB)
- [ ] Configure connection limits per IP (recommended: 5 concurrent)

## Skill Security

- [ ] **(CRITICAL)** Audit all installed skills with the scanner before first use ([guide](guides/skill-vetting.md))
- [ ] **(CRITICAL)** Remove any skills flagged as FAIL by the scanner
- [ ] Review WARN-flagged skills manually before keeping them
- [ ] Enable skill sandboxing if available in your OpenClaw version
- [ ] Restrict skill filesystem access to designated directories only
- [ ] Block skill outbound network access unless explicitly required
- [ ] Pin skill versions (disable auto-updates from ClawHub)
- [ ] Maintain a skill allowlist -- only approved skills can be installed
- [ ] Review skill source code for `eval()`, `exec()`, `subprocess` calls
- [ ] Verify skill publisher identity before installation

## Docker & Container Security

- [ ] Run OpenClaw as non-root user (`user: "1001:1001"`) ([guide](guides/docker-secure-deploy.md))
- [ ] Enable read-only root filesystem (`read_only: true`)
- [ ] Set CPU limits (`cpus: '1.0'`) and memory limits (`mem_limit: 512m`)
- [ ] Use Docker network isolation (do not use `network_mode: host`)
- [ ] Drop all Linux capabilities and add back only what's needed
- [ ] Mount volumes as read-only where possible
- [ ] Enable container health checks
- [ ] Use specific image tags (never `latest`)
- [ ] Scan container images for vulnerabilities before deployment

## Network Security

- [ ] **(CRITICAL)** Ensure OpenClaw is NOT directly exposed to the internet ([guide](guides/network-isolation.md))
- [ ] Place OpenClaw behind a reverse proxy (nginx/Caddy) with rate limiting
- [ ] Configure firewall rules (UFW/iptables) to restrict access
- [ ] Use Cloudflare Tunnel or VPN for remote access (no open ports)
- [ ] Enable security headers on reverse proxy (HSTS, CSP, X-Frame-Options)
- [ ] Block outbound connections to known malicious IPs/domains
- [ ] Monitor DNS queries for suspicious outbound resolution
- [ ] Restrict access to management ports (SSH, admin panels)

## Credential Management

- [ ] **(CRITICAL)** Move all credentials out of environment variables and plain text files ([guide](guides/credential-management.md))
- [ ] Store credentials in Docker secrets or HashiCorp Vault
- [ ] Rotate API keys on a regular schedule (recommended: every 90 days)
- [ ] Use separate API keys per skill (not a shared master key)
- [ ] Enable audit logging for all credential access
- [ ] Remove default/example credentials from production deployments
- [ ] Encrypt credentials at rest
- [ ] Implement least-privilege access for service accounts

## Logging & Monitoring

- [ ] Enable access logging on the gateway
- [ ] Enable error logging with sufficient detail (but no credential leakage)
- [ ] Set up log rotation to prevent disk exhaustion
- [ ] Monitor for unusual skill installation or modification
- [ ] Alert on authentication failures (>5 failures in 10 minutes)
- [ ] Alert on unexpected outbound connections from skills
- [ ] Ship logs to a centralized logging system (ELK, Loki, etc.)
- [ ] Review logs weekly for anomalies

## Backup & Recovery

- [ ] Back up OpenClaw configuration files daily
- [ ] Back up skill data and user data regularly
- [ ] Store backups in a separate location (not on the same server)
- [ ] Test backup restoration quarterly
- [ ] Document your recovery procedure
- [ ] Keep a list of all installed skills and their versions for rebuild

## Updates & Patching

- [ ] Subscribe to OpenClaw security advisories
- [ ] Apply security patches within 48 hours of release
- [ ] Test patches in a staging environment before production
- [ ] Review changelogs for security-relevant changes
- [ ] Keep host OS and Docker updated
- [ ] Monitor this repo for new CVEs and pattern updates

---

## How to Use This Checklist

1. **Initial hardening**: Work through every item marked **(CRITICAL)** first
2. **Full hardening**: Complete all remaining items within 7 days
3. **Ongoing maintenance**: Review this checklist monthly
4. **After incidents**: Re-verify all items after any security event

## Automation

Run the scanner as part of your CI/CD pipeline:

```bash
python3 scanner/scan.py --path ./skills/ --json > scan-results.json
# Fail the pipeline if any FAIL results exist
python3 -c "import json,sys; r=json.load(open('scan-results.json')); sys.exit(1 if r['summary']['fail']>0 else 0)"
```
