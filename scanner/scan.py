#!/usr/bin/env python3
"""
OpenClaw Skill Security Scanner v1.0.0

Scans OpenClaw skill files for malicious patterns, suspicious code,
and known attack signatures. Uses only Python standard library.

Usage:
    python3 scan.py --path ./skills/
    python3 scan.py --path ./skills/ --json
    python3 scan.py --path ./skills/ --verbose
    python3 scan.py --demo

Requirements: Python 3.8+ (no external dependencies)
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSION = "1.0.0"
SCANNER_DIR = Path(__file__).parent.resolve()
DEMO_DIR = SCANNER_DIR / "demo"
PATTERNS_FILE = SCANNER_DIR / "malicious-skills.json"

# ANSI color codes
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        cls.RED = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.BLUE = ""
        cls.BOLD = ""
        cls.DIM = ""
        cls.RESET = ""


# Suspicious patterns organized by severity and category
CRITICAL_PATTERNS = [
    {
        "id": "CRIT-001",
        "name": "eval/exec call",
        "pattern": r"\b(eval|exec|compile)\s*\(",
        "description": "Arbitrary code execution via eval/exec/compile",
        "category": "code_execution",
    },
    {
        "id": "CRIT-002",
        "name": "os.system/os.popen",
        "pattern": r"\bos\s*\.\s*(system|popen|popen2|popen3|popen4)\s*\(",
        "description": "Shell command execution via os module",
        "category": "code_execution",
    },
    {
        "id": "CRIT-003",
        "name": "subprocess usage",
        "pattern": r"\bsubprocess\s*\.\s*(Popen|run|call|check_output|check_call|getoutput|getstatusoutput)\s*\(",
        "description": "Shell command execution via subprocess",
        "category": "code_execution",
    },
    {
        "id": "CRIT-004",
        "name": "child_process (Node.js)",
        "pattern": r"\b(child_process|require\s*\(\s*['\"]child_process['\"]\s*\))\s*\.\s*(exec|spawn|execFile|fork)\s*\(",
        "description": "Shell command execution via child_process (Node.js)",
        "category": "code_execution",
    },
    {
        "id": "CRIT-005",
        "name": "reverse shell pattern",
        "pattern": r"(socket\s*\.\s*connect|new\s+net\.Socket|\.connect\s*\(\s*\{?\s*(?:host|port))\s*.*?(?:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|['\"][^'\"]+['\"])",
        "description": "Network socket connection to external host (reverse shell indicator)",
        "category": "network",
    },
    {
        "id": "CRIT-006",
        "name": "credential file access",
        "pattern": r"""(?:open|readFile|readFileSync|fs\.read)\s*\(.*?(?:\.ssh[/\\]|\.aws[/\\]|\.gnupg[/\\]|\.config[/\\]|id_rsa|id_ed25519|credentials|\.env\b|\.netrc|keychain|wallet\.dat)""",
        "description": "Accessing sensitive credential files",
        "category": "credential_theft",
    },
    {
        "id": "CRIT-007",
        "name": "dynamic import bypass",
        "pattern": r"\b(__import__|importlib\s*\.\s*import_module)\s*\(",
        "description": "Dynamic import to bypass static analysis",
        "category": "evasion",
    },
    {
        "id": "CRIT-008",
        "name": "ctypes native library loading",
        "pattern": r"\bctypes\s*\.\s*(CDLL|cdll|windll|WinDLL)\s*\(",
        "description": "Loading native libraries via ctypes (sandbox escape)",
        "category": "evasion",
    },
    {
        "id": "CRIT-009",
        "name": "Function constructor (JS)",
        "pattern": r"\bnew\s+Function\s*\(",
        "description": "Dynamic code generation via Function constructor",
        "category": "code_execution",
    },
]

WARNING_PATTERNS = [
    {
        "id": "WARN-001",
        "name": "outbound HTTP request",
        "pattern": r"\b(requests\s*\.\s*(get|post|put|delete|patch|head)|urllib\.request\.urlopen|httpx\.\s*(get|post)|aiohttp\.ClientSession|fetch\s*\(|XMLHttpRequest|axios\s*\.\s*(get|post))\s*\(",
        "description": "Outbound HTTP request to external server",
        "category": "network",
    },
    {
        "id": "WARN-002",
        "name": "base64 encoding",
        "pattern": r"\b(base64\s*\.\s*(b64encode|encodebytes|b64decode)|btoa\s*\(|Buffer\.from\s*\(.*?['\"]base64['\"])",
        "description": "Base64 encoding/decoding (potential data exfiltration or payload hiding)",
        "category": "obfuscation",
    },
    {
        "id": "WARN-003",
        "name": "filesystem write outside cwd",
        "pattern": r"""(?:open|writeFile|writeFileSync|fs\.write)\s*\(.*?(?:['\"]\/(?:etc|tmp|var|usr|home)|\.\./)""",
        "description": "File write to path outside skill directory",
        "category": "filesystem",
    },
    {
        "id": "WARN-004",
        "name": "environment variable access",
        "pattern": r"\b(os\.environ|process\.env)\s*[\[.]",
        "description": "Reading environment variables (may contain secrets)",
        "category": "credential_theft",
    },
    {
        "id": "WARN-005",
        "name": "obfuscated code pattern",
        "pattern": r"(\\x[0-9a-fA-F]{2}){8,}|(\\\d{3}){8,}|String\.fromCharCode\s*\(.*?,.*?,.*?,",
        "description": "Obfuscated code (hex/octal escape sequences or fromCharCode chains)",
        "category": "obfuscation",
    },
    {
        "id": "WARN-006",
        "name": "timer-based evasion",
        "pattern": r"\b(setTimeout|setInterval|time\.sleep|asyncio\.sleep)\s*\(.*?(86400|3600000|36000|delay|wait)",
        "description": "Long delay that may be used to evade sandbox analysis",
        "category": "evasion",
    },
    {
        "id": "WARN-007",
        "name": "network socket creation",
        "pattern": r"\b(socket\.socket|new\s+WebSocket|net\.createServer|dgram\.createSocket)\s*\(",
        "description": "Raw network socket creation",
        "category": "network",
    },
    {
        "id": "WARN-008",
        "name": "process/system info gathering",
        "pattern": r"\b(os\.uname|platform\.system|platform\.node|os\.hostname|os\.userInfo|os\.getuid)\s*\(",
        "description": "System information gathering (reconnaissance)",
        "category": "recon",
    },
]

# File extensions to scan
SCAN_EXTENSIONS = {
    ".py", ".js", ".ts", ".mjs", ".cjs", ".jsx", ".tsx",
    ".sh", ".bash", ".zsh",
    ".rb", ".pl", ".lua",
    ".yaml", ".yml", ".json", ".toml",
}


def load_malicious_patterns():
    """Load known malicious skill patterns from JSON file."""
    if not PATTERNS_FILE.exists():
        return []
    try:
        with open(PATTERNS_FILE, "r") as f:
            data = json.load(f)
        return data.get("patterns", [])
    except (json.JSONDecodeError, KeyError):
        return []


def compute_file_hash(filepath):
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except OSError:
        return None


def scan_file(filepath, malicious_patterns, verbose=False):
    """
    Scan a single file for suspicious patterns.

    Returns a dict with:
        - status: "pass", "warn", or "fail"
        - findings: list of finding dicts
    """
    findings = []

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            lines = content.split("\n")
    except OSError as e:
        return {
            "status": "warn",
            "findings": [
                {
                    "severity": "warning",
                    "id": "IO-001",
                    "description": f"Could not read file: {e}",
                    "line": 0,
                    "matched_text": "",
                }
            ],
        }

    # Check against known malicious pattern indicators
    file_hash = compute_file_hash(filepath)
    for mp in malicious_patterns:
        indicators = mp.get("indicators", [])
        for indicator in indicators:
            try:
                if re.search(indicator, content, re.IGNORECASE):
                    findings.append(
                        {
                            "severity": "critical",
                            "id": mp["id"],
                            "description": f"Matched known malicious pattern: {mp['name']}",
                            "line": 0,
                            "matched_text": indicator,
                            "pattern_info": mp.get("description", ""),
                        }
                    )
            except re.error:
                pass

    # Check critical patterns
    for pattern_def in CRITICAL_PATTERNS:
        try:
            regex = re.compile(pattern_def["pattern"], re.IGNORECASE)
        except re.error:
            continue

        for line_num, line in enumerate(lines, 1):
            match = regex.search(line)
            if match:
                findings.append(
                    {
                        "severity": "critical",
                        "id": pattern_def["id"],
                        "description": pattern_def["description"],
                        "line": line_num,
                        "matched_text": match.group(0).strip(),
                        "category": pattern_def["category"],
                    }
                )

    # Check warning patterns
    for pattern_def in WARNING_PATTERNS:
        try:
            regex = re.compile(pattern_def["pattern"], re.IGNORECASE)
        except re.error:
            continue

        for line_num, line in enumerate(lines, 1):
            match = regex.search(line)
            if match:
                findings.append(
                    {
                        "severity": "warning",
                        "id": pattern_def["id"],
                        "description": pattern_def["description"],
                        "line": line_num,
                        "matched_text": match.group(0).strip(),
                        "category": pattern_def["category"],
                    }
                )

    # Determine overall status
    has_critical = any(f["severity"] == "critical" for f in findings)
    has_warning = any(f["severity"] == "warning" for f in findings)

    if has_critical:
        status = "fail"
    elif has_warning:
        status = "warn"
    else:
        status = "pass"

    return {"status": status, "findings": findings, "hash": file_hash}


def discover_files(scan_path):
    """Discover all scannable files in the given path."""
    scan_path = Path(scan_path).resolve()
    files = []

    if scan_path.is_file():
        if scan_path.suffix.lower() in SCAN_EXTENSIONS:
            files.append(scan_path)
    elif scan_path.is_dir():
        for root, _dirs, filenames in os.walk(scan_path):
            # Skip hidden directories and node_modules
            root_path = Path(root)
            if any(
                part.startswith(".") or part == "node_modules"
                for part in root_path.parts
            ):
                continue
            for filename in sorted(filenames):
                filepath = root_path / filename
                if filepath.suffix.lower() in SCAN_EXTENSIONS:
                    files.append(filepath)
    else:
        print(
            f"{Colors.RED}Error: Path does not exist: {scan_path}{Colors.RESET}",
            file=sys.stderr,
        )
        sys.exit(1)

    return files


def print_banner(scan_path):
    """Print the scanner banner."""
    print(f"\n{'=' * 56}")
    print(f"  {Colors.BOLD}OpenClaw Skill Security Scanner v{VERSION}{Colors.RESET}")
    print(f"  Scanning: {scan_path}")
    print(f"{'=' * 56}\n")


def print_result(filepath, result, base_path, verbose=False):
    """Print scan result for a single file."""
    rel_path = filepath.name
    try:
        rel_path = filepath.relative_to(base_path)
    except ValueError:
        rel_path = filepath.name

    status = result["status"]
    findings = result["findings"]

    if status == "pass":
        print(f"{Colors.GREEN}[PASS]{Colors.RESET} {rel_path}")
        if verbose:
            print(f"  {Colors.DIM}No suspicious patterns detected.{Colors.RESET}")
    elif status == "warn":
        warn_count = len([f for f in findings if f["severity"] == "warning"])
        print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {rel_path}")
        print(
            f"  {Colors.YELLOW}{warn_count} warning(s) found:{Colors.RESET}"
        )
        for finding in findings:
            if finding["severity"] == "warning" or verbose:
                line_info = f"Line {finding['line']}: " if finding["line"] > 0 else ""
                print(
                    f"  {Colors.DIM}- {line_info}{finding['description']}{Colors.RESET}"
                )
                if verbose and finding.get("matched_text"):
                    print(
                        f"    {Colors.DIM}Matched: {finding['matched_text']}{Colors.RESET}"
                    )
    elif status == "fail":
        crit_count = len([f for f in findings if f["severity"] == "critical"])
        print(f"{Colors.RED}[FAIL]{Colors.RESET} {rel_path}")
        print(
            f"  {Colors.RED}CRITICAL: {crit_count} malicious indicator(s) detected{Colors.RESET}"
        )
        for finding in findings:
            if finding["severity"] == "critical":
                line_info = f"Line {finding['line']}: " if finding["line"] > 0 else ""
                print(f"  {Colors.RED}- {line_info}{finding['description']}{Colors.RESET}")
                if verbose and finding.get("matched_text"):
                    print(
                        f"    {Colors.DIM}Matched: {finding['matched_text']}{Colors.RESET}"
                    )
                if verbose and finding.get("pattern_info"):
                    print(
                        f"    {Colors.DIM}Info: {finding['pattern_info']}{Colors.RESET}"
                    )
        # Also show warnings in verbose mode
        if verbose:
            for finding in findings:
                if finding["severity"] == "warning":
                    line_info = (
                        f"Line {finding['line']}: " if finding["line"] > 0 else ""
                    )
                    print(
                        f"  {Colors.YELLOW}- {line_info}{finding['description']}{Colors.RESET}"
                    )
    print()


def print_summary(results):
    """Print scan summary."""
    pass_count = sum(1 for r in results.values() if r["status"] == "pass")
    warn_count = sum(1 for r in results.values() if r["status"] == "warn")
    fail_count = sum(1 for r in results.values() if r["status"] == "fail")

    print(f"{'=' * 56}")
    print(f"  {Colors.BOLD}Results:{Colors.RESET} ", end="")
    print(f"{Colors.GREEN}{pass_count} PASS{Colors.RESET}", end=" | ")
    print(f"{Colors.YELLOW}{warn_count} WARN{Colors.RESET}", end=" | ")
    print(f"{Colors.RED}{fail_count} FAIL{Colors.RESET}")

    if fail_count > 0:
        print(
            f"\n  {Colors.RED}{Colors.BOLD}Action Required:{Colors.RESET} "
            f"Remove FAIL items immediately. Review WARN items manually."
        )
    elif warn_count > 0:
        print(
            f"\n  {Colors.YELLOW}Action Required:{Colors.RESET} "
            f"Review WARN items manually before deploying."
        )
    else:
        print(
            f"\n  {Colors.GREEN}All skills passed.{Colors.RESET} "
            f"Consider periodic re-scanning."
        )
    print(f"{'=' * 56}\n")


def output_json(results, scan_path):
    """Output results as JSON."""
    pass_count = sum(1 for r in results.values() if r["status"] == "pass")
    warn_count = sum(1 for r in results.values() if r["status"] == "warn")
    fail_count = sum(1 for r in results.values() if r["status"] == "fail")

    output = {
        "scan_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scanner_version": VERSION,
        "scan_path": str(scan_path),
        "skills_scanned": len(results),
        "summary": {
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
        },
        "results": [],
    }

    for filepath, result in results.items():
        entry = {
            "skill": str(filepath),
            "status": result["status"],
            "hash": result.get("hash", ""),
            "findings": [],
        }
        for finding in result["findings"]:
            entry["findings"].append(
                {
                    "severity": finding["severity"],
                    "id": finding["id"],
                    "description": finding["description"],
                    "line": finding["line"],
                    "matched_text": finding.get("matched_text", ""),
                }
            )
        output["results"].append(entry)

    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw Skill Security Scanner — detect malicious patterns in skill files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --path ./skills/           Scan all skills in directory
  %(prog)s --path ./skills/ --json    Output results as JSON
  %(prog)s --path ./skills/ --verbose Show detailed match information
  %(prog)s --demo                     Scan included demo skills
        """,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"OpenClaw Skill Security Scanner v{VERSION}",
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Path to skill file or directory to scan",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (for CI/CD integration)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed match information including matched text",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Scan the included demo skills directory",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.path and not args.demo:
        parser.error("Either --path or --demo is required")

    # Disable colors if requested or if not a terminal
    if args.no_color or not sys.stdout.isatty() or args.json:
        Colors.disable()

    # Determine scan path
    if args.demo:
        scan_path = DEMO_DIR
        if not scan_path.exists():
            print(
                f"{Colors.RED}Error: Demo directory not found at {scan_path}{Colors.RESET}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        scan_path = Path(args.path).resolve()

    # Load malicious patterns database
    malicious_patterns = load_malicious_patterns()

    # Discover files
    files = discover_files(scan_path)

    if not files:
        if not args.json:
            print(f"{Colors.YELLOW}No scannable files found in {scan_path}{Colors.RESET}")
        else:
            print(json.dumps({"error": "No scannable files found", "scan_path": str(scan_path)}))
        sys.exit(0)

    # Print banner (non-JSON mode)
    if not args.json:
        print_banner(scan_path)

    # Scan all files
    results = {}
    for filepath in files:
        result = scan_file(filepath, malicious_patterns, verbose=args.verbose)
        results[filepath] = result

        if not args.json:
            print_result(filepath, result, scan_path, verbose=args.verbose)

    # Output
    if args.json:
        output_json(results, scan_path)
    else:
        print_summary(results)

    # Exit code: 1 if any failures, 0 otherwise
    has_failures = any(r["status"] == "fail" for r in results.values())
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    main()
