"""
Unified Application Launcher
Runs the complete Quantitative Swing Trading Full-Stack Platform.
"""
import os
import sys
import subprocess
import webbrowser
import time

def main():
    print("=" * 60)
    print(" 🚀 Starting QUANTUM SWING Full-Stack Trading Platform")
    print("=" * 60)

    # Ensure backend is in python path
    backend_dir = os.path.abspath("backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    import uvicorn

    import socket
    local_ip = socket.gethostbyname(socket.gethostname())
    print(f" -> Local (this PC):  http://127.0.0.1:8001")
    print(f" -> LAN (any device): http://{local_ip}:8001")
    print(" -> Press Ctrl+C to terminate.")

    # Auto-open browser
    try:
        webbrowser.open(f"http://{local_ip}:8001")
    except Exception:
        pass

    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True, app_dir=backend_dir)

if __name__ == "__main__":
    main()
