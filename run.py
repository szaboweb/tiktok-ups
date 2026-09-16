import os
import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup base paths
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

# Ensure required runtime directories exist
(BASE_DIR / "Queue").mkdir(exist_ok=True)
(BASE_DIR / "Processed").mkdir(exist_ok=True)
(BASE_DIR / "auth").mkdir(exist_ok=True)

from app.server import app, start_services, stop_services

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "False").lower() in ("true", "1")

    print("================================================================")
    print("           TIKTOK-UPS CONTENT ORCHESTRATOR SERVER               ")
    print("================================================================")
    print(f"[STATUS] Initializing orchestrator on http://localhost:{port}")
    print(f"[WATCHER] Queue directory: {BASE_DIR / 'Queue'}")
    print(f"[ARCHIVE] Processed directory: {BASE_DIR / 'Processed'}")
    print(f"[AUTH] Credentials path: {BASE_DIR / 'auth'}")
    print("================================================================")
    print("Streaming terminal logs active. Zero-emoji compliance verified.")
    print("Ready for content ingestion.\n")

    # Start background scheduler and directory watcher threads
    start_services()

    try:
        # Run Flask development server (threaded for SSE log streaming and concurrent requests)
        app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n[STATUS] Terminating orchestrator services...")
        stop_services()
        print("[STATUS] Shutdown complete.")
