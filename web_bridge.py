# -*- coding: utf-8 -*-
"""
Web Bridge API for AHA DRIVE Astral Engine
Exposes core Python functionalities to Modern Web UI (HTML/CSS/JS) via pywebview js_api
"""

import os
import sys
import time
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog
from core import (
    find_rclone_binary,
    is_winfsp_installed,
    get_available_drive_letters,
    get_disk_space_info,
    get_recommended_cache_dir,
    get_directory_size,
    format_bytes,
    RcloneConfigManager,
    RcloneExecutor,
    MountManager,
    TransferMonitor,
    FileUploader,
    purge_file_and_cache
)
from core.settings_store import load_settings, save_settings, clean_volume_name
from core.mount_manager import get_default_log_path

class WebBridgeAPI:
    def __init__(self):
        self.rclone_bin = find_rclone_binary()
        self.winfsp_ok = is_winfsp_installed()
        self.config_mgr = RcloneConfigManager()
        self.executor = RcloneExecutor(rclone_path=self.rclone_bin)
        self.mount_mgr = MountManager(rclone_path=self.rclone_bin)
        self.transfer_monitor = TransferMonitor()
        self.uploader = FileUploader()

        # Local stage-1 upload tracking
        self.stage1_status = {
            "is_busy": False,
            "current_file": "",
            "percentage": 0,
            "copied_str": "0 B",
            "total_str": "0 B",
            "speed_str": "0 B/s",
            "success": None,
            "message": "",
            "completed_at": 0
        }

    # ==================== SYSTEM & DASHBOARD ====================

    def get_system_info(self):
        return {
            "rclone_ready": bool(self.rclone_bin),
            "rclone_path": self.rclone_bin or "Not Found",
            "winfsp_ready": self.winfsp_ok
        }

    def get_dashboard_status(self):
        settings = load_settings()
        letter = settings.get("drive_letter", "G").strip().rstrip(":").upper()
        volume = settings.get("volume_name", "AHA DRIVE")
        remote = settings.get("union_remote", "Gdrive_union")
        cache_dir = settings.get("cache_dir", get_recommended_cache_dir())

        is_running = self.mount_mgr.is_process_running()
        is_live = self.mount_mgr.is_drive_active(letter)
        is_mounted = is_running or is_live

        cache_bytes = get_directory_size(cache_dir)
        cache_used_str = format_bytes(cache_bytes)
        disk_info = get_disk_space_info(cache_dir)

        is_autostart = self.mount_mgr.is_startup_enabled()

        return {
            "is_mounted": is_mounted,
            "remote": remote,
            "drive_letter": f"{letter}:",
            "volume_name": volume,
            "cache_dir": cache_dir,
            "cache_used": cache_used_str,
            "disk_free": disk_info["free_str"],
            "disk_free_gb": disk_info["free_gb"],
            "disk_critical": disk_info["free_gb"] < 5.0,
            "auto_start": is_autostart,
            "rclone_ready": bool(self.rclone_bin),
            "winfsp_ready": self.winfsp_ok
        }

    def toggle_mount(self):
        settings = load_settings()
        letter = settings.get("drive_letter", "G").strip().rstrip(":").upper()
        is_running = self.mount_mgr.is_process_running() or self.mount_mgr.is_drive_active(letter)

        if is_running:
            self.mount_mgr.stop_mount()
            return {"status": "unmounted", "message": "Virtual drive berhasil dilepas."}
        else:
            remote = settings.get("union_remote", "Gdrive_union")
            cache_dir = settings.get("cache_dir", "")
            cache_size = settings.get("cache_max_size", "10G")
            vol_name = settings.get("volume_name", "AHA DRIVE")

            ok, msg = self.mount_mgr.start_mount(
                remote_name=remote,
                drive_letter=letter,
                cache_dir=cache_dir,
                cache_max_size=cache_size,
                volume_name=vol_name
            )
            return {"status": "mounted" if ok else "error", "message": msg}

    def open_explorer(self):
        settings = load_settings()
        letter = settings.get("drive_letter", "G").strip().rstrip(":").upper()
        drive_path = f"{letter}:\\"
        if os.path.exists(drive_path):
            subprocess.Popen(["explorer.exe", drive_path])
            return True
        return False

    def toggle_autostart(self, enabled: bool):
        settings = load_settings()
        settings["auto_start"] = bool(enabled)
        save_settings(settings)

        self.mount_mgr.set_startup_enabled(
            enabled=bool(enabled),
            remote_name=settings.get("union_remote", "Gdrive_union"),
            drive_letter=settings.get("drive_letter", "G"),
            cache_dir=settings.get("cache_dir", ""),
            cache_max_size=settings.get("cache_max_size", "10G"),
            volume_name=settings.get("volume_name", "AHA DRIVE")
        )
        return True

    # ==================== TRANSFERS & DISPATCH ====================

    def get_transfer_telemetry(self):
        stats = self.transfer_monitor.get_stats()
        # Auto-expire completed stage1 status after 4.5 seconds on backend to prevent infinite loop
        if self.stage1_status.get("success") is not None and not self.stage1_status.get("is_busy"):
            completed_at = self.stage1_status.get("completed_at", 0)
            if completed_at > 0 and (time.time() - completed_at > 4.5):
                self.stage1_status["success"] = None
                self.stage1_status["message"] = ""
                self.stage1_status["percentage"] = 0

        # Merge with local stage 1
        stats["stage1"] = self.stage1_status
        return stats

    def ack_stage1_done(self):
        self.stage1_status["success"] = None
        self.stage1_status["message"] = ""
        self.stage1_status["percentage"] = 0
        return True

    def pick_files(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        files = filedialog.askopenfilenames(
            title="Pilih File untuk Diunggah ke AHA DRIVE",
            filetypes=[("Semua File", "*.*")]
        )
        root.destroy()
        return list(files) if files else []

    def pick_folder(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(title="Pilih Folder untuk Diunggah ke AHA DRIVE")
        root.destroy()
        return folder if folder else ""

    def start_upload(self, paths: list, target_subfolder: str = ""):
        if self.uploader.is_busy:
            return {"ok": False, "message": "Proses salin lain sedang berjalan."}

        settings = load_settings()
        letter = settings.get("drive_letter", "G").strip().rstrip(":")
        base_dir = f"{letter}:\\"
        if target_subfolder and target_subfolder.startswith(base_dir):
            target_dir = target_subfolder
        else:
            target_dir = base_dir

        if not os.path.exists(target_dir):
            return {"ok": False, "message": f"Drive virtual {target_dir} belum terpasang!"}

        self.stage1_status = {
            "is_busy": True,
            "current_file": "Menyiapkan...",
            "percentage": 0,
            "copied_str": "0 B",
            "total_str": "0 B",
            "speed_str": "0 B/s",
            "success": None,
            "message": "Menyalin file ke buffer lokal...",
            "completed_at": 0
        }

        def on_prog(cur, copied, total, spd):
            pct = int((copied / total if total > 0 else 0) * 100)
            self.stage1_status.update({
                "is_busy": True,
                "current_file": cur,
                "percentage": pct,
                "copied_str": format_bytes(copied),
                "total_str": format_bytes(total),
                "speed_str": f"{format_bytes(spd)}/s"
            })

        def on_done(ok, msg):
            self.stage1_status.update({
                "is_busy": False,
                "percentage": 100 if ok else 0,
                "success": ok,
                "message": msg,
                "completed_at": time.time()
            })

        self.uploader.upload_async(
            sources=paths,
            target_dir=target_dir,
            on_progress=on_prog,
            on_complete=on_done
        )
        return {"ok": True, "message": "Proses salin dimulai."}

    def cancel_stage1_upload(self):
        self.uploader.cancel()
        self.stage1_status.update({
            "is_busy": False,
            "success": False,
            "message": "Dibatalkan oleh pengguna.",
            "completed_at": time.time()
        })
        return True

    def cancel_cloud_file(self, file_name: str):
        settings = load_settings()
        letter = settings.get("drive_letter", "G").strip().rstrip(":")
        target_path = os.path.join(f"{letter}:\\", file_name)
        def _bg():
            purge_file_and_cache(target_path)
        threading.Thread(target=_bg, daemon=True).start()
        return True

    # ==================== ACCOUNTS ====================

    def get_accounts_list(self):
        return self.config_mgr.get_gdrive_remotes()

    def check_all_quotas(self):
        remotes = self.config_mgr.get_gdrive_remotes()
        results = {}
        for r in remotes:
            q = self.executor.check_remote_quota(r)
            if q["ok"]:
                results[r] = {
                    "ok": True,
                    "total": format_bytes(q["total"]),
                    "used": format_bytes(q["used"]),
                    "free": format_bytes(q["free"]),
                    "used_percent": int((q["used"] / q["total"]) * 100) if q["total"] > 0 else 0
                }
            else:
                results[r] = {
                    "ok": False,
                    "error": q.get("error", "Error koneksi / token expired")
                }
        return results

    def add_account(self, name: str):
        clean_name = name.strip().replace(" ", "_")
        if not clean_name:
            return {"ok": False, "message": "Nama akun tidak boleh kosong."}

        proc = self.executor.launch_add_account_flow(clean_name)
        return {"ok": True, "message": "Browser autentikasi Google Drive telah dibuka."}

    def reconnect_account(self, name: str):
        proc = self.executor.launch_reconnect_flow(name)
        return {"ok": True, "message": f"Browser login ulang untuk '{name}' telah dibuka."}

    def delete_account(self, name: str):
        ok = self.config_mgr.delete_remote(name)
        return {"ok": ok}

    # ==================== UNION POOL ====================

    def get_union_data(self):
        settings = load_settings()
        target_union = settings.get("union_remote", "Gdrive_union")
        remotes = self.config_mgr.get_all_remotes()
        current_upstreams = []
        current_policy = settings.get("create_policy", "epmfs")

        if target_union in remotes and remotes[target_union]["type"] == "union":
            current_upstreams = remotes[target_union].get("upstreams", [])
            current_policy = remotes[target_union].get("create_policy", current_policy)

        all_gdrives = self.config_mgr.get_gdrive_remotes()

        return {
            "union_name": target_union,
            "policy": current_policy,
            "upstreams": current_upstreams,
            "all_accounts": all_gdrives
        }

    def save_union_config(self, union_name: str, selected_accounts: list, policy: str):
        if not selected_accounts:
            return {"ok": False, "message": "Pilih minimal 1 akun untuk digabung!"}

        ok = self.config_mgr.set_union_remote(union_name, selected_accounts, create_policy=policy)
        if ok:
            settings = load_settings()
            settings["union_remote"] = union_name
            settings["create_policy"] = policy
            save_settings(settings)
            return {"ok": True, "message": f"Konfigurasi Union '{union_name}' tersimpan!"}
        return {"ok": False, "message": "Gagal menyimpan konfigurasi rclone."}

    def test_union_health(self, union_name: str):
        ok, msg = self.executor.check_union_health(union_name)
        return {"ok": ok, "message": msg}

    # ==================== SETTINGS & LOGS ====================

    def get_settings(self):
        settings = load_settings()
        letters = get_available_drive_letters()
        cur_letter = settings.get("drive_letter", "G").strip().rstrip(":").upper()
        if cur_letter not in letters:
            letters.append(cur_letter)
        letters.sort()

        cache_dir = settings.get("cache_dir", get_recommended_cache_dir())
        disk_info = get_disk_space_info(cache_dir)
        cache_bytes = get_directory_size(cache_dir)

        return {
            "drive_letter": cur_letter,
            "available_letters": letters,
            "volume_name": settings.get("volume_name", "AHA DRIVE"),
            "cache_dir": cache_dir,
            "cache_used": format_bytes(cache_bytes),
            "cache_max_size": settings.get("cache_max_size", "10G"),
            "cache_max_age": settings.get("cache_max_age", "24h"),
            "disk_free": disk_info["free_str"],
            "disk_total": disk_info["total_str"],
            "disk_free_gb": disk_info["free_gb"]
        }

    def save_settings(self, new_settings: dict):
        settings = load_settings()
        settings["drive_letter"] = new_settings.get("drive_letter", "G").replace(":", "").strip().upper()
        settings["volume_name"] = clean_volume_name(new_settings.get("volume_name", "AHA DRIVE"))
        settings["cache_dir"] = new_settings.get("cache_dir", get_recommended_cache_dir())
        settings["cache_max_size"] = new_settings.get("cache_max_size", "10G")
        settings["cache_max_age"] = new_settings.get("cache_max_age", "24h")
        save_settings(settings)
        return {"ok": True, "message": "Pengaturan berhasil disimpan."}

    def browse_cache_folder(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(title="Pilih Folder Cache Rclone")
        root.destroy()
        return folder if folder else ""

    def open_folder(self, path: str):
        if os.path.exists(path):
            subprocess.Popen(["explorer.exe", path])
            return True
        return False

    def get_logs(self):
        log_path = get_default_log_path()
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception as e:
                return f"Error membaca log: {e}"
        return "Belum ada file log yang tercatat."

    def clear_logs(self):
        log_path = get_default_log_path()
        if os.path.exists(log_path):
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
                return True
            except Exception:
                pass
        return False

    def open_log_folder(self):
        log_path = get_default_log_path()
        log_dir = os.path.dirname(log_path)
        if os.path.exists(log_dir):
            subprocess.Popen(["explorer.exe", log_dir])
            return True
        return False
