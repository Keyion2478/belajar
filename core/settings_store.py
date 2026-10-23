import json
import os
from .system_detector import get_recommended_cache_dir

SETTINGS_FILE = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "rclone",
    "gui_settings.json"
)

DEFAULT_SETTINGS = {
    "union_remote": "Gdrive_union",
    "drive_letter": "G",
    "volume_name": "AHA DRIVE",
    "cache_dir": get_recommended_cache_dir(),
    "cache_max_size": "10G",
    "cache_max_age": "24h",
    "auto_start": False,
    "create_policy": "epff"
}

def clean_volume_name(name: str) -> str:
    """Membersihkan karakter ilegal Windows untuk label volume dan UNC share (< > : " / \\ | ? *)."""
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join(c for c in str(name) if c not in invalid_chars).strip()
    return cleaned or "AHA DRIVE"

def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = dict(DEFAULT_SETTINGS)
                merged.update(data)
                # Bersihkan volume name dari karakter ilegal
                merged["volume_name"] = clean_volume_name(merged.get("volume_name", "AHA DRIVE"))
                return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)

def save_settings(data: dict):
    if "volume_name" in data:
        data["volume_name"] = clean_volume_name(data["volume_name"])
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
