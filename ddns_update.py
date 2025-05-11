#!/usr/bin/env python3
"""
Simple public‑IP checker & Dynamic‑DNS updater for use in a cron job.

Cron example (runs every 5 minutes):
    */5 * * * * /usr/bin/env python3 /usr/local/bin/ddns_update.py
"""

# ─── Configuration ────────────────────────────────────────────────────────────
IP_FILE      = "/var/cache/current_public_ip"         # where we remember the last IP
CHECK_IP_URL = "https://ipv4.icanhazip.com"           # service that returns plain IPv4 text
DYNDNS_URL   = "https://user:pass@dyn.example.com/nic/update?hostname=myhome.example.com"
# ───────────────────────────────────────────────────────────────────────────────

import re
import sys
import subprocess
from pathlib import Path

_IPv4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

# -----------------------------------------------------------------------------


def _curl(url: str) -> str:
    """Run curl -fsSL <url> and return its stdout, raising on failure/timeout."""
    try:
        out = subprocess.check_output(["curl", "-fsSL4", url], timeout=15)
        return out.decode().strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        sys.exit(f"[ERROR] curl failed ({url}): {exc}")


def current_ip() -> str:
    """Fetch the current public IPv4 and validate it."""
    ip = _curl(CHECK_IP_URL)
    if not _IPv4_RE.fullmatch(ip):
        sys.exit(f"[ERROR] Invalid IP returned by {CHECK_IP_URL!r}: {ip!r}")
    return ip


def stored_ip(file_path: Path) -> str | None:
    """
    Read and validate the stored IP.
    Returns None if the file is missing, empty, contains >1 line, or is invalid.
    """
    try:
        lines = file_path.read_text().splitlines()
    except FileNotFoundError:
        return None

    if len(lines) != 1:
        return None

    ip = lines[0].strip()
    return ip if _IPv4_RE.fullmatch(ip) else None


def write_ip(file_path: Path, ip: str) -> None:
    """Overwrite the file with the new IP (plus newline)."""
    file_path.write_text(ip + "\n")


def update_dyndns() -> None:
    """Trigger the Dynamic‑DNS provider and print its response."""
    response = _curl(DYNDNS_URL)
    print(f"[INFO] DynDNS response: {response}")


def main() -> None:
    cur = current_ip()
    prev = stored_ip(Path(IP_FILE))

    if prev == cur:
        print(f"[INFO] IP unchanged: {cur}")
        return

    print(f"[INFO] IP change detected: {prev or '<none>'} → {cur}")
    update_dyndns()
    write_ip(Path(IP_FILE), cur)
    print("[INFO] Stored IP updated.")


if __name__ == "__main__":
    main()
