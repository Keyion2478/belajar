import os
import shutil
import configparser

def get_default_config_path() -> str:
    """Mencari lokasi file rclone.conf resmi."""
    app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
    standard_path = os.path.join(app_data, "rclone", "rclone.conf")
    if os.path.exists(standard_path):
        return standard_path

    # Alternatif path
    user_home = os.path.expanduser("~")
    alt_paths = [
        os.path.join(user_home, ".config", "rclone", "rclone.conf"),
        os.path.join(user_home, "rclone.conf")
    ]
    for p in alt_paths:
        if os.path.exists(p):
            return p
    return standard_path

class RcloneConfigManager:
    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or get_default_config_path()

    def exists(self) -> bool:
        return os.path.exists(self.config_path)

    def load(self) -> configparser.RawConfigParser:
        config = configparser.RawConfigParser()
        if os.path.exists(self.config_path):
            config.read(self.config_path, encoding="utf-8")
        return config

    def save(self, config: configparser.RawConfigParser):
        # Buat backup sebelum menimpa
        if os.path.exists(self.config_path):
            backup_path = self.config_path + ".bak"
            shutil.copy2(self.config_path, backup_path)

        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            config.write(f)

    def get_all_remotes(self) -> dict[str, dict]:
        """
        Mengembalikan kamus semua remote:
        {
            "luzia": {"type": "drive", "scope": "drive", ...},
            "Gdrive_union": {"type": "union", "upstreams": ["luzia", "luzia2"], ...}
        }
        """
        config = self.load()
        remotes = {}
        for section in config.sections():
            items = dict(config.items(section))
            remote_type = items.get("type", "unknown")
            remotes[section] = {
                "name": section,
                "type": remote_type,
                "raw": items
            }
            if remote_type == "union":
                upstreams_raw = items.get("upstreams", "")
                parts = [p.strip().rstrip(":") for p in upstreams_raw.split() if p.strip()]
                remotes[section]["upstreams"] = parts
                raw_policy = items.get("create_policy", "epmfs")
                if raw_policy == "mfs":
                    raw_policy = "epmfs"
                elif raw_policy == "lfs":
                    raw_policy = "eplfs"
                remotes[section]["create_policy"] = raw_policy
                remotes[section]["min_free_space"] = items.get("min_free_space", "1Gi")
        return remotes

    def get_gdrive_remotes(self) -> list[str]:
        """Mengambil nama semua remote yang bertipe Google Drive ('drive')."""
        remotes = self.get_all_remotes()
        return [name for name, data in remotes.items() if data["type"] == "drive"]

    def get_union_remotes(self) -> list[dict]:
        """Mengambil semua remote bertipe 'union' beserta daftar upstream-nya."""
        remotes = self.get_all_remotes()
        return [data for name, data in remotes.items() if data["type"] == "union"]

    def set_union_remote(self, union_name: str, upstream_remotes: list[str], create_policy: str = "epmfs", min_free_space: str = "1Gi") -> bool:
        """
        Membuat atau memperbarui remote union dengan daftar upstream berurutan dan create policy.
        Contoh: set_union_remote("Gdrive_union", ["luzia2", "luzia3", "keyion"], create_policy="epmfs")
        """
        if not upstream_remotes:
            return False

        config = self.load()
        if not config.has_section(union_name):
            config.add_section(union_name)

        upstreams_str = " ".join(f"{r}:" for r in upstream_remotes)
        config.set(union_name, "type", "union")
        config.set(union_name, "upstreams", upstreams_str)
        config.set(union_name, "create_policy", create_policy)
        config.set(union_name, "min_free_space", min_free_space)

        self.save(config)
        return True

    def delete_remote(self, remote_name: str) -> bool:
        """Menghapus remote dari rclone.conf."""
        config = self.load()
        if config.has_section(remote_name):
            config.remove_section(remote_name)
            self.save(config)
            return True
        return False
