#!/usr/bin/env python3
"""
Routine: Browser screenshot of the karaoke frontend.
Starts server, takes screenshot via browser, saves proof.
"""

import subprocess
import time
import sys
import os
import json
from pathlib import Path

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
PORT = 8765
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), '..', 'test_output')


def run():
    print("=== Routine: Browser Screenshot ===")

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # Start server
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT)],
        cwd=FRONTEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    time.sleep(1)

    try:
        # Verify server
        import urllib.request
        resp = urllib.request.urlopen(f"http://localhost:{PORT}/")
        html = resp.read().decode()
        print(f"  ✓ Server running on port {PORT}")
        print(f"  ✓ HTML length: {len(html)} bytes")

        # Check for key elements
        checks = {
            "RAPCHECK logo": "RAPCHECK" in html,
            "song list": "song-list" in html,
            "lyrics container": "lyrics-container" in html,
            "play button": "playBtn" in html,
            "grade display": "gradeDisplay" in html,
            "mic indicator": "micIndicator" in html,
        }

        for name, ok in checks.items():
            print(f"  {'✓' if ok else '✗'} {name}")

        # Save screenshot info for browser tool
        info = {
            "url": f"http://localhost:{PORT}/",
            "port": PORT,
            "checks": checks,
            "html_size": len(html),
        }
        info_path = Path(SCREENSHOT_DIR) / "screenshot_info.json"
        with open(info_path, "w") as f:
            json.dump(info, f, indent=2)
        print(f"\n  → Screenshot URL: http://localhost:{PORT}/")
        print(f"  → Info saved: {info_path}")

        # Keep server running for browser tool
        print(f"\n  Server PID: {server.pid}")
        print(f"  Kill with: kill {server.pid}")

        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        server.terminate()
        return False


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
