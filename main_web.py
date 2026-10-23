# -*- coding: utf-8 -*-
"""
AHA DRIVE • Astral Engine (Modern Web Desktop Edition)
Native Windows Executable using Edge WebView2 (pywebview) + Python Core
"""

import os
import sys
import webview
from web_bridge import WebBridgeAPI

# Path resolution aman baik mode script maupun PyInstaller frozen .exe
if getattr(sys, 'frozen', False):
    # Mode PyInstaller
    bundle_dir = getattr(sys, '_MEIPASS', None)
    if bundle_dir and os.path.exists(os.path.join(bundle_dir, "web")):
        BASE_DIR = bundle_dir
    else:
        BASE_DIR = os.path.dirname(sys.executable)
else:
    # Mode Python normal
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def main():
    try:
        # DPI Awareness untuk Windows modern
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

        # Inisialisasi API Bridge Python
        api = WebBridgeAPI()

        # Path ke file web UI
        web_dir = os.path.join(BASE_DIR, "web")
        index_file = os.path.join(web_dir, "index.html")

        # Fallback jika folder web ada di samping exe
        if not os.path.exists(index_file):
            alt_web = os.path.join(os.path.dirname(sys.executable), "web", "index.html")
            if os.path.exists(alt_web):
                index_file = alt_web

        if not os.path.exists(index_file):
            print(f"Error: File UI tidak ditemukan di {index_file}", file=sys.stderr)
            sys.exit(1)

        # Buat Desktop Window berakselerasi GPU (Edge WebView2)
        window = webview.create_window(
            title="AHA DRIVE • Astral Engine (Rclone Google Drive Union)",
            url=index_file,
            js_api=api,
            width=1160,
            height=740,
            min_size=(980, 640),
            background_color="#0B0C0F",
            text_select=False
        )

        # Jalankan loop aplikasi desktop
        webview.start(debug=False)

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
