# Security Policy

## Scope

This policy covers vulnerabilities in **this repository** (the scanner tool, configs, and guides). If you find a vulnerability in OpenClaw itself, please report it to the [OpenClaw project](https://github.com/openclaw/openclaw/security/advisories) directly.

In scope:
- Bugs in `scanner/scan.py` that cause false negatives (missing real threats)
- Malicious patterns missing from `malicious-skills.json`
- Security misconfigurations in provided config files (`configs/`)

Out of scope:
- Vulnerabilities in OpenClaw core
- Issues in third-party tools listed in `resources.md`

## Reporting a Vulnerability

Email **contact@cognitiveappdev.com** with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

Do **not** open a public issue for security vulnerabilities.

## Response Timeline

- **48 hours**: Acknowledgment of your report
- **7 days**: Initial assessment and fix timeline
- **30 days**: Public disclosure (coordinated with reporter)

## Credit

We credit all reporters in the fix commit and CHANGELOG unless anonymity is requested.
