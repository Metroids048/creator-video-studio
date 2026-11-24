#!/usr/bin/env python3
"""Run the upstream subset compiler over the studio's generated project."""
import io
import runpy
import subprocess
import sys
import urllib.request


def fetch(request, timeout=60):
    data = subprocess.check_output([
        "curl", "-q", "--noproxy", "*", "--interface", "en0", "-fLsS",
        "--connect-timeout", "15", "--max-time", str(timeout),
        "-A", request.get_header("User-agent"), request.full_url,
    ])
    return io.BytesIO(data)


script = sys.argv.pop(1)
urllib.request.urlopen = fetch
runpy.run_path(script, run_name="__main__")
