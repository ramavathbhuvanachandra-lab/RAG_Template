#!/usr/bin/env python3
"""Dedicated production launcher for S. R. Group of Institutions (SRGI) AI Assistant.

Ensures deterministic startup:
- Loads .env with INSTITUTION_ID=srgi
- Verifies Ollama connectivity
- Checks port availability (default: 8501)
- Launches Streamlit with the authoritative SRGI configuration
"""

import os
import socket
import sys
import subprocess
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parent

# 1. Force authoritative environment
os.environ["INSTITUTION_ID"] = "srgi"
os.environ["RAG_USE_STAGING"] = "1"
load_dotenv(WORKSPACE_ROOT / ".env", override=False)


def check_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if the designated port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def check_ollama(base_url: str = "http://localhost:11434") -> bool:
    """Verify local Ollama service is reachable."""
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", headers={"User-Agent": "SRGI-Launcher"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> None:
    port = int(os.environ.get("STREAMLIT_PORT", "8501"))
    host = os.environ.get("STREAMLIT_HOST", "localhost")

    print("=" * 70)
    print("  S. R. Group of Institutions (SRGI), Lucknow — AI Assistant Launcher")
    print("=" * 70)
    print(f"• Workspace Directory: {WORKSPACE_ROOT}")
    print(f"• Institution Tenant:  {os.environ.get('INSTITUTION_ID')}")
    print(f"• Target Service URL:  http://{host}:{port}")

    # Check Ollama
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    if not check_ollama(ollama_url):
        print(f"\n⚠️  WARNING: Ollama server at {ollama_url} does not appear to be running.")
        print("   Please start Ollama in another terminal via: 'ollama serve'\n")
    else:
        print(f"• Ollama Status:       ONLINE ({ollama_url})")

    # Check Port
    if check_port_in_use(port):
        print(f"\nℹ️  Port {port} is currently bound by an existing process.")
        print("   If this is an existing SRGI instance, you can access it directly at:")
        print(f"   --> http://{host}:{port}")
        print("\n   To start on an alternative port (e.g. 8502):")
        print(f"   STREAMLIT_PORT=8502 python {Path(__file__).name}\n")
        sys.exit(0)

    print(f"\n🚀 Launching SRGI Assistant on port {port}...")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(WORKSPACE_ROOT / "app.py"),
        "--server.port",
        str(port),
        "--server.address",
        "0.0.0.0",
        "--browser.serverAddress",
        host,
    ]
    try:
        subprocess.run(cmd, cwd=str(WORKSPACE_ROOT))
    except KeyboardInterrupt:
        print("\n🛑 SRGI Assistant stopped cleanly.")


if __name__ == "__main__":
    main()
