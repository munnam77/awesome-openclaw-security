<p align="center">
  <img src="https://img.shields.io/badge/OpenClaw_Security-Hardening_Guide-red?style=for-the-badge&logo=shield" alt="OpenClaw Security"/>
  <br/>
  <img src="https://img.shields.io/badge/Last_Updated-March_2026-blue?style=flat-square" alt="Last Updated"/>
  <img src="https://img.shields.io/badge/CVEs_Tracked-5-critical?style=flat-square" alt="CVEs Tracked"/>
  <img src="https://img.shields.io/badge/Malicious_Patterns-15-orange?style=flat-square" alt="Malicious Patterns"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"/>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python" alt="Python 3.8+"/>
</p>

# awesome-openclaw-security

> **Stop deploying OpenClaw naked. 30,000+ instances are exposed right now. Don't be one of them.**

A comprehensive security hardening guide, toolkit, and malicious skill scanner for [OpenClaw](https://github.com/openclaw/openclaw) -- the open-source personal AI assistant with 280k+ GitHub stars and a massive security crisis.

---

## Quick Start: Scan Your Skills in 30 Seconds

```bash
git clone https://github.com/munnam77/awesome-openclaw-security.git
cd awesome-openclaw-security
python3 scanner/scan.py --path /path/to/your/openclaw/skills
```

Want to see it in action first? Run the demo:

```bash
python3 scanner/scan.py --demo
```

<details>
<summary>Example output</summary>

```
========================================================
  OpenClaw Skill Security Scanner v1.0.0
  Scanning: scanner/demo/
========================================================

[FAIL] malicious-skill.js
  CRITICAL: 5 malicious indicator(s) detected
  - Matched known malicious pattern: Node.js Reverse Shell
  - Matched known malicious pattern: AWS Credential Theft
  - Matched known malicious pattern: Crontab/LaunchAgent Persistence
  - Line 78: Arbitrary code execution via eval/exec/compile
  - Line 68: Shell command execution via child_process (Node.js)

[PASS] safe-skill.js

[WARN] suspicious-skill.js
  1 warning(s) found:
  - Line 88: Reading environment variables (may contain secrets)

========================================================
  Results: 1 PASS | 1 WARN | 1 FAIL

  Action Required: Remove FAIL items immediately. Review WARN items manually.
========================================================
```

</details>

---

## Security Score: Rate Your Deployment

Answer these questions to gauge your risk level:

| # | Question | Yes | No |
|---|----------|-----|----|
| 1 | Is your gateway bound to `127.0.0.1` (not `0.0.0.0`)? | +0 | +3 |
| 2 | Is authentication enabled on the WebSocket gateway? | +0 | +5 |
| 3 | Have you audited all installed skills? | +0 | +4 |
| 4 | Are credentials stored in a vault (not env vars)? | +0 | +3 |
| 5 | Is your instance behind a reverse proxy with rate limiting? | +0 | +2 |
| 6 | Are you running in Docker with non-root user? | +0 | +2 |
| 7 | Is network access restricted (firewall/VPN)? | +0 | +3 |
| 8 | Do you manually review skill updates before applying? | +0 | +2 |

**Score interpretation:**

| Score | Risk Level | Action |
|-------|-----------|--------|
| 0 | Hardened | Maintain vigilance. Review monthly. |
| 1-5 | Moderate | Address gaps using guides below. |
| 6-12 | High | Stop. Harden before continued use. |
| 13+ | Critical | **Your instance is likely already compromised.** |

---

## Table of Contents

- [CVE Summary](#cve-summary)
- [Why This Exists](#why-this-exists)
- [Security Checklist](#security-checklist)
- [Guides](#guides)
- [Scanner Tool](#scanner-tool)
- [Secure Configs](#secure-configs)
- [Resources](#resources)
- [Contributing](#contributing)
- [License](#license)

---

## CVE Summary

| CVE ID | CVSS | Description | Status | Patch |
|--------|------|-------------|--------|-------|
| [CVE-2026-25253](cve-tracker.md#cve-2026-25253) | **8.8** (High) | Remote code execution via gateway WebSocket hijack | Patch available | v0.4.7+ |
| [CVE-2026-24891](cve-tracker.md#cve-2026-24891) | **9.1** (Critical) | Skill sandbox escape via `__import__` bypass | Patch available | v0.4.6+ |
| [CVE-2026-23102](cve-tracker.md#cve-2026-23102) | **7.5** (High) | Unauthenticated gateway access (default config) | Mitigation only | See [guide](guides/gateway-hardening.md) |
| [CVE-2026-22847](cve-tracker.md#cve-2026-22847) | **6.5** (Medium) | Credential leakage via skill error messages | Patch available | v0.4.5+ |
| [CVE-2026-21534](cve-tracker.md#cve-2026-21534) | **8.1** (High) | ClawHub supply chain injection via typosquatting | Under review | N/A |

Full details: [cve-tracker.md](cve-tracker.md)

---

## Why This Exists

OpenClaw hit 280k stars and became the #1 trending project on GitHub. But rapid adoption outpaced security:

- **800+ malicious skills** discovered in ClawHub (roughly 20% of the registry) -- SecurityWeek: "OpenClaw Security Issues Continue as Adoption Soars" (Feb 2026)
- **30,000+ internet-exposed instances** found via Shodan with zero authentication -- The Hacker News: "ClawJacked -- Critical Flaw in OpenClaw Gateway" (Feb 2026)
- **Microsoft Security Blog** published "Running OpenClaw Safely in Enterprise" warning against unvetted deployments -- Microsoft Security Blog (Feb 2026)
- **Kaspersky** published "Key OpenClaw Risks Enterprises Must Address" -- Kaspersky Blog (Mar 2026)
- **CVE-2026-25253** (CVSS 8.8) enables full remote code execution through a compromised gateway

This repo exists because security documentation for OpenClaw is scattered, incomplete, and hard to act on. We centralized everything into one place with actionable checklists, guides, configs, and a scanner you can run right now.

---

## Security Checklist

A comprehensive, copy-paste hardening checklist with 25+ items organized by category.

**[View Full Checklist](security-checklist.md)**

Preview:

- [ ] Gateway bound to `127.0.0.1` instead of `0.0.0.0`
- [ ] Authentication tokens enabled on gateway
- [ ] All skills audited with scanner before installation
- [ ] Docker deployment using non-root user
- [ ] Credentials stored in Docker secrets or HashiCorp Vault

---

## Guides

| Guide | Description |
|-------|-------------|
| [Gateway Hardening](guides/gateway-hardening.md) | Lock down the WebSocket gateway: bind address, auth, rate limiting, session timeouts |
| [Skill Vetting](guides/skill-vetting.md) | Audit skills before installation: red flags, manual review, scanner usage, sandboxing |
| [Secure Docker Deployment](guides/docker-secure-deploy.md) | Production Docker Compose: non-root, read-only fs, network isolation, resource limits |
| [Network Isolation](guides/network-isolation.md) | Firewall rules, Cloudflare Tunnel, VPN-only access, reverse proxy hardening |
| [Credential Management](guides/credential-management.md) | Secure storage: Docker secrets, Vault integration, key rotation, audit trails |

---

## Scanner Tool

A zero-dependency Python CLI that scans OpenClaw skills for malicious patterns.

```bash
# Scan a skills directory
python3 scanner/scan.py --path ./my-skills/

# JSON output for CI/CD integration
python3 scanner/scan.py --path ./my-skills/ --json

# Verbose mode (show all pattern matches)
python3 scanner/scan.py --path ./my-skills/ --verbose

# Run demo with sample skills
python3 scanner/scan.py --demo
```

**What it detects:**

- `eval()`, `exec()`, `compile()` calls
- `subprocess`, `os.system`, `os.popen` usage
- Outbound HTTP/HTTPS requests (requests, urllib, httpx, aiohttp, fetch)
- Base64 encoding (potential data exfiltration)
- File system access outside skill directory
- Dynamic imports (`__import__`, `importlib`)
- Known malicious pattern hashes (from `malicious-skills.json`)
- Reverse shell indicators
- Credential harvesting patterns

**Requirements:** Python 3.8+ (standard library only, no pip install needed)

---

## Secure Configs

Ready-to-use configuration files for production deployments:

| Config | Description |
|--------|-------------|
| [docker-compose.secure.yml](configs/docker-compose.secure.yml) | Hardened Docker Compose with non-root, read-only fs, resource limits |
| [nginx-proxy.conf](configs/nginx-proxy.conf) | Nginx reverse proxy with rate limiting, security headers, WebSocket support |
| [.env.example](configs/.env.example) | Environment variable template with secure defaults |

---

## Resources

Curated external references for OpenClaw security:

**[View All Resources](resources.md)**

Key readings:
- Microsoft Security Blog: "Running OpenClaw Safely in Enterprise Environments"
- Kaspersky: "Key OpenClaw Risks Enterprises Must Address"
- The Hacker News: "ClawJacked -- Critical Flaw in OpenClaw Gateway"
- SecurityWeek: "OpenClaw Security Issues Continue as Adoption Soars"

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to report a vulnerability
- How to add a new guide
- How to update the malicious skills database
- Code style for scanner contributions

---

## License

[MIT](LICENSE) -- Copyright 2026 Cognitive AppDev

---

<p align="center">
  <strong>If this helped you secure your OpenClaw deployment, give it a star.</strong><br/>
  <em>One star = one fewer exposed instance.</em>
</p>

---

See also: [LLM Price War](https://github.com/munnam77/llm-price-war) -- LLM pricing comparison across providers.
