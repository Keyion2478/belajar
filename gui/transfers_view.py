# -*- coding: utf-8 -*-
import os
import threading
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import customtkinter as ctk
from core import TransferMonitor, FileUploader, purge_file_and_cache, format_bytes
from core.settings_store import load_settings
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

class TransfersView(ctk.CTkFrame):
    def __init__(self, master, transfer_monitor: TransferMonitor = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.monitor = transfer_monitor or TransferMonitor()
        self.uploader = FileUploader()
        self.is_monitoring = True
        self.poll_job = None
        self.last_view_state = ""

        # Pengaturan folder tujuan default (Drive-Chan Root)
        settings = load_settings()
        letter = settings.get("drive_letter", "G").strip().rstrip(":")
        self.default_target_dir = f"{letter}:\\"
        self.current_target_dir = self.default_target_dir

        self._build_ui()
        self._start_polling()

    def _build_ui(self):
        # 1. Header (Astral HUD Header)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(18, 10))

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left")

        lbl_tag = ctk.CTkLabel(
            header_left,
            text=f"{TAG_HAZARD} TRANSMISSION // DATA FLOW MONITOR",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_tag.pack(anchor="w")

        title = ctk.CTkLabel(
            header_left,
            text="MONITOR TRANSFER & UPLOAD CEPAT",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_WHITE
        )
        title.pack(anchor="w", pady=(1, 0))

        self.lbl_live_badge = ctk.CTkLabel(
            header,
            text="● LIVE TELEMETRY",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GOLD_LIGHT,
            fg_color=BG_CARD_GOLD,
            corner_radius=6,
            padx=10,
            pady=4
        )
        self.lbl_live_badge.pack(side="right")

        # 2. Metric summary cards (4 columns)
        metrics_frame = ctk.CTkFrame(self, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=25, pady=(0, 10))
        metrics_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_status = self._create_metric_card(metrics_frame, 0, "STATUS TRANSFER", "○ MOUNT MATI", TEXT_MUTED)
        self.card_speed = self._create_metric_card(metrics_frame, 1, "KECEPATAN UPLOAD", "0 B/s", GOLD_PRIMARY)
        self.card_total = self._create_metric_card(metrics_frame, 2, "DATA TERKIRIM", "0 B", GOLD_LIGHT)
        self.card_completed = self._create_metric_card(metrics_frame, 3, "FILE SELESAI", "0 File", COLOR_SUCCESS)

        # 3. Drop Zone & Quick Upload Card
        self.drop_card = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_DARK
        )
        self.drop_card.pack(fill="x", padx=25, pady=(0, 10))

        drop_inner = ctk.CTkFrame(self.drop_card, fg_color="transparent")
        drop_inner.pack(fill="x", padx=20, pady=14)

        # Drop Zone Header Info
        top_drop_row = ctk.CTkFrame(drop_inner, fg_color="transparent")
        top_drop_row.pack(fill="x", pady=(0, 10))

        lbl_drop_icon = ctk.CTkLabel(top_drop_row, text="⚡", font=ctk.CTkFont(size=22), text_color=GOLD_PRIMARY)
        lbl_drop_icon.pack(side="left", padx=(0, 10))

        title_col = ctk.CTkFrame(top_drop_row, fg_color="transparent")
        title_col.pack(side="left", fill="x", expand=True)

        lbl_drop_title = ctk.CTkLabel(
            title_col,
            text="UPLOAD BUFFER CEPAT KE DRIVE-CHAN",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_WHITE,
            anchor="w"
        )
        lbl_drop_title.pack(anchor="w")

        lbl_drop_sub = ctk.CTkLabel(
            title_col,
            text="File disalin instan ke cache buffer lokal, kemudian Rclone VFS mengunggahnya secara berurutan ke Google Drive.",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
            anchor="w"
        )
        lbl_drop_sub.pack(anchor="w")

        # Destination Folder Selector Bar
        dest_bar = ctk.CTkFrame(drop_inner, corner_radius=8, fg_color=BG_CARD_INNER, border_width=1, border_color=BORDER_DARK)
        dest_bar.pack(fill="x", pady=(0, 10))

        lbl_dest_tag = ctk.CTkLabel(
            dest_bar,
            text="📍 TARGET DIRECTORY:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_dest_tag.pack(side="left", padx=(12, 6), pady=6)

        self.lbl_target_path = ctk.CTkLabel(
            dest_bar,
            text=self.current_target_dir,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_WHITE
        )
        self.lbl_target_path.pack(side="left", pady=6)

        btn_change_dest = ctk.CTkButton(
            dest_bar,
            text="PILIH SUBFOLDER...",
            width=120,
            height=26,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=BG_CARD,
            hover_color=BG_HOVER,
            text_color=GOLD_LIGHT,
            border_width=1,
            border_color=GOLD_BORDER,
            command=self._on_change_target_folder
        )
        btn_change_dest.pack(side="right", padx=(6, 8), pady=4)

        btn_reset_dest = ctk.CTkButton(
            dest_bar,
            text="RESET ROOT",
            width=90,
            height=26,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=BG_HOVER,
            text_color=TEXT_MUTED,
            command=self._on_reset_target_folder
        )
        btn_reset_dest.pack(side="right", padx=(0, 4), pady=4)

        # Action Buttons Row
        action_row = ctk.CTkFrame(drop_inner, fg_color="transparent")
        action_row.pack(fill="x")

        self.btn_select_files = ctk.CTkButton(
            action_row,
            text="📄 PILIH FILE LOKAL...",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
            corner_radius=8,
            fg_color=GOLD_PRIMARY,
            hover_color=GOLD_HOVER,
            text_color=TEXT_DARK,
            command=self._on_select_files
        )
        self.btn_select_files.pack(side="left", padx=(0, 10))

        self.btn_select_folder = ctk.CTkButton(
            action_row,
            text="📁 PILIH FOLDER LOKAL...",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
            corner_radius=8,
            fg_color=BG_CARD_INNER,
            hover_color=BG_HOVER,
            text_color=TEXT_WHITE,
            border_width=1,
            border_color=BORDER_DARK,
            command=self._on_select_folder
        )
        self.btn_select_folder.pack(side="left")

        # In-Progress Local Copy Frame (Stage 1)
        self.copy_progress_frame = ctk.CTkFrame(drop_inner, fg_color="transparent")
        # Hidden by default

        self.lbl_copy_status = ctk.CTkLabel(
            self.copy_progress_frame,
            text="📥 Tahap 1: Menyalin ke Buffer Drive-Chan...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=GOLD_LIGHT,
            anchor="w"
        )
        self.lbl_copy_status.pack(anchor="w", pady=(8, 2))

        copy_bar_row = ctk.CTkFrame(self.copy_progress_frame, fg_color="transparent")
        copy_bar_row.pack(fill="x", pady=(0, 4))

        self.pbar_local_copy = ctk.CTkProgressBar(
            copy_bar_row,
            height=8,
            corner_radius=4,
            progress_color=GOLD_PRIMARY,
            fg_color=BG_CARD_INNER
        )
        self.pbar_local_copy.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.pbar_local_copy.set(0.0)

        self.btn_cancel_copy = ctk.CTkButton(
            copy_bar_row,
            text="❌ BATALKAN SALIN",
            width=120,
            height=26,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            text_color=TEXT_WHITE,
            command=self._on_cancel_copy
        )
        self.btn_cancel_copy.pack(side="right")

        # 4. Section: Active Cloud Transfers (Stage 2)
        sec_header = ctk.CTkFrame(self, fg_color="transparent")
        sec_header.pack(fill="x", padx=25, pady=(2, 6))

        lbl_sec_tag = ctk.CTkLabel(
            sec_header,
            text=f"{TAG_HAZARD} CLOUD DISPATCH // ANTREAN GOOGLE DRIVE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_sec_tag.pack(side="left")

        self.scroll_transfers = ctk.CTkScrollableFrame(
            self,
            corner_radius=12,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_DARK
        )
        self.scroll_transfers.pack(fill="both", expand=True, padx=25, pady=(0, 14))

    def _on_select_files(self):
        """Memilih file via Windows File Dialog."""
        files = filedialog.askopenfilenames(
            title="Pilih File untuk Diunggah ke Drive-Chan",
            filetypes=[("Semua File", "*.*")]
        )
        if files:
            self._start_upload_queue(list(files))

    def _on_select_folder(self):
        """Memilih seluruh folder via Windows Directory Dialog."""
        folder = filedialog.askdirectory(title="Pilih Folder untuk Diunggah ke Drive-Chan")
        if folder:
            self._start_upload_queue([folder])

    def _on_change_target_folder(self):
        """Mengubah folder tujuan di dalam Drive-Chan."""
        if not os.path.exists(self.default_target_dir):
            messagebox.showwarning(
                "Drive Belum Siap",
                f"Drive {self.default_target_dir} belum terpasang. Silakan mount terlebih dahulu di Dashboard."
            )
            return

        new_dir = filedialog.askdirectory(
            initialdir=self.default_target_dir,
            title="Pilih Folder Tujuan di Drive-Chan"
        )
        if new_dir:
            self.current_target_dir = os.path.normpath(new_dir)
            self.lbl_target_path.configure(text=self.current_target_dir)

    def _on_reset_target_folder(self):
        """Mengembalikan folder tujuan ke root drive."""
        self.current_target_dir = self.default_target_dir
        self.lbl_target_path.configure(text=self.current_target_dir)

    def _start_upload_queue(self, paths: list[str]):
        """Validasi dan mulai proses copy asinkron."""
        if not os.path.exists(self.current_target_dir):
            messagebox.showwarning(
                "Drive Tidak Aktif",
                f"Drive virtual '{self.current_target_dir}' tidak terdeteksi!\n\n"
                "Silakan buka tab Dashboard lalu klik 'Pasang (Mount) Drive' terlebih dahulu."
            )
            return

        if self.uploader.is_busy:
            messagebox.showinfo(
                "Sedang Memproses",
                "Masih ada proses penyalinan lain yang sedang berjalan. Harap tunggu hingga selesai."
            )
            return

        # Tampilkan progress bar copy lokal
        self.copy_progress_frame.pack(fill="x", pady=(10, 0))
        self.btn_select_files.configure(state="disabled")
        self.btn_select_folder.configure(state="disabled")
        self.btn_cancel_copy.configure(state="normal", text="❌ BATALKAN SALIN")
        self.lbl_copy_status.configure(
            text=f"Menyiapkan penyalinan {len(paths)} item ke Drive-Chan...",
            text_color=GOLD_LIGHT
        )
        self.pbar_local_copy.set(0.0)

        self.uploader.upload_async(
            sources=paths,
            target_dir=self.current_target_dir,
            on_progress=self._on_copy_progress_callback,
            on_complete=self._on_copy_complete_callback
        )

    def _on_copy_progress_callback(self, current_file: str, copied_bytes: int, total_bytes: int, speed: float):
        pct = max(0.0, min(1.0, copied_bytes / total_bytes if total_bytes > 0 else 0))
        pct_text = int(pct * 100)
        copied_str = format_bytes(copied_bytes)
        total_str = format_bytes(total_bytes)
        speed_str = f"{format_bytes(speed)}/s"

        def _update():
            self.pbar_local_copy.set(pct)
            self.lbl_copy_status.configure(
                text=f"📥 Tahap 1 (Buffer Lokal): {current_file} ({pct_text}% • {copied_str}/{total_str} • {speed_str})"
            )

        self.after(0, _update)

    def _on_copy_complete_callback(self, success: bool, message: str):
        def _finish():
            self.btn_select_files.configure(state="normal")
            self.btn_select_folder.configure(state="normal")

            if success:
                self.pbar_local_copy.set(1.0)
                self.lbl_copy_status.configure(
                    text=f"✅ {message} (File masuk antrean upload Google Drive)",
                    text_color=COLOR_SUCCESS
                )
                self.after(4000, lambda: self.copy_progress_frame.pack_forget())
            else:
                self.lbl_copy_status.configure(
                    text=f"⚠️ {message}",
                    text_color=COLOR_DANGER
                )
                self.after(4000, lambda: self.copy_progress_frame.pack_forget())

        self.after(0, _finish)

    def _on_cancel_copy(self):
        """Membatalkan proses salin lokal dan langsung menghapus sisa file & cache."""
        self.btn_cancel_copy.configure(state="disabled", text="Membatalkan...")
        self.lbl_copy_status.configure(text="Membatalkan & membersihkan cache...", text_color=COLOR_DANGER)
        self.uploader.cancel()

    def _on_cancel_cloud_transfer(self, file_name: str):
        """Membatalkan upload file ke Google Drive dan langsung mempurge cache lokalnya."""
        confirm = messagebox.askyesno(
            "Batalkan Upload & Hapus Cache",
            f"Apakah kamu yakin ingin membatalkan upload file:\n\n'{file_name}'\n\n"
            "File akan dihapus dari antrean dan ruang disk cache lokal akan segera dibebaskan."
        )
        if not confirm:
            return

        def _worker():
            target_virtual = os.path.join(self.default_target_dir, file_name)
            purge_file_and_cache(target_virtual)

        threading.Thread(target=_worker, daemon=True).start()

    def _create_metric_card(self, parent, col: int, title: str, default_val: str, val_color: str):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color=BG_CARD, border_width=1, border_color=BORDER_DARK)
        card.grid(row=0, column=col, padx=4, sticky="ew")

        lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color=GOLD_PRIMARY)
        lbl_t.pack(anchor="w", padx=12, pady=(8, 2))

        lbl_v = ctk.CTkLabel(card, text=default_val, font=ctk.CTkFont(size=16, weight="bold"), text_color=val_color)
        lbl_v.pack(anchor="w", padx=12, pady=(0, 8))

        return lbl_v

    def _start_polling(self):
        self._update_data()

    def _update_data(self):
        if not self.is_monitoring:
            return

        try:
            stats = self.monitor.get_stats()
            self._render_stats(stats)
        except Exception:
            pass

        self.poll_job = self.after(1500, self._update_data)

    def _render_stats(self, stats: dict):
        is_conn = stats.get("is_connected", False)
        is_up = stats.get("is_uploading", False)
        speed_str = stats.get("speed_str", "0 B/s")
        transferred_str = stats.get("transferred_str", "0 B")
        completed_count = stats.get("transfers_completed", 0)
        transferring = stats.get("transferring", [])
        queued = stats.get("queued", [])

        if not is_conn:
            self.card_status.configure(text="○ MOUNT MATI", text_color=TEXT_MUTED)
            self.card_speed.configure(text="0 B/s")
        elif is_up:
            q_cnt = len(queued)
            if q_cnt > 0:
                self.card_status.configure(text=f"🚀 UPLOAD (+{q_cnt} ANTRE)", text_color=GOLD_PRIMARY)
            else:
                self.card_status.configure(text="🚀 MENGUNGGAH...", text_color=GOLD_PRIMARY)
            self.card_speed.configure(text=speed_str)
        elif len(queued) > 0:
            self.card_status.configure(text=f"⏳ {len(queued)} ANTREAN", text_color=COLOR_WARNING)
            self.card_speed.configure(text="0 B/s")
        else:
            self.card_status.configure(text="● IDLE (SINKRON)", text_color=COLOR_SUCCESS)
            self.card_speed.configure(text="0 B/s")

        self.card_total.configure(text=transferred_str)
        self.card_completed.configure(text=f"{completed_count} Selesai")

        # Optimasi UI: Hindari destroy & re-create widget jika status tidak berubah
        if not is_conn:
            if self.last_view_state != "disconnected":
                self.last_view_state = "disconnected"
                self._clear_scroll_transfers()
                msg = ctk.CTkLabel(
                    self.scroll_transfers,
                    text="Drive virtual sedang tidak aktif. Pasang (Mount) drive di Dashboard untuk memulai pemantauan.",
                    text_color=TEXT_MUTED,
                    font=ctk.CTkFont(size=13)
                )
                msg.pack(pady=40)
            return

        if not transferring and not queued:
            if self.last_view_state != "empty":
                self.last_view_state = "empty"
                self._clear_scroll_transfers()
                empty_frame = ctk.CTkFrame(self.scroll_transfers, fg_color="transparent")
                empty_frame.pack(pady=35)

                icon = ctk.CTkLabel(empty_frame, text="✨", font=ctk.CTkFont(size=28), text_color=GOLD_PRIMARY)
                icon.pack()

                msg = ctk.CTkLabel(
                    empty_frame,
                    text="Semua file sudah tersinkronisasi sempurna!\nTidak ada antrean upload yang tertunda saat ini.",
                    text_color=TEXT_CREAM,
                    font=ctk.CTkFont(size=13),
                    justify="center"
                )
                msg.pack(pady=(5, 0))
            return

        # Render list file aktif & antrean
        self.last_view_state = "transferring"
        self._clear_scroll_transfers()

        # 1. FILE YANG SEDANG AKTIF DIUNGGAH (TRANSFERRING)
        if transferring:
            for item in transferring:
                row = ctk.CTkFrame(
                    self.scroll_transfers,
                    corner_radius=10,
                    fg_color=BG_CARD_GOLD,
                    border_width=1,
                    border_color=BORDER_GOLD
                )
                row.pack(fill="x", padx=10, pady=6)

                top_row = ctk.CTkFrame(row, fg_color="transparent")
                top_row.pack(fill="x", padx=15, pady=(12, 4))

                name_frame = ctk.CTkFrame(top_row, fg_color="transparent")
                name_frame.pack(side="left")

                badge_active = ctk.CTkLabel(
                    name_frame,
                    text="⚡ AKTIF UPLOAD",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color=GOLD_PRIMARY,
                    corner_radius=4,
                    text_color=TEXT_DARK,
                    padx=6,
                    pady=1
                )
                badge_active.pack(side="left", padx=(0, 8))

                name_lbl = ctk.CTkLabel(
                    name_frame,
                    text=f"📁 {item['name']}",
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=TEXT_WHITE,
                    anchor="w"
                )
                name_lbl.pack(side="left")

                # Persentase
                pct = item.get("percentage", 0)
                pct_lbl = ctk.CTkLabel(
                    top_row,
                    text=f"{pct}%",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=GOLD_LIGHT
                )
                pct_lbl.pack(side="right")

                # Progress Bar
                pbar = ctk.CTkProgressBar(
                    row,
                    height=8,
                    corner_radius=4,
                    progress_color=GOLD_PRIMARY,
                    fg_color=BG_CARD_INNER
                )
                pbar.pack(fill="x", padx=15, pady=4)
                pbar.set(max(0.0, min(1.0, pct / 100.0)))

                # Sub info row: size, speed, ETA, and Cancel Button
                sub_row = ctk.CTkFrame(row, fg_color="transparent")
                sub_row.pack(fill="x", padx=15, pady=(2, 12))

                size_info = f"📦 {item.get('bytes_str', '0 B')} / {item.get('size_str', '0 B')}"
                speed_info = f"⚡ {item.get('speed_str', '0 B/s')}"
                eta_info = f"⏳ Sisa Waktu: {item.get('eta_str', '--')}"

                lbl_sub = ctk.CTkLabel(
                    sub_row,
                    text=f"{size_info}   •   {speed_info}   •   {eta_info}",
                    font=ctk.CTkFont(size=12),
                    text_color=TEXT_CREAM
                )
                lbl_sub.pack(side="left")

                # Tombol Batalkan Upload & Hapus Cache
                btn_cancel_cloud = ctk.CTkButton(
                    sub_row,
                    text="❌ BATALKAN & PURGE CACHE",
                    width=175,
                    height=26,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color=COLOR_DANGER,
                    hover_color=COLOR_DANGER_HOVER,
                    text_color=TEXT_WHITE,
                    command=lambda f=item['name']: self._on_cancel_cloud_transfer(f)
                )
                btn_cancel_cloud.pack(side="right")

        # 2. DAFTAR FILE YANG MASIH MENGANTRI (QUEUED)
        if queued:
            queue_header = ctk.CTkFrame(self.scroll_transfers, fg_color="transparent")
            queue_header.pack(fill="x", padx=12, pady=(12, 4))

            lbl_q_hdr = ctk.CTkLabel(
                queue_header,
                text=f"⏳ ANTREAN TERTUNDA ({len(queued)} File Menunggu Giliran Upload):",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=GOLD_LIGHT
            )
            lbl_q_hdr.pack(side="left")

            for idx, q_item in enumerate(queued):
                q_row = ctk.CTkFrame(
                    self.scroll_transfers,
                    corner_radius=8,
                    fg_color=BG_CARD_INNER,
                    border_width=1,
                    border_color=BORDER_DARK
                )
                q_row.pack(fill="x", padx=10, pady=4)

                q_inner = ctk.CTkFrame(q_row, fg_color="transparent")
                q_inner.pack(fill="x", padx=14, pady=8)

                q_left = ctk.CTkFrame(q_inner, fg_color="transparent")
                q_left.pack(side="left")

                # Badge nomor antrean
                badge_num = ctk.CTkLabel(
                    q_left,
                    text=f"#{idx + 1}",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color=BG_CARD,
                    corner_radius=4,
                    text_color=GOLD_LIGHT,
                    padx=6,
                    pady=1
                )
                badge_num.pack(side="left", padx=(0, 8))

                q_name = ctk.CTkLabel(
                    q_left,
                    text=f"📄 {q_item['name']}",
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=TEXT_WHITE,
                    anchor="w"
                )
                q_name.pack(side="left", padx=(0, 10))

                q_size = ctk.CTkLabel(
                    q_left,
                    text=f"📦 {q_item['size_str']}",
                    font=ctk.CTkFont(size=12),
                    text_color=TEXT_MUTED
                )
                q_size.pack(side="left", padx=(0, 10))

                q_status = ctk.CTkLabel(
                    q_left,
                    text="⏳ Menunggu Giliran",
                    font=ctk.CTkFont(size=11),
                    text_color=COLOR_WARNING
                )
                q_status.pack(side="left")

                # Tombol Batalkan Antrean
                btn_cancel_q = ctk.CTkButton(
                    q_inner,
                    text="❌ BATALKAN",
                    width=110,
                    height=24,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color=COLOR_DANGER,
                    hover_color=COLOR_DANGER_HOVER,
                    text_color=TEXT_WHITE,
                    command=lambda f=q_item['name']: self._on_cancel_cloud_transfer(f)
                )
                btn_cancel_q.pack(side="right")

    def _clear_scroll_transfers(self):
        for widget in self.scroll_transfers.winfo_children():
            widget.destroy()

    def destroy(self):
        self.is_monitoring = False
        if self.poll_job:
            self.after_cancel(self.poll_job)
        super().destroy()
