# Skill Vetting Guide

With 800+ malicious skills discovered in ClawHub (approximately 20% of the registry), every skill must be treated as untrusted code until proven safe. This guide covers manual review, automated scanning, and ongoing monitoring.

---

## Table of Contents

- [The Threat](#the-threat)
- [Red Flags to Look For](#red-flags-to-look-for)
- [Manual Code Review Checklist](#manual-code-review-checklist)
- [Using the Scanner](#using-the-scanner)
- [Trusted vs Untrusted Sources](#trusted-vs-untrusted-sources)
- [Sandboxing Skills](#sandboxing-skills)
- [CI/CD Integration](#cicd-integration)
- [Ongoing Monitoring](#ongoing-monitoring)

---

## The Threat

Malicious skills discovered in ClawHub fall into these categories:

| Category | % of Malicious Skills | Example |
|----------|-----------------------|---------|
| Credential theft | 35% | Reads `~/.ssh/id_rsa`, browser cookies, API keys |
| Reverse shells | 20% | Opens socket to attacker-controlled server |
| Crypto miners | 15% | Runs mining process in background |
| Data exfiltration | 15% | Base64 encodes local files and POSTs to external server |
| Keyloggers | 10% | Captures keystrokes via OS-level hooks |
| Ransomware loaders | 5% | Downloads and executes encryption payload |

Common attack vectors:
- **Typosquatting**: `weather-skilll` (three L's) impersonating `weather-skill`
- **Dependency confusion**: Malicious skill with same name as internal/private skill
- **Update hijack**: Clean initial version, malicious payload added in later update
- **Obfuscation**: Malicious code hidden in base64 strings, hex-encoded payloads, or compressed data

---

## Red Flags to Look For

### Critical (Immediate reject)

| Pattern | Why It's Dangerous |
|---------|--------------------|
| `eval()`, `exec()`, `compile()` | Executes arbitrary code at runtime |
| `os.system()`, `os.popen()` | Runs shell commands |
| `subprocess.Popen`, `subprocess.run` | Spawns external processes |
| `socket.connect()` to external IP | Reverse shell or C2 communication |
| Reading `~/.ssh/`, `~/.aws/`, `~/.gnupg/` | Credential harvesting |
| `base64.b64encode` + outbound HTTP | Data exfiltration |
| `__import__('os')`, `importlib.import_module` | Dynamic import to bypass static analysis |
| `ctypes.CDLL` | Loading native libraries (sandbox escape) |

### Warning (Needs manual review)

| Pattern | Possible Legitimate Use |
|---------|------------------------|
| `requests.get/post` | API calls (check the URL) |
| `urllib.request` | Fetching data (check the URL) |
| `open()` with absolute paths | Config reading (verify path is safe) |
| `threading` / `multiprocessing` | Performance optimization (verify not spawning hidden workers) |
| `tempfile` | Temporary data storage (verify cleanup) |
| Minified or obfuscated code | Bundled dependencies (should still be reviewable) |

### JavaScript-specific Red Flags

| Pattern | Why It's Dangerous |
|---------|--------------------|
| `eval()`, `Function()` constructor | Arbitrary code execution |
| `child_process.exec/spawn` | Shell command execution |
| `require('net').connect()` | Network socket (reverse shell) |
| `fs.readFile` on sensitive paths | Credential harvesting |
| `Buffer.from(..., 'base64')` + HTTP | Data exfiltration |
| `process.env` access | Reading sensitive environment variables |

---

## Manual Code Review Checklist

Before installing any skill, perform this review:

```
1. [ ] Check publisher profile
      - Account age > 30 days?
      - Other published skills?
      - GitHub profile linked?

2. [ ] Read the skill manifest
      - Permissions requested match stated functionality?
      - No excessive filesystem/network permissions?

3. [ ] Review source code
      - Search for every pattern in the red flags table above
      - Check ALL files, not just the main entry point
      - Look inside data files (JSON, YAML) for embedded code

4. [ ] Check dependencies
      - Are dependencies pinned to specific versions?
      - Are dependencies from known, trusted packages?
      - Any dependencies with suspicious names?

5. [ ] Verify update history
      - When was the skill last updated?
      - Do recent updates change permissions?
      - Review diff of latest update

6. [ ] Test in isolation
      - Run in a sandboxed environment first
      - Monitor network connections during execution
      - Check filesystem access patterns
```

---

## Using the Scanner

The included scanner automates detection of known malicious patterns.

### Basic scan

```bash
# Scan a single skill directory
python3 scanner/scan.py --path ./skills/my-skill/

# Scan all skills
python3 scanner/scan.py --path ./skills/

# Verbose output (shows line numbers and matched patterns)
python3 scanner/scan.py --path ./skills/ --verbose
```

### Understanding results

```
[PASS] skill-name
  No suspicious patterns detected.
```
Skill appears clean. Still recommended to do a manual spot-check.

```
[WARN] skill-name
  2 warnings found:
  - Line 14: outbound HTTP request (fetch to external URL)
  - Line 27: dynamic code evaluation pattern
```
Skill has suspicious patterns that MAY be legitimate. Manual review required.

```
[FAIL] skill-name
  CRITICAL: Matched known malicious pattern AMOS-001
```
Skill matches a known malicious signature. **Remove immediately.**

### JSON output for automation

```bash
python3 scanner/scan.py --path ./skills/ --json > results.json
```

Output format:

```json
{
  "scan_date": "2026-03-09T10:30:00Z",
  "scanner_version": "1.0.0",
  "skills_scanned": 15,
  "summary": {
    "pass": 10,
    "warn": 3,
    "fail": 2
  },
  "results": [
    {
      "skill": "skill-name",
      "status": "FAIL",
      "findings": [...]
    }
  ]
}
```

---

## Trusted vs Untrusted Sources

### Trusted (lower risk, still verify)

- Skills from the official OpenClaw repository (`openclaw/skills-*`)
- Skills from verified publishers with 6+ month history
- Skills you or your team wrote and maintain
- Skills recommended in official OpenClaw documentation

### Untrusted (scan and review thoroughly)

- Any skill from ClawHub by an unverified publisher
- Skills with fewer than 10 downloads
- Skills published within the last 30 days
- Skills with no source code repository linked
- Skills that request permissions beyond their stated purpose
- Forked skills with modifications (compare diff against original)

### Never install

- Skills from unknown URLs shared in forums/chat
- Skills distributed as binary/compiled files
- Skills that require disabling security features to install
- Skills that the scanner flags as FAIL

---

## Sandboxing Skills

Even after vetting, run skills with minimal privileges.

### Filesystem sandboxing

Restrict skills to their own directory:

```yaml
# In skill configuration
skills:
  sandbox:
    filesystem:
      # Only allow access to the skill's own directory
      allowed_paths:
        - "${SKILL_DIR}/"
        - "${DATA_DIR}/skill-name/"
      # Block access to sensitive locations
      denied_paths:
        - "/etc/"
        - "${HOME}/.ssh/"
        - "${HOME}/.aws/"
        - "${HOME}/.gnupg/"
        - "${HOME}/.config/"
```

### Network sandboxing

Restrict outbound network access:

```yaml
skills:
  sandbox:
    network:
      # Block all outbound connections by default
      outbound: deny
      # Allowlist specific domains if needed
      allowed_domains:
        - "api.openweathermap.org"
        - "api.github.com"
      # Block all inbound connections
      inbound: deny
```

### Docker-based sandboxing

Run each skill in its own container:

```yaml
services:
  skill-weather:
    image: openclaw/skill-runner:latest
    read_only: true
    network_mode: none  # No network access
    volumes:
      - ./skills/weather:/skill:ro
      - skill-weather-data:/data
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 128M
```

---

## CI/CD Integration

Add the scanner to your deployment pipeline:

```yaml
# GitHub Actions example
name: Skill Security Scan
on:
  pull_request:
    paths:
      - 'skills/**'

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run security scanner
        run: |
          python3 scanner/scan.py --path ./skills/ --json > scan-results.json

      - name: Check for failures
        run: |
          python3 -c "
          import json, sys
          results = json.load(open('scan-results.json'))
          if results['summary']['fail'] > 0:
              print(f'BLOCKED: {results[\"summary\"][\"fail\"]} skills failed security scan')
              for r in results['results']:
                  if r['status'] == 'FAIL':
                      print(f'  - {r[\"skill\"]}: {r[\"findings\"]}')
              sys.exit(1)
          if results['summary']['warn'] > 0:
              print(f'WARNING: {results[\"summary\"][\"warn\"]} skills need manual review')
          print(f'PASSED: {results[\"summary\"][\"pass\"]} skills clean')
          "
```

---

## Ongoing Monitoring

Security is not a one-time check. Set up ongoing monitoring:

1. **Re-scan weekly**: Run the scanner on all installed skills every week
2. **Update patterns**: Pull the latest `malicious-skills.json` from this repo
3. **Monitor ClawHub advisories**: Subscribe to the OpenClaw security mailing list
4. **Audit skill permissions**: Review what each skill has access to monthly
5. **Check for updates**: New skill versions may introduce malicious code

```bash
# Weekly cron job example
0 2 * * 1 cd /opt/openclaw && python3 scanner/scan.py --path ./skills/ --json >> /var/log/openclaw-scan.json 2>&1
```

---

**Next**: [Secure Docker Deployment](docker-secure-deploy.md) | **Previous**: [Gateway Hardening](gateway-hardening.md) | [Back to README](../README.md)
