import sys
import os

# Pastikan path folder root proyek terdaftar di sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from gui import MainApp

def main():
    try:
        # Dukungan DPI scaling Windows modern
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

        app = MainApp()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error tidak terduga: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
