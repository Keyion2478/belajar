# -*- coding: utf-8 -*-
import os
import subprocess
import customtkinter as ctk
from core.mount_manager import get_default_log_path
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

class LogsView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.log_path = get_default_log_path()

        self._build_ui()
        self.refresh_log()

    def _build_ui(self):
        # Header Box
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(18, 10))

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left")

        lbl_tag = ctk.CTkLabel(
            header_left,
            text=f"{TAG_HAZARD} SYSTEM DIAGNOSTICS // EVENT LOGS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_tag.pack(anchor="w")

        title = ctk.CTkLabel(
            header_left,
            text="LOG AKTIVITAS RCLONE & KERNEL",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_WHITE
        )
        title.pack(anchor="w", pady=(1, 0))

        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        btn_refresh = ctk.CTkButton(
            btn_box,
            text="🔄 REFRESH",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=90,
            height=32,
            corner_radius=6,
            fg_color=BG_CARD,
            hover_color=BG_HOVER,
            text_color=GOLD_LIGHT,
            border_width=1,
            border_color=GOLD_BORDER,
            command=self.refresh_log
        )
        btn_refresh.pack(side="left", padx=(0, 8))

        btn_clear = ctk.CTkButton(
            btn_box,
            text="🧹 BERSIHKAN",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=100,
            height=32,
            corner_radius=6,
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            text_color=TEXT_WHITE,
            command=self._clear_log
        )
        btn_clear.pack(side="left", padx=(0, 8))

        btn_open_folder = ctk.CTkButton(
            btn_box,
            text="📂 BUKA FOLDER",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=110,
            height=32,
            corner_radius=6,
            fg_color=BG_CARD_INNER,
            hover_color=BG_HOVER,
            text_color=TEXT_WHITE,
            border_width=1,
            border_color=BORDER_DARK,
            command=self._open_folder
        )
        btn_open_folder.pack(side="left")

        # Log Text Box Container
        self.textbox = ctk.CTkTextbox(
            self,
            corner_radius=10,
            fg_color=BG_CARD,
            text_color=TEXT_CREAM,
            border_width=1,
            border_color=BORDER_DARK,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none"
        )
        self.textbox.pack(fill="both", expand=True, padx=25, pady=(5, 18))

    def refresh_log(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                self.textbox.configure(state="normal")
                self.textbox.delete("1.0", "end")
                self.textbox.insert("1.0", content)
                self.textbox.see("end")
                self.textbox.configure(state="disabled")
            except Exception as e:
                self.textbox.configure(state="normal")
                self.textbox.delete("1.0", "end")
                self.textbox.insert("1.0", f"Error membaca file log: {e}")
                self.textbox.configure(state="disabled")
        else:
            self.textbox.configure(state="normal")
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", "Belum ada file log yang dibuat.")
            self.textbox.configure(state="disabled")

    def _clear_log(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "w", encoding="utf-8") as f:
                    f.write("")
                self.refresh_log()
            except Exception:
                pass

    def _open_folder(self):
        log_dir = os.path.dirname(self.log_path)
        if os.path.exists(log_dir):
            subprocess.Popen(["explorer.exe", log_dir])
