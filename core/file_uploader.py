import os
import shutil
import threading
import time
import json
import urllib.request
from typing import Callable, List, Optional
from .settings_store import load_settings

def purge_file_and_cache(file_path: str, cache_dir: str = "", remote_name: str = ""):
    """
    Menghapus file dari drive virtual dan membersihkan cache VFS rclone terkait seketika.
    Menghentikan antrean upload Rclone yang sedang berjalan untuk file tersebut.
    """
    # 1. Hapus file di virtual drive jika ada
    if os.path.exists(file_path):
        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path, ignore_errors=True)
            else:
                os.remove(file_path)
        except Exception:
            pass

    # 2. Ambil path cache dan remote union jika tidak diberikan
    st = load_settings()
    actual_cache_dir = cache_dir or st.get("cache_dir", "")
    actual_remote = remote_name or st.get("union_remote", "Gdrive_union")

    file_name = os.path.basename(file_path)

    # 3. Hapus langsung file dari direktori vfs dan vfsMeta di disk cache
    if actual_cache_dir and actual_remote:
        for folder in ["vfs", "vfsMeta"]:
            target_cache = os.path.join(actual_cache_dir, folder, actual_remote, file_name)
            if os.path.exists(target_cache):
                try:
                    if os.path.isdir(target_cache):
                        shutil.rmtree(target_cache, ignore_errors=True)
                    else:
                        os.remove(target_cache)
                except Exception:
                    pass

    # 4. Beritahu Rclone via RC API untuk melupakan file dari antrean upload VFS
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:5572/vfs/forget",
            data=json.dumps({"file": file_name}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=1.5)
    except Exception:
        pass


class FileUploader:
    """
    Menyalin file/folder dari lokal ke Drive-Chan secara aman di latar belakang.
    Mencegah Windows Explorer macet/hang (Not Responding) saat menyalin file besar.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._is_uploading = False
        self._cancel_requested = False
        self._current_dest_path: Optional[str] = None
        self._worker_thread: Optional[threading.Thread] = None

    @property
    def is_busy(self) -> bool:
        with self._lock:
            return self._is_uploading

    def cancel(self):
        with self._lock:
            self._cancel_requested = True
            dest = self._current_dest_path

        # Jika ada file yang sedang disalin sebagian, bersihkan seketika
        if dest:
            purge_file_and_cache(dest)

    def upload_async(
        self,
        sources: List[str],
        target_dir: str,
        on_progress: Optional[Callable[[str, int, int, float], None]] = None,
        on_complete: Optional[Callable[[bool, str], None]] = None
    ) -> bool:
        """
        Memulai proses penyalinan asinkron.
        on_progress(current_file_name, copied_bytes, total_bytes, speed_bps)
        on_complete(success, message)
        """
        with self._lock:
            if self._is_uploading:
                return False
            self._is_uploading = True
            self._cancel_requested = False
            self._current_dest_path = None

        self._worker_thread = threading.Thread(
            target=self._run_copy,
            args=(sources, target_dir, on_progress, on_complete),
            daemon=True
        )
        self._worker_thread.start()
        return True

    def _run_copy(self, sources, target_dir, on_progress, on_complete):
        active_dest = None
        try:
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            # 1. Hitung total ukuran seluruh file
            total_bytes = 0
            file_queue = []

            for src in sources:
                if not os.path.exists(src):
                    continue
                if os.path.isfile(src):
                    size = os.path.getsize(src)
                    total_bytes += size
                    dest = os.path.join(target_dir, os.path.basename(src))
                    file_queue.append((src, dest, size))
                elif os.path.isdir(src):
                    dir_name = os.path.basename(src.rstrip("\\/"))
                    base_dest_dir = os.path.join(target_dir, dir_name)
                    for root, _, files in os.walk(src):
                        rel = os.path.relpath(root, src)
                        dest_sub = os.path.join(base_dest_dir, rel) if rel != "." else base_dest_dir
                        os.makedirs(dest_sub, exist_ok=True)
                        for f in files:
                            f_src = os.path.join(root, f)
                            f_size = os.path.getsize(f_src)
                            total_bytes += f_size
                            file_queue.append((f_src, os.path.join(dest_sub, f), f_size))

            if not file_queue:
                if on_complete:
                    on_complete(True, "Tidak ada file yang disalin.")
                return

            overall_copied = 0
            start_time = time.time()
            chunk_size = 4 * 1024 * 1024  # 4 MB chunk buffer

            for src_path, dest_path, file_size in file_queue:
                if self._cancel_requested:
                    break

                active_dest = dest_path
                with self._lock:
                    self._current_dest_path = dest_path

                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                file_copied = 0

                with open(src_path, "rb") as f_in, open(dest_path, "wb") as f_out:
                    while True:
                        if self._cancel_requested:
                            break
                        chunk = f_in.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        chunk_len = len(chunk)
                        file_copied += chunk_len
                        overall_copied += chunk_len

                        if on_progress:
                            elapsed = max(0.1, time.time() - start_time)
                            speed = overall_copied / elapsed
                            on_progress(os.path.basename(src_path), overall_copied, total_bytes, speed)

                if self._cancel_requested:
                    # Bersihkan file parsial & cache seketika
                    purge_file_and_cache(dest_path)
                    break



            with self._lock:
                self._current_dest_path = None

            if self._cancel_requested:
                if active_dest:
                    purge_file_and_cache(active_dest)
                if on_complete:
                    on_complete(False, "Proses salin dibatalkan dan file sementara/cache telah dihapus bersih.")
            else:
                if on_complete:
                    on_complete(True, f"Berhasil menyalin {len(file_queue)} file ke AHA DRIVE!")

        except Exception as e:
            if active_dest and self._cancel_requested:
                purge_file_and_cache(active_dest)
            if on_complete:
                on_complete(False, f"Gagal menyalin file: {e}")
        finally:
            with self._lock:
                self._is_uploading = False
                self._current_dest_path = None
