import os
import sys
import customtkinter as ctk

from core import (
    find_rclone_binary,
    is_winfsp_installed,
    RcloneConfigManager,
    RcloneExecutor,
    MountManager,
    TransferMonitor
)

from .theme import (
    BG_BASE,
    BG_SIDEBAR,
    BG_CARD,
    GOLD_PRIMARY,
    GOLD_HOVER,
    GOLD_LIGHT,
    GOLD_BORDER,
    TEXT_WHITE,
    TEXT_CREAM,
    TEXT_MUTED,
    TEXT_DARK,
    BORDER_DARK,
    COLOR_SUCCESS,
    COLOR_DANGER,
    TAG_HAZARD,
    BRAND_HEADER
)

from .dashboard_view import DashboardView
from .transfers_view import TransfersView
from .accounts_view import AccountsView
from .union_view import UnionView
from .settings_view import SettingsView
from .logs_view import LogsView

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Inisialisasi backend engine
        self.rclone_bin = find_rclone_binary()
        self.winfsp_ok = is_winfsp_installed()
        self.config_mgr = RcloneConfigManager()
        self.executor = RcloneExecutor(rclone_path=self.rclone_bin)
        self.mount_mgr = MountManager(rclone_path=self.rclone_bin)
        self.transfer_monitor = TransferMonitor()

        # Setup Window
        self.title("Drive-Chan • Astral Engine (Rclone Google Drive Union)")
        self.geometry("1120x720")
        self.minsize(980, 640)

        ctk.set_appearance_mode("dark")
        self.configure(fg_color=BG_BASE)

        self._build_layout()
        self.show_view("dashboard")

    def _build_layout(self):
        # Grid konfigurasi: Kolom 0 untuk sidebar, Kolom 1 untuk content
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Sidebar Frame
        self.sidebar = ctk.CTkFrame(
            self,
            width=230,
            corner_radius=0,
            fg_color=BG_SIDEBAR,
            border_width=1,
            border_color=BORDER_DARK
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(9, weight=1)

        # Sci-Fi Top Header Pill
        top_pill = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        top_pill.grid(row=0, column=0, padx=16, pady=(18, 6), sticky="w")

        lbl_top_tag = ctk.CTkLabel(
            top_pill,
            text=f"{TAG_HAZARD} VFS POOL",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_top_tag.pack(side="left")

        # App Brand Header
        self.lbl_brand = ctk.CTkLabel(
            self.sidebar,
            text="DRIVE-CHAN.",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_WHITE
        )
        self.lbl_brand.grid(row=1, column=0, padx=16, pady=(0, 2), sticky="w")

        self.lbl_sub = ctk.CTkLabel(
            self.sidebar,
            text="ASTRAL STORAGE ENGINE",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=GOLD_LIGHT
        )
        self.lbl_sub.grid(row=2, column=0, padx=16, pady=(0, 20), sticky="w")

        # Nav Buttons
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "⚡ Dashboard HUD"),
            ("transfers", "🚀 Monitor Transfer"),
            ("accounts", "👥 Akun Google Drive"),
            ("union", "🔗 Union Storage Pool"),
            ("settings", "⚙️ Pengaturan Engine"),
            ("logs", "📜 Log Aktivitas")
        ]

        for idx, (view_id, label) in enumerate(nav_items, start=3):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
                height=38,
                corner_radius=10,
                fg_color="transparent",
                text_color=TEXT_CREAM,
                hover_color="#262830",
                command=lambda v=view_id: self.show_view(v)
            )
            btn.grid(row=idx, column=0, padx=12, pady=4, sticky="ew")
            self.nav_buttons[view_id] = btn

        # System Health Card di dasar sidebar (Card Gaya Star Rail)
        health_card = ctk.CTkFrame(
            self.sidebar,
            corner_radius=12,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_DARK
        )
        health_card.grid(row=10, column=0, padx=12, pady=16, sticky="ew")

        # Top Stars row
        stars_row = ctk.CTkFrame(health_card, fg_color="transparent")
        stars_row.pack(fill="x", padx=12, pady=(10, 2))

        lbl_stars = ctk.CTkLabel(
            stars_row,
            text="★ ★ ★ ★ ★",
            font=ctk.CTkFont(size=11),
            text_color=GOLD_PRIMARY
        )
        lbl_stars.pack(side="left")

        lbl_health_badge = ctk.CTkLabel(
            stars_row,
            text="CORE 100%",
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color="#2B2518",
            text_color=GOLD_LIGHT,
            corner_radius=4,
            padx=4,
            pady=1
        )
        lbl_health_badge.pack(side="right")

        rclone_status = "● Rclone: Ready" if self.rclone_bin else "● Rclone: Missing"
        winfsp_status = "● WinFsp: Mounted" if self.winfsp_ok else "● WinFsp: Inactive"
        color_rc = COLOR_SUCCESS if self.rclone_bin else COLOR_DANGER
        color_wf = COLOR_SUCCESS if self.winfsp_ok else COLOR_DANGER

        ctk.CTkLabel(health_card, text=rclone_status, font=ctk.CTkFont(size=11, weight="bold"), text_color=color_rc).pack(anchor="w", padx=12, pady=(4, 1))
        ctk.CTkLabel(health_card, text=winfsp_status, font=ctk.CTkFont(size=11, weight="bold"), text_color=color_wf).pack(anchor="w", padx=12, pady=(1, 10))

        # 2. Main Content Frame
        self.content_container = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_BASE)
        self.content_container.grid(row=0, column=1, sticky="nsew")
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(1, weight=1)

        # Top Global Ribbon Header
        top_ribbon = ctk.CTkFrame(self.content_container, height=36, corner_radius=0, fg_color="#101114")
        top_ribbon.grid(row=0, column=0, sticky="ew")

        lbl_ribbon_left = ctk.CTkLabel(
            top_ribbon,
            text=BRAND_HEADER,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_ribbon_left.pack(side="left", padx=20)

        lbl_ribbon_right = ctk.CTkLabel(
            top_ribbon,
            text="/// MULTI-ACCOUNT POOL • VFS VIRTUAL DISK",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_MUTED
        )
        lbl_ribbon_right.pack(side="right", padx=20)

        self.content_area = ctk.CTkFrame(self.content_container, corner_radius=0, fg_color=BG_BASE)
        self.content_area.grid(row=1, column=0, sticky="nsew")
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

        # Inisialisasi views
        self.views = {
            "dashboard": DashboardView(
                self.content_area,
                self.mount_mgr,
                on_navigate_callback=self.show_view,
                transfer_monitor=self.transfer_monitor
            ),
            "transfers": TransfersView(
                self.content_area,
                transfer_monitor=self.transfer_monitor
            ),
            "accounts": AccountsView(self.content_area, self.config_mgr, self.executor),
            "union": UnionView(self.content_area, self.config_mgr, self.executor),
            "settings": SettingsView(self.content_area, on_save_callback=self._on_settings_saved),
            "logs": LogsView(self.content_area)
        }

    def show_view(self, view_id: str):
        # Update warna aktif nav button (Emas Mewah HSR)
        for vid, btn in self.nav_buttons.items():
            if vid == view_id:
                btn.configure(fg_color=GOLD_PRIMARY, text_color=TEXT_DARK)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_CREAM)

        # Sembunyikan view lain & tampilkan view target
        for vid, view in self.views.items():
            if vid == view_id:
                view.grid(row=0, column=0, sticky="nsew")
                if hasattr(view, "refresh_status"):
                    view.refresh_status()
                elif hasattr(view, "load_accounts"):
                    view.load_accounts()
                elif hasattr(view, "load_union_data"):
                    view.load_union_data()
                elif hasattr(view, "refresh_log"):
                    view.refresh_log()
            else:
                view.grid_forget()

    def _on_settings_saved(self):
        # Refresh dashboard setelah simpan setting
        if "dashboard" in self.views:
            self.views["dashboard"].refresh_status()

