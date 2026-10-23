import json
import subprocess
import os
from .system_detector import find_rclone_binary
from .config_manager import get_default_config_path

class RcloneExecutor:
    def __init__(self, rclone_path: str | None = None, config_path: str | None = None):
        self.rclone_path = rclone_path or find_rclone_binary() or "rclone"
        self.config_path = config_path or get_default_config_path()

    def check_remote_quota(self, remote_name: str) -> dict:
        """
        Mengecek kuota dan keabsahan token untuk remote tertentu via 'rclone about'.
        Mengembalikan kamus:
        {
            "ok": True/False,
            "total": int,
            "used": int,
            "free": int,
            "error": str
        }
        """
        clean_name = remote_name.strip().rstrip(":") + ":"
        cmd = [
            self.rclone_path,
            "about",
            clean_name,
            "--json",
            "--config",
            self.config_path
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if res.returncode == 0:
                # Kadang ada baris NOTICE sebelum JSON, cari tanda kurung kurawal pertama
                stdout = res.stdout.strip()
                json_start = stdout.find("{")
                if json_start != -1:
                    json_str = stdout[json_start:]
                    data = json.loads(json_str)
                    return {
                        "ok": True,
                        "total": data.get("total", 0),
                        "used": data.get("used", 0),
                        "free": data.get("free", 0),
                        "error": ""
                    }
                return {"ok": True, "total": 0, "used": 0, "free": 0, "error": ""}
            else:
                error_output = res.stderr or res.stdout
                is_auth_error = "401" in error_output or "authError" in error_output or "Invalid Credentials" in error_output
                err_msg = "Token Expired / Perlu Login Ulang" if is_auth_error else error_output.split("\n")[0]
                return {
                    "ok": False,
                    "total": 0,
                    "used": 0,
                    "free": 0,
                    "error": err_msg
                }
        except subprocess.TimeoutExpired:
            return {"ok": False, "total": 0, "used": 0, "free": 0, "error": "Koneksi timeout"}
        except Exception as e:
            return {"ok": False, "total": 0, "used": 0, "free": 0, "error": str(e)}

    def check_union_health(self, union_name: str) -> tuple[bool, str]:
        """Memeriksa apakah remote union bisa dibaca (semua upstream aktif)."""
        clean_name = union_name.strip().rstrip(":") + ":"
        cmd = [
            self.rclone_path,
            "lsd",
            clean_name,
            "--max-depth", "1",
            "--config",
            self.config_path
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if res.returncode == 0:
                return True, "Semua akun terhubung! Siap di-mount."
            err = (res.stderr or res.stdout).strip()
            if "401" in err or "Invalid Credentials" in err:
                return False, "Salah satu akun dalam union expired/perlu login ulang di tab Akun GDrive."
            # Ambil pesan error relevan
            lines = [l for l in err.splitlines() if not l.startswith("202") or "ERROR" in l or "CRITICAL" in l]
            clean_err = lines[-1] if lines else err[:80]
            return False, clean_err
        except subprocess.TimeoutExpired:
            return False, "Koneksi Google timeout (jaringan lambat). Silakan klik Uji lagi."
        except Exception as e:
            return False, f"Kendala koneksi: {e}"

    def launch_reconnect_flow(self, remote_name: str) -> subprocess.Popen:
        """
        Membuka jendela konsol bantuan untuk proses OAuth Google di browser.
        Menggunakan batch script sementara agar tidak terkena bug quoting cmd.exe pada path berspasi.
        """
        import tempfile
        clean_name = remote_name.strip().rstrip(":")
        temp_dir = tempfile.gettempdir()
        bat_file = os.path.join(temp_dir, f"rclone_reconnect_{clean_name}.bat")

        bat_content = f"""@echo off
title Login Ulang Google Drive: {clean_name}
color 0E
echo ======================================================================
echo  MENGHUBUNGKAN KEMBALI AKUN: {clean_name}
echo ======================================================================
echo.
echo Browser akan terbuka otomatis untuk otentikasi ulang Google kamu.
echo Silakan login dan berikan izin akses (Allow).
echo.
echo ======================================================================
echo.

"{self.rclone_path}" config reconnect "{clean_name}:" --config "{self.config_path}"

echo.
if errorlevel 1 (
    color 0C
    echo ======================================================================
    echo [!] Terjadi kesalahan atau otentikasi dibatalkan.
    echo ======================================================================
) else (
    color 0A
    echo ======================================================================
    echo [V] SUKSES! Token akun "{clean_name}" berhasil diperbarui!
    echo ======================================================================
)
echo.
echo Tekan sembarang tombol untuk menutup jendela ini...
pause >nul
"""
        with open(bat_file, "w", encoding="utf-8") as f:
            f.write(bat_content)

        proc = subprocess.Popen(["cmd.exe", "/c", bat_file], creationflags=subprocess.CREATE_NEW_CONSOLE)
        return proc

    def launch_add_account_flow(self, remote_name: str) -> subprocess.Popen:
        """
        Membuka alur penambahan akun Google Drive baru via browser OAuth.
        Menggunakan batch script sementara agar tidak terkena bug quoting cmd.exe pada path berspasi.
        """
        import tempfile
        clean_name = remote_name.strip().rstrip(":")
        temp_dir = tempfile.gettempdir()
        bat_file = os.path.join(temp_dir, f"rclone_add_{clean_name}.bat")

        bat_content = f"""@echo off
title Menambahkan Akun Google Drive: {clean_name}
color 0B
echo ======================================================================
echo  MENYIAPKAN OTENTIKASI GOOGLE DRIVE: {clean_name}
echo ======================================================================
echo.
echo Browser akan terbuka otomatis untuk login ke akun Google kamu.
echo Silakan berikan izin akses (Allow) pada halaman browser tersebut.
echo.
echo Jika browser tidak otomatis terbuka, salin link URL yang muncul di bawah:
echo ======================================================================
echo.

"{self.rclone_path}" config create "{clean_name}" drive scope drive config_is_local true --config "{self.config_path}"

echo.
if errorlevel 1 (
    color 0C
    echo ======================================================================
    echo [!] Terjadi kesalahan atau pendaftaran akun dibatalkan.
    echo ======================================================================
) else (
    color 0A
    echo ======================================================================
    echo [V] SUKSES! Akun "{clean_name}" berhasil didaftarkan ke Rclone!
    echo ======================================================================
)
echo.
echo Tekan sembarang tombol untuk menutup jendela ini...
pause >nul
"""
        with open(bat_file, "w", encoding="utf-8") as f:
            f.write(bat_content)

        proc = subprocess.Popen(["cmd.exe", "/c", bat_file], creationflags=subprocess.CREATE_NEW_CONSOLE)
        return proc
