# -*- coding: utf-8 -*-
import threading
import customtkinter as ctk
from core import RcloneConfigManager, RcloneExecutor, format_bytes
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

class AccountsView(ctk.CTkFrame):
    def __init__(self, master, config_mgr: RcloneConfigManager, executor: RcloneExecutor, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config_mgr = config_mgr
        self.executor = executor
        self.account_cards = {}

        self._build_ui()
        self.load_accounts()

    def _build_ui(self):
        # Header Box
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(18, 10))

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left")

        lbl_tag = ctk.CTkLabel(
            header_left,
            text=f"{TAG_HAZARD} AUTHENTICATION // GOOGLE DRIVE ROSTER",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_tag.pack(anchor="w")

        title = ctk.CTkLabel(
            header_left,
            text="MANAJEMEN AKUN GOOGLE DRIVE",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_WHITE
        )
        title.pack(anchor="w", pady=(1, 0))

        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        btn_add = ctk.CTkButton(
            btn_box,
            text="➕ TAMBAH AKUN BARU",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            height=34,
            fg_color=GOLD_PRIMARY,
            hover_color=GOLD_HOVER,
            text_color=TEXT_DARK,
            command=self._on_add_account_click
        )
        btn_add.pack(side="left", padx=(0, 10))

        btn_refresh = ctk.CTkButton(
            btn_box,
            text="🔄 CEK KUOTA",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            height=34,
            fg_color=BG_CARD,
            hover_color=BG_HOVER,
            text_color=GOLD_LIGHT,
            border_width=1,
            border_color=GOLD_BORDER,
            command=self.load_accounts
        )
        btn_refresh.pack(side="left")

        # Scrollable container for account cards
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=12,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_DARK
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=25, pady=(5, 18))

    def load_accounts(self):
        # Bersihkan card lama
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.account_cards.clear()

        remotes = self.config_mgr.get_gdrive_remotes()
        if not remotes:
            empty_lbl = ctk.CTkLabel(
                self.scroll_frame,
                text="Belum ada akun Google Drive yang terdaftar.\nKlik tombol '➕ TAMBAH AKUN BARU' di atas untuk memulai otorisasi OAuth.",
                font=ctk.CTkFont(size=14),
                text_color=TEXT_MUTED
            )
            empty_lbl.pack(pady=40)
            return

        for name in remotes:
            card = self._create_account_card(name)
            self.account_cards[name] = card

        # Background worker checker kuota
        threading.Thread(target=self._check_all_quotas_worker, args=(remotes,), daemon=True).start()

    def _create_account_card(self, name: str) -> dict:
        card_frame = ctk.CTkFrame(
            self.scroll_frame,
            corner_radius=10,
            fg_color=BG_CARD_INNER,
            border_width=1,
            border_color=BORDER_DARK
        )
        card_frame.pack(fill="x", padx=10, pady=6)

        left_col = ctk.CTkFrame(card_frame, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=16, pady=12)

        header_row = ctk.CTkFrame(left_col, fg_color="transparent")
        header_row.pack(anchor="w")

        lbl_badge = ctk.CTkLabel(
            header_row,
            text="[ REMOTE GDRIVE ]",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=GOLD_PRIMARY,
            fg_color=BG_CARD,
            corner_radius=4,
            padx=6,
            pady=1
        )
        lbl_badge.pack(side="left", padx=(0, 8))

        lbl_name = ctk.CTkLabel(
            header_row,
            text=f"{name}",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=TEXT_WHITE
        )
        lbl_name.pack(side="left")

        lbl_status = ctk.CTkLabel(
            left_col,
            text="⏳ Memeriksa kuota & token autentikasi...",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_WARNING
        )
        lbl_status.pack(anchor="w", pady=(4, 0))

        # Right col buttons
        right_col = ctk.CTkFrame(card_frame, fg_color="transparent")
        right_col.pack(side="right", padx=16, pady=12)

        btn_reconnect = ctk.CTkButton(
            right_col,
            text="🔑 LOGIN ULANG",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=110,
            height=28,
            corner_radius=6,
            fg_color=BG_CARD,
            hover_color=BG_HOVER,
            text_color=GOLD_LIGHT,
            border_width=1,
            border_color=GOLD_BORDER,
            command=lambda n=name: self._on_reconnect_click(n)
        )
        btn_reconnect.pack(side="left", padx=(0, 8))

        btn_delete = ctk.CTkButton(
            right_col,
            text="🗑️ HAPUS",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=80,
            height=28,
            corner_radius=6,
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            text_color=TEXT_WHITE,
            command=lambda n=name: self._on_delete_click(n)
        )
        btn_delete.pack(side="left")

        return {
            "frame": card_frame,
            "status_label": lbl_status,
            "reconnect_btn": btn_reconnect
        }

    def _check_all_quotas_worker(self, remotes: list[str]):
        for name in remotes:
            card_info = self.account_cards.get(name)
            if not card_info:
                continue

            quota = self.executor.check_remote_quota(name)
            if quota["ok"]:
                total_s = format_bytes(quota["total"])
                free_s = format_bytes(quota["free"])
                used_s = format_bytes(quota["used"])
                msg = f"● AKTIF | Total: {total_s} (Tersisa: {free_s}, Terpakai: {used_s})"
                color = COLOR_SUCCESS
            else:
                err_text = quota.get("error", "Error")
                msg = f"○ {err_text} (Klik LOGIN ULANG)"
                color = COLOR_DANGER

            # Update UI di thread utama
            self.after(0, lambda ci=card_info, m=msg, c=color: self._update_card_status(ci, m, c))

    def _update_card_status(self, card_info: dict, text: str, color: str):
        try:
            card_info["status_label"].configure(text=text, text_color=color)
        except Exception:
            pass

    def _on_reconnect_click(self, name: str):
        proc = self.executor.launch_reconnect_flow(name)
        def wait_worker():
            proc.wait()
            self.after(1000, self.load_accounts)
        threading.Thread(target=wait_worker, daemon=True).start()

    def _on_add_account_click(self):
        dialog = ctk.CTkInputDialog(
            text="Masukkan nama panggilan untuk akun Google Drive ini\n(Contoh: gdrive_pribadi atau luzia5):",
            title="Tambah Akun Baru"
        )
        account_name = dialog.get_input()
        if account_name:
            clean_name = account_name.strip().replace(" ", "_")
            proc = self.executor.launch_add_account_flow(clean_name)
            def wait_worker():
                proc.wait()
                self.after(1000, self.load_accounts)
            threading.Thread(target=wait_worker, daemon=True).start()

    def _on_delete_click(self, name: str):
        dialog = ctk.CTkInputDialog(
            text=f"Ketik 'HAPUS' untuk mengonfirmasi penghapusan akun '{name}':",
            title="Hapus Akun"
        )
        val = dialog.get_input()
        if val and val.strip().upper() == "HAPUS":
            self.config_mgr.delete_remote(name)
            self.load_accounts()
