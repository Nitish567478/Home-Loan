import uvicorn
import os
import sys
import webbrowser
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

def open_browser(port):
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{port}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    print("=" * 70)
    print(f"  Home Credit LAP Voice Agent is running!")
    print(f"  👉 Open in your browser: http://localhost:{port}")
    print(f"                     or:   http://127.0.0.1:{port}")
    print("=" * 70)
    
    if os.environ.get("NO_BROWSER") != "1":
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    uvicorn.run("app.api:app", host=host, port=port, reload=False)

