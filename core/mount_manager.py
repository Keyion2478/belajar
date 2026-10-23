import os
import subprocess
import signal
import psutil
import winreg
import ctypes
from .system_detector import find_rclone_binary
from .config_manager import get_default_config_path

def delete_reg_key_tree(root, subkey: str):
    """Menghapus kunci registry beserta seluruh subkey di dalamnya secara rekursif."""
    try:
        key = winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        return
    while True:
        try:
            sub = winreg.EnumKey(key, 0)
            delete_reg_key_tree(root, f"{subkey}\\{sub}")
        except OSError:
            break
    winreg.CloseKey(key)
    try:
        winreg.DeleteKey(root, subkey)
    except Exception:
        pass

def update_explorer_drive_label(drive_letter: str, volume_name: str):
    """Menyetel label drive di registry Windows agar Explorer menampilkannya dengan rapi sebagai harddisk lokal."""
    try:
        clean_let = drive_letter.strip().rstrip(":").upper()

        # 1. Set label untuk letter di MountPoints2
        k1 = winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\{clean_let}")
        winreg.SetValueEx(k1, "_LabelFromReg", 0, winreg.REG_SZ, volume_name)

        # 2. Set label di DriveIcons agar Windows Explorer menampilkan nama kustom di "Devices and drives"
        k_icon = winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\{clean_let}\DefaultLabel")
        winreg.SetValueEx(k_icon, "", 0, winreg.REG_SZ, volume_name)

        # 3. Hapus SEMUA ghost network share (##server#...) dari MountPoints2 agar tidak muncul icon silang merah
        base = r"Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2"
        try:
            root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, base)
            ghosts = []
            for i in range(200):
                try:
                    sub = winreg.EnumKey(root, i)
                    if sub.startswith("##server#") or ">" in sub or "<" in sub:
                        ghosts.append(sub)
                except OSError:
                    break
            winreg.CloseKey(root)
            for g in ghosts:
                delete_reg_key_tree(winreg.HKEY_CURRENT_USER, rf"{base}\{g}")
        except Exception:
            pass
    except Exception:
        pass

    try:
        # Refresh cache shell Windows Explorer
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x1000, None, None)
        ctypes.windll.shell32.SHChangeNotify(0x00000100, 0x1000, None, None)
    except Exception:
        pass

def get_startup_folder() -> str:
    """Mengambil folder Startup Windows pengguna saat ini."""
    app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")

def get_default_log_path() -> str:
    """Mengambil lokasi file log default."""
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    log_dir = os.path.join(local_app_data, "rclone", "logs")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "mount.log")

