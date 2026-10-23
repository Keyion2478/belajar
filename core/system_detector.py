import os
import shutil
import string
import winreg
import psutil

def format_bytes(size_bytes: int) -> str:
    """Format bytes ke string yang mudah dibaca manusia (B, KB, MB, GB, TB)."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"

def get_directory_size(path: str) -> int:
    """Menghitung total ukuran file di dalam direktori (dalam bytes)."""
    if not os.path.exists(path):
        return 0
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += get_directory_size(entry.path)
            except (PermissionError, FileNotFoundError):
                continue
    except (PermissionError, FileNotFoundError):
        pass
    return total

def find_rclone_binary() -> str | None:
    """Mencari lokasi binary rclone.exe di sistem."""
    which_path = shutil.which("rclone")
    if which_path and os.path.exists(which_path):
        return which_path

    common_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\rclone.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\rclone\rclone.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\rclone\rclone.exe"),
        os.path.expandvars(r"%USERPROFILE%\rclone\rclone.exe"),
        r"C:\rclone\rclone.exe",
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None

def is_winfsp_installed() -> bool:
    """Mengecek apakah driver WinFsp terpasang dan aktif."""
    # 1. Cek registry
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for subkey in (r"SOFTWARE\WinFsp", r"SOFTWARE\WOW6432Node\WinFsp"):
            try:
                with winreg.OpenKey(root, subkey):
                    return True
            except OSError:
                pass

    # 2. Cek file biner launcher WinFsp
    common_files = [
        os.path.expandvars(r"%PROGRAMFILES%\WinFsp\bin\launcher-x64.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\WinFsp\bin\launcher-x86.exe"),
    ]
    for path in common_files:
        if os.path.exists(path):
            return True

    # 3. Cek services
    try:
        service = psutil.win_service_get("WinFsp.Launcher")
        if service:
            return True
    except Exception:
        pass

    return False

def get_used_drive_letters() -> set[str]:
    """Mengambil semua huruf drive yang sedang digunakan di Windows."""
    used = set()
    for part in psutil.disk_partitions(all=True):
        mount = part.mountpoint.strip("\\").upper()
        if len(mount) == 2 and mount[1] == ":":
            used.add(mount[0])
    # Fallback cek os.path.exists
    for char in string.ascii_uppercase:
        if os.path.exists(f"{char}:\\"):
            used.add(char)
    return used

def get_available_drive_letters() -> list[str]:
    """Mengembalikan daftar huruf drive yang kosong/tersedia dari D sampai Z."""
    used = get_used_drive_letters()
    # Biasa drive A, B, C dicadangkan atau sudah terpakai
    candidates = [c for c in string.ascii_uppercase if c not in ("A", "B", "C")]
    available = [c for c in candidates if c not in used]
    return available

def get_disk_space_info(path: str) -> dict:
    """Mendapatkan informasi total, used, dan free space dari suatu path direktori."""
    try:
        drive_path = os.path.splitdrive(os.path.abspath(path))[0] + "\\"
        usage = shutil.disk_usage(drive_path)
        return {
            "drive": drive_path,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "free_str": format_bytes(usage.free),
            "total_str": format_bytes(usage.total),
            "free_gb": usage.free / (1024 ** 3),
            "percent_free": (usage.free / usage.total) * 100 if usage.total > 0 else 0
        }
    except Exception:
        return {
            "drive": path,
            "total_bytes": 0,
            "used_bytes": 0,
            "free_bytes": 0,
            "free_str": "N/A",
            "total_str": "N/A",
            "free_gb": 0,
            "percent_free": 0
        }

def get_recommended_cache_dir() -> str:
    """
    Rekomendasikan lokasi folder cache yang aman.
    Jika drive C memiliki ruang sisa kurang dari 10GB dan ada drive lain (misal A:)
    dengan ruang lebih lega, prioritaskan drive lain tersebut.
    """
    c_info = get_disk_space_info(r"C:\Users")
    # Cek drive A: jika ada
    if os.path.exists(r"A:\ "):
        a_info = get_disk_space_info(r"A:\ ")
        if a_info["free_gb"] > 10.0 and c_info["free_gb"] < 10.0:
            target = r"A:\rclone_cache"
            return target

    # Default fallback
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    return os.path.join(local_app_data, "rclone", "cache")
