import os
import sys
import time

print("=" * 60)
print("TESTING FITUR Rclone Drive Manager SATU PER SATU")
print("=" * 60)

# 1. System Detector
print("\n[1/7] Testing System Detector...")
from core import (
    find_rclone_binary,
    is_winfsp_installed,
    get_available_drive_letters,
    get_disk_space_info,
    get_recommended_cache_dir,
    format_bytes
)

rclone = find_rclone_binary()
assert rclone is not None and os.path.exists(rclone), f"Rclone binary tidak ditemukan: {rclone}"
print(f"  -> Rclone binary: {rclone} [OK]")

winfsp = is_winfsp_installed()
assert winfsp is True, "WinFsp tidak terdeteksi!"
print(f"  -> WinFsp status: {winfsp} [OK]")

letters = get_available_drive_letters()
assert len(letters) > 0, "Tidak ada drive letter kosong!"
print(f"  -> Available drive letters ({len(letters)}): {', '.join(letters[:6])}... [OK]")

c_space = get_disk_space_info(r"C:\Users")
a_space = get_disk_space_info(r"A:\ ")
print(f"  -> Free space C: {c_space['free_str']} | Free space A: {a_space['free_str']} [OK]")

rec_cache = get_recommended_cache_dir()
assert "A:" in rec_cache or "a:" in rec_cache, f"Cache harusnya diprioritaskan di A:, tapi di: {rec_cache}"
print(f"  -> Rekomendasi Cache: {rec_cache} [OK]")

# 2. Config Manager
print("\n[2/7] Testing Config Manager...")
from core import RcloneConfigManager
cfg = RcloneConfigManager()
assert cfg.exists(), "rclone.conf tidak ditemukan!"

remotes = cfg.get_all_remotes()
gdrives = cfg.get_gdrive_remotes()
unions = cfg.get_union_remotes()
print(f"  -> Total remotes: {len(remotes)} | GDrive: {gdrives} | Unions: {[u['name'] for u in unions]} [OK]")
assert "luzia" in gdrives, "luzia harusnya ada di gdrives"
assert "Gdrive_union" in remotes, "Gdrive_union harusnya ada di remotes"

# 3. Rclone Executor - Quota & Health
print("\n[3/7] Testing Rclone Quota & Union Health Check...")
from core import RcloneExecutor
executor = RcloneExecutor()

quota_luzia = executor.check_remote_quota("luzia")
print(f"  -> Quota luzia: OK={quota_luzia['ok']}, Total={format_bytes(quota_luzia['total'])}, Free={format_bytes(quota_luzia['free'])} [OK]")
assert quota_luzia["ok"] is True, f"luzia quota failed: {quota_luzia}"

union_ok, union_msg = executor.check_union_health("Gdrive_union")
print(f"  -> Union Health Gdrive_union: {union_ok} ({union_msg}) [OK]")
assert union_ok is True, f"Union health failed: {union_msg}"

# 4. Settings Store
print("\n[4/7] Testing Settings Store...")
from core.settings_store import load_settings, save_settings
s = load_settings()
s["drive_letter"] = "G"
save_settings(s)
s2 = load_settings()
assert s2["drive_letter"] == "G", "Settings gagal disimpan/dibaca!"
print(f"  -> Settings drive letter: {s2['drive_letter']} [OK]")

# 5. Mount Manager - Startup Script
print("\n[5/7] Testing Mount Manager (Startup Generation)...")
from core import MountManager
from core.mount_manager import get_startup_folder
mm = MountManager()
test_startup = mm.set_startup_enabled(
    enabled=True,
    remote_name="Gdrive_union",
    drive_letter="G",
    cache_dir=rec_cache,
    cache_max_size="10G",
    volume_name="Drive-Chan >//<"
)
assert test_startup is True, "Gagal membuat script startup!"
assert mm.is_startup_enabled() is True, "Startup file tidak terdeteksi!"
vbs_path = os.path.join(get_startup_folder(), "RcloneAutoMount.vbs")
with open(vbs_path, "r", encoding="utf-8") as vf:
    vbs_text = vf.read()
assert "LC:\\" not in vbs_text, "Ditemukan typo LC:\\ di script startup!"
print("  -> VBScript Startup berhasil digenerate tanpa typo [OK]")

# Bersihkan test startup
mm.set_startup_enabled(False, "Gdrive_union", "G", rec_cache, "10G", "Drive-Chan")
assert mm.is_startup_enabled() is False, "Startup file gagal dihapus saat disabled!"
print("  -> VBScript Startup berhasil dibersihkan [OK]")

# 6. Test Batch Launch Flow (Add Account & Reconnect)
print("\n[6/7] Testing OAuth Batch Launcher...")
proc = executor.launch_add_account_flow("test_verifier_remote")
print(f"  -> Spawned batch runner PID: {proc.pid}")
time.sleep(2)
poll = proc.poll()
print(f"  -> Runner status after 2s: {poll} (None berarti jendela aktif & browser auth terbuka)")
assert poll is None, f"Batch runner langsung mati dengan kode {poll}! Berarti masih ada error cmd!"
# Kill test proc
proc.terminate()
time.sleep(1)
if proc.poll() is None:
    proc.kill()
# Bersihkan proses rclone yang mungkin spawned
import subprocess
subprocess.run(["rclone", "config", "delete", "test_verifier_remote", "--config", cfg.config_path], capture_output=True)
print("  -> Batch runner terbukti aktif dan berjalan normal! [OK]")

# 7. GUI Initialization Test
print("\n[7/7] Testing GUI Window Initialization...")
from gui import MainApp
app = MainApp()
app.update() # Render satu frame GUI untuk memvalidasi seluruh widget
app.destroy()
print("  -> Seluruh widget dan view GUI berhasil dirender tanpa error! [OK]")

print("\n" + "=" * 60)
print("SEMUA PENGUJIAN 100% SUKSES DAN BEBAS ERROR!")
print("=" * 60)
