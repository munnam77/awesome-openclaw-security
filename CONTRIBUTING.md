# Contributing to awesome-openclaw-security

Thank you for your interest in improving OpenClaw security for everyone. This project welcomes contributions from security researchers, developers, and system administrators.

---

## Ways to Contribute

### Report a Vulnerability

If you discover a vulnerability in OpenClaw itself:

1. **Do NOT open a public issue.** Responsible disclosure protects users.
2. Report to the OpenClaw maintainers via their security policy first.
3. After a CVE is assigned and a patch is released, submit a PR to add it to `cve-tracker.md`.

If you find an issue with THIS repository (e.g., a guide recommends an insecure configuration):

1. Open an issue with the label `security-fix`.
2. Describe the problem and suggest a correction.

### Add a New Guide

1. Create your guide in the `guides/` directory as a Markdown file.
2. Follow the existing format:
   - Title as H1
   - Table of contents
   - Clear sections with code blocks
   - Navigation links at the bottom (Next / Previous / Back to README)
3. Add an entry in `README.md` under the Guides table.
4. Submit a pull request.

**Guide quality standards:**
- All commands must be tested and working
- Explain the "why" behind each configuration change
- Include verification steps so users can confirm the hardening worked
- Link to relevant CVEs when applicable

### Update the Malicious Skills Database

To add new malicious patterns to `scanner/malicious-skills.json`:

1. Fork the repository.
2. Add your pattern to the `patterns` array:

```json
{
  "id": "CATEGORY-NNN",
  "name": "Human-readable name",
  "severity": "critical",
  "indicators": [
    "regex_pattern_1",
    "regex_pattern_2"
  ],
  "description": "What this pattern does and why it's dangerous.",
  "first_seen": "YYYY-MM-DD",
  "claw_hub_ids": ["known-malicious-skill-names"]
}
```

3. Update the `total_patterns` count and `last_updated` date.
4. Test your pattern: `python3 scanner/scan.py --demo --verbose`
5. Submit a pull request with:
   - The pattern definition
   - Evidence or reference for the malicious behavior
   - A test case (add to `scanner/demo/` if applicable)

**Pattern ID conventions:**
- `AMOS-NNN` -- macOS stealer variants
- `RSHELL-NNN` -- Reverse shells
- `CRED-NNN` -- Credential theft
- `MINER-NNN` -- Crypto miners
- `EXFIL-NNN` -- Data exfiltration
- `KEYLOG-NNN` -- Keyloggers
- `RANSOM-NNN` -- Ransomware
- `PERSIST-NNN` -- Persistence mechanisms
- `SUPPLY-NNN` -- Supply chain attacks
- `PRIV-NNN` -- Privilege escalation
- `CLIP-NNN` -- Clipboard attacks

### Improve the Scanner

The scanner (`scanner/scan.py`) uses only the Python standard library. Contributions must maintain this constraint.

**Code style:**
- Python 3.8+ compatible
- Type hints where practical
- Docstrings for all public functions
- No external dependencies (stdlib only)
- Test your changes against the demo skills

**Testing:**

```bash
# Run against demo skills (should produce 1 PASS, 1 WARN, 1 FAIL)
python3 scanner/scan.py --demo

# Run with verbose output
python3 scanner/scan.py --demo --verbose

# Test JSON output
python3 scanner/scan.py --demo --json | python3 -m json.tool
```

### Add External Resources

To add a link to `resources.md`:

1. Place it in the appropriate category.
2. Include: title, one-line description, and URL.
3. Prefer primary sources (original research, official blogs) over summaries.

---

## Pull Request Process

1. Fork the repository and create a descriptive branch name.
2. Make your changes.
3. Test everything locally.
4. Submit a PR with:
   - Clear description of what changed and why
   - Reference to any related issues
   - Test results (for scanner changes)
5. A maintainer will review within 72 hours.

---

## Code of Conduct

- Be respectful and constructive
- Focus on facts and technical merit
- No personal attacks or harassment
- Security discussions should be responsible (no publishing working exploits against unpatched vulnerabilities)

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
