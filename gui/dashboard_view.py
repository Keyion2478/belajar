# -*- coding: utf-8 -*-
import os
import subprocess
import threading
import customtkinter as ctk
from core import MountManager, format_bytes, get_disk_space_info, get_directory_size, TransferMonitor
from core.settings_store import load_settings, save_settings
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

class DashboardView(ctk.CTkFrame):
    def __init__(self, master, mount_mgr: MountManager, on_navigate_callback=None, transfer_monitor: TransferMonitor = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.mount_mgr = mount_mgr
        self.on_navigate = on_navigate_callback
        self.settings = load_settings()
        self.transfer_monitor = transfer_monitor or TransferMonitor()
        self.is_monitoring = True
        self.transfer_poll_job = None

        self._build_ui()
        self.refresh_status()
        self._start_transfer_polling()

    def _build_ui(self):
        # 1. Header Box (Astral HUD Header)
        title_box = ctk.CTkFrame(self, fg_color="transparent")
        title_box.pack(fill="x", padx=25, pady=(18, 10))

        title_left = ctk.CTkFrame(title_box, fg_color="transparent")
        title_left.pack(side="left")

        lbl_tag = ctk.CTkLabel(
            title_left,
            text=f"{TAG_HAZARD} SYSTEM CORE // STATUS MONITOR",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_tag.pack(anchor="w")

        title = ctk.CTkLabel(
            title_left,
            text="KONTROL MOUNT DRIVE-CHAN",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_WHITE
        )
        title.pack(anchor="w", pady=(1, 0))

        # Refresh button (Gold Outline Pill)
        btn_refresh = ctk.CTkButton(
            title_box,
            text="🔄 REFRESH STATUS",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=BG_CARD,
            hover_color=BG_HOVER,
            text_color=GOLD_LIGHT,
            border_width=1,
            border_color=GOLD_BORDER,
            corner_radius=8,
            height=34,
            command=self.refresh_status
        )
        btn_refresh.pack(side="right")

        # 2. Main Hero Mount Status Card (HSR Character/HUD Style)
        self.status_card = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_DARK
        )
        self.status_card.pack(fill="x", padx=25, pady=8)

        card_inner = ctk.CTkFrame(self.status_card, fg_color="transparent")
        card_inner.pack(fill="x", padx=22, pady=18)

        # Tags Row (Pill Badges)
        badge_row = ctk.CTkFrame(card_inner, fg_color="transparent")
        badge_row.pack(fill="x", pady=(0, 8))

        self.badge_mode = ctk.CTkLabel(
            badge_row,
            text="[ VFS FULL CACHE ]",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=GOLD_LIGHT,
            fg_color=BG_CARD_GOLD,
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.badge_mode.pack(side="left", padx=(0, 8))

        self.badge_pool = ctk.CTkLabel(
            badge_row,
            text="[ EPMFS STORAGE POOL ]",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_MUTED,
            fg_color=BG_CARD_INNER,
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.badge_pool.pack(side="left")

        # Big Display Status
        self.status_indicator = ctk.CTkLabel(
            card_inner,
            text="● DRIVE STATUS: ONLINE (TERPASANG)",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_SUCCESS
        )
        self.status_indicator.pack(anchor="w", pady=(2, 4))

        self.status_desc = ctk.CTkLabel(
            card_inner,
            text="Virtual drive Google Drive aktif dan siap digunakan di File Explorer.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_CREAM
        )
        self.status_desc.pack(anchor="w", pady=(0, 16))

        # Action Buttons Row
        btn_row = ctk.CTkFrame(card_inner, fg_color="transparent")
        btn_row.pack(fill="x")

        # Primary Toggle Mount (Gold Solid when inactive, Crimson when active)
        self.btn_toggle_mount = ctk.CTkButton(
            btn_row,
            text="⚡ PASANG (MOUNT) DRIVE",
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=GOLD_PRIMARY,
            hover_color=GOLD_HOVER,
            text_color=TEXT_DARK,
            command=self._on_toggle_mount_click
        )
        self.btn_toggle_mount.pack(side="left", padx=(0, 10))

        # Open Explorer Button (Dark Charcoal with Gold Border)
        self.btn_open_explorer = ctk.CTkButton(
            btn_row,
            text="📂 BUKA FILE EXPLORER",
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=BG_CARD_INNER,
            hover_color=BG_HOVER,
            text_color=TEXT_WHITE,
            border_width=1,
            border_color=BORDER_DARK,
            command=self._open_explorer,
            state="disabled"
        )
        self.btn_open_explorer.pack(side="left", padx=(0, 10))

        # Quick Upload Button
        self.btn_quick_upload = ctk.CTkButton(
            btn_row,
            text="📥 TRANSFER & UPLOAD",
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=BG_CARD_INNER,
            hover_color=BG_HOVER,
            text_color=TEXT_WHITE,
            border_width=1,
            border_color=BORDER_DARK,
            command=lambda: self.on_navigate("transfers") if self.on_navigate else None,
            state="disabled"
        )
        self.btn_quick_upload.pack(side="left")

        # 3. Live Sync & Telemetry Mini Banner
        self.transfer_card = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_DARK
        )
        self.transfer_card.pack(fill="x", padx=25, pady=(0, 8))

        transfer_inner = ctk.CTkFrame(self.transfer_card, fg_color="transparent")
        transfer_inner.pack(fill="x", padx=20, pady=12)

        transfer_left = ctk.CTkFrame(transfer_inner, fg_color="transparent")
        transfer_left.pack(side="left", fill="x", expand=True)

        self.lbl_transfer_title = ctk.CTkLabel(
            transfer_left,
            text="📡 STATUS SINKRONISASI: ● IDLE (SEMUA FILE TERSINKRON)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_SUCCESS,
            anchor="w"
        )
        self.lbl_transfer_title.pack(anchor="w")

        self.lbl_transfer_desc = ctk.CTkLabel(
            transfer_left,
            text="Tidak ada antrean upload yang sedang berjalan dari cache lokal ke Google Drive.",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
            anchor="w"
        )
        self.lbl_transfer_desc.pack(anchor="w", pady=(2, 0))

        self.btn_view_transfers = ctk.CTkButton(
            transfer_inner,
            text="MONITOR TRANSFER 📊",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=160,
            height=34,
            corner_radius=8,
            fg_color=BG_CARD_INNER,
            hover_color=BG_HOVER,
            text_color=GOLD_LIGHT,
            border_width=1,
            border_color=BORDER_DARK,
            command=self._go_to_transfers
        )
        self.btn_view_transfers.pack(side="right", padx=(10, 0))

        # 4. System & Configuration Details Grid (Industrial Specs Card)
        details_frame = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_DARK
        )
        details_frame.pack(fill="both", expand=True, padx=25, pady=8)

        details_head = ctk.CTkFrame(details_frame, fg_color="transparent")
        details_head.pack(fill="x", padx=20, pady=(14, 8))

        lbl_details_tag = ctk.CTkLabel(
            details_head,
            text=f"{TAG_HAZARD} TELEMETRI SISTEM",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_details_tag.pack(anchor="w")

        details_title = ctk.CTkLabel(
            details_head,
            text="RINCIAN KONFIGURASI AKTIF",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=TEXT_WHITE
        )
        details_title.pack(anchor="w")

        self.info_grid = ctk.CTkFrame(details_frame, fg_color="transparent")
        self.info_grid.pack(fill="x", padx=20, pady=(0, 14))
        self.info_grid.grid_columnconfigure(1, weight=1)

        self.lbl_target_remote = self._create_info_row(self.info_grid, 0, "REMOTE TARGET:", "-")
        self.lbl_target_letter = self._create_info_row(self.info_grid, 1, "HURUF DRIVE:", "-")
        self.lbl_vol_name = self._create_info_row(self.info_grid, 2, "LABEL WINDOWS:", "-")
        self.lbl_cache_dir = self._create_info_row(self.info_grid, 3, "CACHE LOKAL:", "-")
        self.lbl_disk_free = self._create_info_row(self.info_grid, 4, "SISA DISK CACHE:", "-")

        # 5. Startup Toggle Card (Bottom Bar)
        startup_frame = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_DARK
        )
        startup_frame.pack(fill="x", padx=25, pady=(4, 18))

        self.switch_startup = ctk.CTkSwitch(
            startup_frame,
            text="⚡ Jalankan Mount Otomatis saat Windows Menyala (Auto-Start)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_CREAM,
            progress_color=GOLD_PRIMARY,
            button_color=GOLD_LIGHT,
            button_hover_color=GOLD_PRIMARY,
            command=self._on_startup_toggle
        )
        self.switch_startup.pack(side="left", padx=20, pady=12)

    def _create_info_row(self, parent, row: int, label_text: str, value_text: str) -> ctk.CTkLabel:
        lbl_key = ctk.CTkLabel(
            parent,
            text=label_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_key.grid(row=row, column=0, sticky="w", pady=4, padx=(0, 20))

        lbl_val = ctk.CTkLabel(
            parent,
            text=value_text,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_WHITE
        )
        lbl_val.grid(row=row, column=1, sticky="w", pady=4)
        return lbl_val

    def refresh_status(self):
        self.settings = load_settings()
        remote = self.settings.get("union_remote", "Gdrive_union")
        letter = self.settings.get("drive_letter", "G").upper()
        volume = self.settings.get("volume_name", "Google Drive")
        cache_dir = self.settings.get("cache_dir", "")

        self.lbl_target_remote.configure(text=f"{remote}:")
        self.lbl_target_letter.configure(text=f"{letter}:\\")
        self.lbl_vol_name.configure(text=volume)
        current_cache_bytes = get_directory_size(cache_dir)
        cache_used_str = format_bytes(current_cache_bytes)
        self.lbl_cache_dir.configure(text=f"{cache_dir} (Terpakai: {cache_used_str})")

        disk_info = get_disk_space_info(cache_dir)
        free_str = disk_info["free_str"]
        if disk_info["free_gb"] < 5.0:
            self.lbl_disk_free.configure(text=f"{free_str} ⚠️ [KRITIS - Alihkan Drive]", text_color=COLOR_DANGER)
        else:
            self.lbl_disk_free.configure(text=f"{free_str} [AMAN]", text_color=COLOR_SUCCESS)

        # Cek status proses dan drive
        is_running = self.mount_mgr.is_process_running()
        is_drive_live = self.mount_mgr.is_drive_active(letter)

        if is_running or is_drive_live:
            self.status_card.configure(border_color=BORDER_GOLD)
            self.status_indicator.configure(
                text=f"● STATUS: TERPASANG PADA DRIVE {letter}: ({volume})",
                text_color=COLOR_SUCCESS
            )
            self.status_desc.configure(
                text="Virtual drive Google Drive aktif dan siap digunakan di File Explorer.",
                text_color=TEXT_CREAM
            )
            self.btn_toggle_mount.configure(
                text="🛑 LEPAS (UNMOUNT) DRIVE",
                fg_color=COLOR_DANGER,
                hover_color=COLOR_DANGER_HOVER,
                text_color=TEXT_WHITE
            )
            self.btn_open_explorer.configure(
                state="normal",
                border_color=GOLD_BORDER,
                text_color=GOLD_LIGHT
            )
            self.btn_quick_upload.configure(
                state="normal",
                border_color=GOLD_BORDER,
                text_color=GOLD_LIGHT
            )
        else:
            self.status_card.configure(border_color=BORDER_DARK)
            self.status_indicator.configure(
                text="○ STATUS: TIDAK AKTIF (UNMOUNTED)",
                text_color=TEXT_MUTED
            )
            self.status_desc.configure(
                text="Virtual drive belum dipasang ke File Explorer.",
                text_color=TEXT_MUTED
            )
            self.btn_toggle_mount.configure(
                text="⚡ PASANG (MOUNT) DRIVE",
                fg_color=GOLD_PRIMARY,
                hover_color=GOLD_HOVER,
                text_color=TEXT_DARK
            )
            self.btn_open_explorer.configure(
                state="disabled",
                border_color=BORDER_DARK,
                text_color=TEXT_MUTED
            )
            self.btn_quick_upload.configure(
                state="disabled",
                border_color=BORDER_DARK,
                text_color=TEXT_MUTED
            )

        # Status switch startup
        if self.mount_mgr.is_startup_enabled():
            self.switch_startup.select()
        else:
            self.switch_startup.deselect()

    def _on_toggle_mount_click(self):
        is_running = self.mount_mgr.is_process_running()
        if is_running:
            self.btn_toggle_mount.configure(text="Sedang Menghentikan...", state="disabled")
            threading.Thread(target=self._stop_mount_worker, daemon=True).start()
        else:
            self.btn_toggle_mount.configure(text="Sedang Memasang...", state="disabled")
            threading.Thread(target=self._start_mount_worker, daemon=True).start()

    def _start_mount_worker(self):
        self.settings = load_settings()
        remote = self.settings.get("union_remote", "Gdrive_union")
        letter = self.settings.get("drive_letter", "G")
        cache_dir = self.settings.get("cache_dir", "")
        cache_size = self.settings.get("cache_max_size", "10G")
        vol_name = self.settings.get("volume_name", "Drive-Chan")

        ok, msg = self.mount_mgr.start_mount(
            remote_name=remote,
            drive_letter=letter,
            cache_dir=cache_dir,
            cache_max_size=cache_size,
            volume_name=vol_name
        )
        self.after(2000, self.refresh_status)
        self.after(2000, lambda: self.btn_toggle_mount.configure(state="normal"))

    def _stop_mount_worker(self):
        self.mount_mgr.stop_mount()
        self.after(1500, self.refresh_status)
        self.after(1500, lambda: self.btn_toggle_mount.configure(state="normal"))

    def _open_explorer(self):
        letter = self.settings.get("drive_letter", "G").upper()
        drive_path = f"{letter}:\\"
        if os.path.exists(drive_path):
            subprocess.Popen(["explorer.exe", drive_path])

    def _on_startup_toggle(self):
        is_on = bool(self.switch_startup.get())
        self.settings = load_settings()
        self.settings["auto_start"] = is_on
        save_settings(self.settings)

        self.mount_mgr.set_startup_enabled(
            enabled=is_on,
            remote_name=self.settings.get("union_remote", "Gdrive_union"),
            drive_letter=self.settings.get("drive_letter", "G"),
            cache_dir=self.settings.get("cache_dir", ""),
            cache_max_size=self.settings.get("cache_max_size", "10G"),
            volume_name=self.settings.get("volume_name", "Drive-Chan")
        )

    def _go_to_transfers(self):
        if self.on_navigate:
            self.on_navigate("transfers")

    def _start_transfer_polling(self):
        self._poll_transfer_card()

    def _poll_transfer_card(self):
        if not self.is_monitoring:
            return
        try:
            stats = self.transfer_monitor.get_stats()
            if stats.get("is_uploading"):
                items = stats.get("transferring", [])
                queued = stats.get("queued", [])
                count = len(items)
                q_count = len(queued)
                speed = stats.get("speed_str", "0 B/s")
                self.transfer_card.configure(fg_color=BG_CARD_GOLD, border_color=BORDER_GOLD)
                self.lbl_transfer_title.configure(
                    text=f"🚀 UPLOAD AKTIF: {count} BERJALAN • {q_count} ANTREAN | ⚡ {speed}",
                    text_color=GOLD_LIGHT
                )
                if items:
                    first = items[0]
                    detail = f"Sedang transfer: {first['name']} ({first['percentage']}%) • {first['bytes_str']}/{first['size_str']}"
                    if count > 1 or q_count > 0:
                        detail += f" (+{count - 1 + q_count} file antrean)"
                    self.lbl_transfer_desc.configure(text=detail, text_color=TEXT_CREAM)
                self.btn_view_transfers.configure(
                    fg_color=GOLD_PRIMARY,
                    hover_color=GOLD_HOVER,
                    text_color=TEXT_DARK,
                    border_color=BORDER_GOLD
                )
            else:
                self.transfer_card.configure(fg_color=BG_CARD, border_color=BORDER_DARK)
                letter = self.settings.get("drive_letter", "G")
                is_live = self.mount_mgr.is_drive_active(letter) or self.mount_mgr.is_process_running()
                if is_live:
                    self.lbl_transfer_title.configure(
                        text="📡 STATUS SINKRONISASI: ● IDLE (SEMUA FILE TERSINKRON)",
                        text_color=COLOR_SUCCESS
                    )
                    self.lbl_transfer_desc.configure(
                        text="Semua data di cache lokal telah tersimpan rapi di Google Drive.",
                        text_color=TEXT_MUTED
                    )
                else:
                    self.lbl_transfer_title.configure(
                        text="📡 STATUS SINKRONISASI: ○ DRIVE TIDAK AKTIF",
                        text_color=TEXT_MUTED
                    )
                    self.lbl_transfer_desc.configure(
                        text="Pasang virtual drive untuk memulai sinkronisasi otomatis.",
                        text_color=TEXT_MUTED
                    )
                self.btn_view_transfers.configure(
                    fg_color=BG_CARD_INNER,
                    hover_color=BG_HOVER,
                    text_color=GOLD_LIGHT,
                    border_color=BORDER_DARK
                )
        except Exception:
            pass

        self.transfer_poll_job = self.after(2000, self._poll_transfer_card)

    def destroy(self):
        self.is_monitoring = False
        if self.transfer_poll_job:
            self.after_cancel(self.transfer_poll_job)
        super().destroy()
