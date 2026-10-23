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

    print(" -> Backend API & Frontend UI running at: http://127.0.0.1:8000")
    print(" -> Press Ctrl+C to terminate.")

    # Auto-open browser
    try:
        webbrowser.open("http://127.0.0.1:8000")
    except Exception:
        pass

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, app_dir=backend_dir)

if __name__ == "__main__":
    main()
