# -*- coding: utf-8 -*-
import os
import subprocess
from tkinter import filedialog
import customtkinter as ctk
from core import (
    get_available_drive_letters,
    get_disk_space_info,
    get_recommended_cache_dir,
    get_directory_size,
    format_bytes
)
from core.settings_store import load_settings, save_settings, clean_volume_name
from .theme import (
    BG_BASE,
    BG_CARD,
    BG_CARD_INNER,
    BG_CARD_GOLD,
    BG_HOVER,
    GOLD_PRIMARY,
    GOLD_HOVER,
    GOLD_LIGHT,
    GOLD_BORDER,
    BORDER_DARK,
    BORDER_GOLD,
    TEXT_WHITE,
    TEXT_CREAM,
    TEXT_MUTED,
    TEXT_DARK,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_DANGER_HOVER,
    TAG_HAZARD
)

class SettingsView(ctk.CTkFrame):
    def __init__(self, master, on_save_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_save_cb = on_save_callback
        self.settings = load_settings()

        self._build_ui()
        self.load_current_values()

    def _build_ui(self):
        # Header Box
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(18, 10))

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left")

        lbl_tag = ctk.CTkLabel(
            header_left,
            text=f"{TAG_HAZARD} SYSTEM CONFIG // VFS STORAGE ENGINE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_tag.pack(anchor="w")

        title = ctk.CTkLabel(
            header_left,
            text="PENGATURAN MOUNT & PROTEKSI CACHE",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_WHITE
        )
        title.pack(anchor="w", pady=(1, 0))

        # Scrollable form container
        form_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=12,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_DARK
        )
        form_frame.pack(fill="both", expand=True, padx=25, pady=(5, 18))

        # 1. Drive Letter
        lbl_drive = ctk.CTkLabel(
            form_frame,
            text="1. HURUF DRIVE VIRTUAL (DRIVE LETTER):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_drive.pack(anchor="w", padx=20, pady=(15, 4))

        available_letters = get_available_drive_letters()
        if "G" not in available_letters:
            available_letters.append("G")
        available_letters.sort()

        self.combo_letter = ctk.CTkComboBox(
            form_frame,
            values=[f"{c}:" for c in available_letters],
            width=160,
            fg_color=BG_CARD_INNER,
            border_color=BORDER_DARK,
            button_color=GOLD_PRIMARY,
            button_hover_color=GOLD_HOVER
        )
        self.combo_letter.pack(anchor="w", padx=20, pady=(0, 15))

        # 2. Volume Name
        lbl_vol = ctk.CTkLabel(
            form_frame,
            text="2. NAMA LABEL VOLUME (WINDOWS EXPLORER):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_vol.pack(anchor="w", padx=20, pady=(0, 4))

        self.entry_vol = ctk.CTkEntry(
            form_frame,
            width=320,
            placeholder_text="Contoh: Drive-Chan",
            fg_color=BG_CARD_INNER,
            border_color=BORDER_DARK
        )
        self.entry_vol.pack(anchor="w", padx=20, pady=(0, 15))

        # 3. Cache Directory
        lbl_cache = ctk.CTkLabel(
            form_frame,
            text="3. FOLDER CACHE PENYIMPANAN SEMENTARA (VFS BUFFER):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_cache.pack(anchor="w", padx=20, pady=(0, 4))

        cache_row = ctk.CTkFrame(form_frame, fg_color="transparent")
        cache_row.pack(fill="x", padx=20, pady=(0, 6))

        self.entry_cache = ctk.CTkEntry(
            cache_row,
            width=420,
            fg_color=BG_CARD_INNER,
            border_color=BORDER_DARK
        )
        self.entry_cache.pack(side="left", padx=(0, 10))

        btn_browse = ctk.CTkButton(
            cache_row,
            text="📁 PILIH FOLDER",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=120,
            height=30,
            corner_radius=6,
            fg_color=BG_CARD_INNER,
            hover_color=BG_HOVER,
            text_color=GOLD_LIGHT,
            border_width=1,
            border_color=GOLD_BORDER,
            command=self._on_browse_cache
        )
        btn_browse.pack(side="left")

        # Disk health label under cache entry
        self.lbl_cache_disk_status = ctk.CTkLabel(
            form_frame,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_cache_disk_status.pack(anchor="w", padx=20, pady=(0, 10))

        # Current Cache Usage Info Box
        cache_usage_card = ctk.CTkFrame(
            form_frame,
            corner_radius=10,
            fg_color=BG_CARD_INNER,
            border_width=1,
            border_color=BORDER_DARK
        )
        cache_usage_card.pack(fill="x", padx=20, pady=(0, 15))

        self.lbl_current_cache_usage = ctk.CTkLabel(
            cache_usage_card,
            text="📦 Penggunaan Cache Saat Ini: Menghitung...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=GOLD_LIGHT
        )
        self.lbl_current_cache_usage.pack(side="left", padx=16, pady=10)

        btn_open_cache_folder = ctk.CTkButton(
            cache_usage_card,
            text="📂 BUKA FOLDER",
            width=120,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=BG_CARD,
            hover_color=BG_HOVER,
            text_color=TEXT_WHITE,
            command=self._on_open_cache_folder
        )
        btn_open_cache_folder.pack(side="right", padx=(5, 12), pady=8)

        btn_refresh_cache_size = ctk.CTkButton(
            cache_usage_card,
            text="🔄 CEK UKURAN",
            width=110,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=BG_CARD,
            hover_color=BG_HOVER,
            text_color=GOLD_LIGHT,
            border_width=1,
            border_color=GOLD_BORDER,
            command=self._refresh_cache_usage
        )
        btn_refresh_cache_size.pack(side="right", padx=(5, 5), pady=8)

        # 4. Cache Max Size
        lbl_size = ctk.CTkLabel(
            form_frame,
            text="4. BATAS MAKSIMAL UKURAN CACHE (VFS MAX SIZE):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_size.pack(anchor="w", padx=20, pady=(0, 4))

        self.combo_size = ctk.CTkComboBox(
            form_frame,
            values=["2G", "5G", "10G", "15G", "20G", "50G"],
            width=160,
            fg_color=BG_CARD_INNER,
            border_color=BORDER_DARK,
            button_color=GOLD_PRIMARY,
            button_hover_color=GOLD_HOVER
        )
        self.combo_size.pack(anchor="w", padx=20, pady=(0, 15))

        # 5. Cache Max Age
        lbl_age = ctk.CTkLabel(
            form_frame,
            text="5. DURASI PENYIMPANAN CACHE (VFS MAX AGE):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_age.pack(anchor="w", padx=20, pady=(0, 4))

        self.entry_age = ctk.CTkEntry(
            form_frame,
            width=160,
            fg_color=BG_CARD_INNER,
            border_color=BORDER_DARK
        )
        self.entry_age.pack(anchor="w", padx=20, pady=(0, 20))

        # Save Button
        self.btn_save = ctk.CTkButton(
            form_frame,
            text="💾 SIMPAN PENGATURAN",
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=GOLD_PRIMARY,
            hover_color=GOLD_HOVER,
            text_color=TEXT_DARK,
            command=self._on_save_settings
        )
        self.btn_save.pack(anchor="w", padx=20, pady=(0, 15))

        self.lbl_save_status = ctk.CTkLabel(form_frame, text="", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_save_status.pack(anchor="w", padx=20, pady=(0, 10))

    def load_current_values(self):
        self.settings = load_settings()

        letter = self.settings.get("drive_letter", "G").upper()
        self.combo_letter.set(f"{letter}:")

        self.entry_vol.delete(0, "end")
        self.entry_vol.insert(0, self.settings.get("volume_name", "Drive-Chan"))

        cache_dir = self.settings.get("cache_dir", get_recommended_cache_dir())
        self.entry_cache.delete(0, "end")
        self.entry_cache.insert(0, cache_dir)

        self.combo_size.set(self.settings.get("cache_max_size", "10G"))

        self.entry_age.delete(0, "end")
        self.entry_age.insert(0, self.settings.get("cache_max_age", "24h"))

        self._update_disk_meter(cache_dir)
        self._refresh_cache_usage()

    def _refresh_cache_usage(self):
        cache_path = self.entry_cache.get().strip()
        size_bytes = get_directory_size(cache_path)
        size_str = format_bytes(size_bytes)
        limit = self.combo_size.get().strip() or "5G"
        self.lbl_current_cache_usage.configure(
            text=f"📦 Penggunaan Cache Saat Ini: {size_str} (Batas VFS: {limit})"
        )

    def _on_open_cache_folder(self):
        cache_path = self.entry_cache.get().strip()
        if not os.path.exists(cache_path):
            os.makedirs(cache_path, exist_ok=True)
        subprocess.Popen(["explorer.exe", cache_path])

    def _update_disk_meter(self, path: str):
        info = get_disk_space_info(path)
        drive_name = info["drive"]
        free_s = info["free_str"]
        total_s = info["total_str"]
        free_gb = info["free_gb"]

        if free_gb < 5.0:
            msg = f"⚠️ PERINGATAN: Drive {drive_name} hanya tersisa {free_s} dari {total_s}! Sangat tidak disarankan memakai drive ini untuk cache."
            color = COLOR_DANGER
        elif free_gb < 15.0:
            msg = f"ℹ️ Sisa ruang pada {drive_name}: {free_s} dari {total_s}. Cukup aman."
            color = COLOR_WARNING
        else:
            msg = f"✅ Drive {drive_name} memiliki sisa {free_s} dari {total_s}. Sangat aman untuk cache."
            color = COLOR_SUCCESS

        self.lbl_cache_disk_status.configure(text=msg, text_color=color)

    def _on_browse_cache(self):
        folder = filedialog.askdirectory(title="Pilih Folder Cache Rclone")
        if folder:
            self.entry_cache.delete(0, "end")
            self.entry_cache.insert(0, folder)
            self._update_disk_meter(folder)
            self._refresh_cache_usage()

    def _on_save_settings(self):
        letter_clean = self.combo_letter.get().replace(":", "").strip().upper()
        vol_clean = clean_volume_name(self.entry_vol.get().strip() or "Drive-Chan")
        cache_clean = self.entry_cache.get().strip() or get_recommended_cache_dir()
        size_clean = self.combo_size.get().strip() or "10G"
        age_clean = self.entry_age.get().strip() or "24h"

        self.settings["drive_letter"] = letter_clean
        self.settings["volume_name"] = vol_clean
        self.settings["cache_dir"] = cache_clean
        self.settings["cache_max_size"] = size_clean
        self.settings["cache_max_age"] = age_clean

        save_settings(self.settings)
        self._update_disk_meter(cache_clean)
        self._refresh_cache_usage()

        self.lbl_save_status.configure(
            text="✅ Pengaturan berhasil disimpan!",
            text_color=COLOR_SUCCESS
        )
        self.after(3000, lambda: self.lbl_save_status.configure(text=""))

        if self.on_save_cb:
            self.on_save_cb()