class MountManager:
    def __init__(self, rclone_path: str | None = None, config_path: str | None = None):
        self.rclone_path = rclone_path or find_rclone_binary() or "rclone"
        self.config_path = config_path or get_default_config_path()
        self.current_process: subprocess.Popen | None = None

    def is_process_running(self) -> bool:
        """Mengecek apakah proses rclone mount sedang berjalan di latar belakang sistem."""
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                name = p.info.get('name') or ""
                if "rclone" in name.lower():
                    cmdline = p.info.get('cmdline') or []
                    if any("mount" in str(arg).lower() for arg in cmdline):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def is_drive_active(self, drive_letter: str) -> bool:
        """Mengecek apakah huruf drive yang dituju sudah aktif dan bisa diakses."""
        clean_letter = drive_letter.strip().rstrip(":").upper()
        drive_root = f"{clean_letter}:\\"
        return os.path.exists(drive_root)

    def start_mount(
        self,
        remote_name: str,
        drive_letter: str,
        cache_dir: str,
        cache_max_size: str = "10G",
        volume_name: str = "Google Drive",
        log_path: str | None = None
    ) -> tuple[bool, str]:
        """
        Menjalankan proses mount rclone di latar belakang tanpa jendela hitam (silent).
        """
        if self.is_process_running():
            return False, "Proses Rclone mount sudah aktif berjalan."

        clean_remote = remote_name.strip().rstrip(":") + ":"
        clean_letter = drive_letter.strip().rstrip(":").upper() + ":"
        actual_log = log_path or get_default_log_path()

        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(os.path.dirname(actual_log), exist_ok=True)

        safe_volume = "".join(c for c in str(volume_name) if c not in '<>:"/\\|?*').strip() or "AHA DRIVE"

        cmd = [
            self.rclone_path,
            "mount",
            clean_remote,
            clean_letter,
            "--config", self.config_path,
            "--rc",
            "--rc-no-auth",
            "--rc-addr", "127.0.0.1:5572",
            "--vfs-cache-mode", "full",
            "--vfs-links",
            "--cache-dir", cache_dir,
            "--vfs-cache-max-size", cache_max_size,
            "--vfs-cache-max-age", "24h",
            "--vfs-write-back", "5s",
            "--transfers", "1",
            "--drive-chunk-size", "64M",
            "--buffer-size", "32M",
            "--volname", safe_volume,
            "--log-file", actual_log,
            "--log-level", "INFO"
        ]

        try:
            self.current_process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
            update_explorer_drive_label(clean_letter, safe_volume)
            return True, f"Mount berhasil dimulai pada {clean_letter}"
        except Exception as e:
            return False, f"Gagal memulai mount: {e}"

    def stop_mount(self) -> tuple[bool, str]:
        """Menghentikan seluruh proses rclone mount di sistem."""
        killed = False
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                name = p.info.get('name') or ""
                if "rclone" in name.lower():
                    cmdline = p.info.get('cmdline') or []
                    if any("mount" in str(arg).lower() for arg in cmdline):
                        p.terminate()
                        try:
                            p.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            p.kill()
                        killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed:
            self.current_process = None
            try:
                ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x1000, None, None)
            except Exception:
                pass
            return True, "Mount berhasil dihentikan."
        return False, "Tidak ada proses rclone mount yang sedang aktif."

    def is_startup_enabled(self) -> bool:
        """Cek apakah auto-start di folder Startup Windows aktif."""
        startup_file = os.path.join(get_startup_folder(), "RcloneAutoMount.vbs")
        return os.path.exists(startup_file)

    def set_startup_enabled(
        self,
        enabled: bool,
        remote_name: str,
        drive_letter: str,
        cache_dir: str,
        cache_max_size: str,
        volume_name: str
    ) -> bool:
        """
        Menyalakan atau mematikan otomatisasi mount saat booting Windows
        melalui file silent VBScript di folder Startup pengguna.
        """
        startup_file = os.path.join(get_startup_folder(), "RcloneAutoMount.vbs")

        if not enabled:
            if os.path.exists(startup_file):
                try:
                    os.remove(startup_file)
                    return True
                except OSError:
                    return False
            return True

        # Generate silent VBScript
        clean_remote = remote_name.strip().rstrip(":") + ":"
        clean_letter = drive_letter.strip().rstrip(":").upper() + ":"
        log_path = get_default_log_path()

        # Gunakan path yang sudah divalidasi tanpa typo
        safe_volume = "".join(c for c in str(volume_name) if c not in '<>:"/\\|?*').strip() or "AHA DRIVE"
        vbs_content = (
            'Set shell = CreateObject("WScript.Shell")\n'
            f'command = """{self.rclone_path}"" mount {clean_remote} {clean_letter} '
            f'--config ""{self.config_path}"" --rc --rc-no-auth --rc-addr 127.0.0.1:5572 '
            f'--vfs-cache-mode full --vfs-links '
            f'--cache-dir ""{cache_dir}"" --vfs-cache-max-size {cache_max_size} '
            f'--vfs-cache-max-age 24h --vfs-write-back 5s --buffer-size 32M '
            f'--volname ""{safe_volume}"" '
            f'--log-file ""{log_path}"" --log-level INFO"\n'
            'shell.Run command, 0, False\n'
        )

        try:
            os.makedirs(os.path.dirname(startup_file), exist_ok=True)
            with open(startup_file, "w", encoding="utf-8") as f:
                f.write(vbs_content)
            return True
        except Exception:
            return False
