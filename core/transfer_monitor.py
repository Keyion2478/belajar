import json
import threading
import time
import urllib.request
import urllib.error
import psutil
from .system_detector import format_bytes

def is_rclone_process_active() -> bool:
    """Cek cepat apakah proses rclone sedang berjalan."""
    for p in psutil.process_iter(['name']):
        try:
            if "rclone" in (p.info.get('name') or "").lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def format_eta(seconds: int | float | None) -> str:
    """Mengubah detik ke format waktu ramah pengguna."""
    if seconds is None or seconds < 0:
        return "--"
    sec = int(seconds)
    if sec < 60:
        return f"{sec} dtk"
    mins = sec // 60
    rem_sec = sec % 60
    if mins < 60:
        return f"{mins}m {rem_sec}s"
    hours = mins // 60
    rem_mins = mins % 60
    return f"{hours}j {rem_mins}m"

class TransferMonitor:
    def __init__(self, rc_url: str = "http://127.0.0.1:5572"):
        self.rc_url = rc_url.rstrip("/")
        self._lock = threading.Lock()
        self._cached_stats = self._get_default_stats()
        self._is_running = True

        # Jalankan pemantau di background thread agar UI thread 100% bebas lag
        self._worker_thread = threading.Thread(target=self._background_worker, daemon=True)
        self._worker_thread.start()

    def _get_default_stats(self) -> dict:
        return {
            "is_connected": False,
            "is_uploading": False,
            "speed": 0,
            "speed_str": "0 B/s",
            "bytes_transferred": 0,
            "total_bytes": 0,
            "transferred_str": "0 B",
            "total_bytes_str": "0 B",
            "overall_percent": 0,
            "transfers_completed": 0,
            "errors": 0,
            "transferring": [],
            "queued": []
        }

    def get_stats(self) -> dict:
        """
        Mengembalikan statistik transfer terkini secara instan dari memori cache (0ms lag).
        Tidak pernah memblokir thread UI.
        """
        with self._lock:
            return dict(self._cached_stats)

    def _background_worker(self):
        while self._is_running:
            # 1. Jika rclone tidak jalan, jangan lakukan panggilan socket/jaringan sama sekali
            if not is_rclone_process_active():
                with self._lock:
                    self._cached_stats = self._get_default_stats()
                time.sleep(1.5)
                continue

            # 2. Jika rclone aktif, baru ambil data dari RC API
            try:
                # Ambil core stats
                req_stats = urllib.request.Request(
                    f"{self.rc_url}/core/stats",
                    data=b"{}",
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req_stats, timeout=1.0) as resp:
                    stats_data = json.loads(resp.read().decode("utf-8"))

                # Ambil vfs queue untuk mengetahui file yang sedang mengantri
                queue_data = {}
                try:
                    req_queue = urllib.request.Request(
                        f"{self.rc_url}/vfs/queue",
                        data=b"{}",
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req_queue, timeout=1.0) as resp:
                        queue_data = json.loads(resp.read().decode("utf-8"))
                except Exception:
                    pass

                parsed = self._parse_api_response(stats_data, queue_data)
                with self._lock:
                    self._cached_stats = parsed
            except Exception:
                # Gagal connect ke port RC (misal rclone baru start/stop)
                with self._lock:
                    self._cached_stats = self._get_default_stats()

            time.sleep(1.0)

    def _parse_api_response(self, data: dict, queue_data: dict | None = None) -> dict:
        transferring_raw = data.get("transferring") or []
        transferring_items = []
        active_names = set()

        for item in transferring_raw:
            item_name = item.get("name", "Unknown File")
            active_names.add(item_name)
            item_bytes = item.get("bytes", 0)
            item_size = item.get("size", 0)
            item_percent = item.get("percentage", 0)
            if item_size > 0 and item_percent == 0 and item_bytes > 0:
                item_percent = int((item_bytes / item_size) * 100)

            item_speed = item.get("speed", 0)
            item_eta = item.get("eta")

            transferring_items.append({
                "name": item_name,
                "bytes": item_bytes,
                "size": item_size,
                "bytes_str": format_bytes(item_bytes),
                "size_str": format_bytes(item_size),
                "percentage": item_percent,
                "speed": item_speed,
                "speed_str": f"{format_bytes(item_speed)}/s",
                "eta": item_eta,
                "eta_str": format_eta(item_eta)
            })

        # Parse daftar file yang sedang antre menunggu giliran upload
        queued_items = []
        if queue_data and isinstance(queue_data.get("queue"), list):
            for q_item in queue_data.get("queue"):
                q_name = q_item.get("name", "")
                if not q_name:
                    continue
                # Lewati file yang sedang aktif diupload
                if q_item.get("uploading") or q_name in active_names:
                    continue
                q_size = q_item.get("size", 0)
                queued_items.append({
                    "name": q_name,
                    "size": q_size,
                    "size_str": format_bytes(q_size),
                    "id": q_item.get("id"),
                    "expiry": q_item.get("expiry"),
                    "tries": q_item.get("tries", 0)
                })

        is_uploading = len(transferring_items) > 0
        has_queue = len(queued_items) > 0
        speed = data.get("speed", 0) if is_uploading else 0
        bytes_transferred = data.get("bytes", 0)
        total_bytes = data.get("totalBytes", 0)
        overall_percent = 0
        if total_bytes > 0:
            overall_percent = min(100, int((bytes_transferred / total_bytes) * 100))

        return {
            "is_connected": True,
            "is_uploading": is_uploading,
            "has_queue": has_queue,
            "speed": speed,
            "speed_str": f"{format_bytes(speed)}/s" if is_uploading else "0 B/s",
            "bytes_transferred": bytes_transferred,
            "total_bytes": total_bytes,
            "transferred_str": format_bytes(bytes_transferred),
            "total_bytes_str": format_bytes(total_bytes),
            "overall_percent": overall_percent,
            "transfers_completed": data.get("transfers", 0),
            "errors": data.get("errors", 0),
            "transferring": transferring_items,
            "queued": queued_items
        }

    def stop(self):
        self._is_running = False
