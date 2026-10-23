# -*- coding: utf-8 -*-
import threading
import customtkinter as ctk
from core import RcloneConfigManager, RcloneExecutor
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

POLICY_MAP = {
    "⚖️ Ratakan ke Akun Paling Kosong (Rekomendasi / epmfs)": "epmfs",
    "⬇️ Koneksi Tercepat Merespons (First Found / epff)": "epff",
    "📦 Habiskan Akun Paling Penuh Dulu (Least Free Space / eplfs)": "eplfs"
}

REVERSE_POLICY_MAP = {
    "epmfs": "⚖️ Ratakan ke Akun Paling Kosong (Rekomendasi / epmfs)",
    "mfs": "⚖️ Ratakan ke Akun Paling Kosong (Rekomendasi / epmfs)",
    "epff": "⬇️ Koneksi Tercepat Merespons (First Found / epff)",
    "ff": "⬇️ Koneksi Tercepat Merespons (First Found / epff)",
    "eplfs": "📦 Habiskan Akun Paling Penuh Dulu (Least Free Space / eplfs)",
    "lfs": "📦 Habiskan Akun Paling Penuh Dulu (Least Free Space / eplfs)"
}

POLICY_DESCRIPTIONS = {
    "epmfs": "💡 Rekomendasi Resmi: File baru dialihkan ke akun yang memiliki sisa kuota paling besar (kapasitas terbagi seimbang & aman).",
    "epff": "💡 First Found: File baru dialihkan ke akun yang merespons koneksi tercepat saat pembuatan file.",
    "eplfs": "💡 Least Free Space: File baru dialihkan ke akun yang sisa kuotanya paling sedikit untuk dihabiskan terlebih dahulu."
}

class UnionView(ctk.CTkFrame):
    def __init__(self, master, config_mgr: RcloneConfigManager, executor: RcloneExecutor, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config_mgr = config_mgr
        self.executor = executor
        self.ordered_accounts: list[str] = []
        self.account_checked: dict[str, ctk.BooleanVar] = {}

        self._build_ui()
        self.load_union_data()

    def _build_ui(self):
        # Header Box
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(18, 10))

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left")

        lbl_tag = ctk.CTkLabel(
            header_left,
            text=f"{TAG_HAZARD} UNION POOL // AGGREGATION ENGINE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        lbl_tag.pack(anchor="w")

        title = ctk.CTkLabel(
            header_left,
            text="PEMBUAT DRIVE GABUNGAN (UNION POOL)",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_WHITE
        )
        title.pack(anchor="w", pady=(1, 0))

        # Instruction Card
        desc_card = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_DARK
        )
        desc_card.pack(fill="x", padx=25, pady=(0, 10))

        desc_text = ctk.CTkLabel(
            desc_card,
            text=(
                "Atur urutan dan strategi penyimpanan akun Google Drive di bawah ini.\n"
                "Gunakan tombol ⬆️ dan ⬇️ untuk menentukan urutan prioritas akun dalam union pool."
            ),
            font=ctk.CTkFont(size=12),
            justify="left",
            text_color=TEXT_CREAM
        )
        desc_text.pack(anchor="w", padx=16, pady=10)

        # Config Row: Union Name & Policy Dropdown
        cfg_frame = ctk.CTkFrame(self, fg_color="transparent")
        cfg_frame.pack(fill="x", padx=25, pady=(0, 5))

        # 1. Union Name
        name_col = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        name_col.pack(side="left", padx=(0, 20))

        lbl_name = ctk.CTkLabel(name_col, text="NAMA REMOTE UNION:", font=ctk.CTkFont(size=11, weight="bold"), text_color=GOLD_PRIMARY)
        lbl_name.pack(anchor="w")

        self.entry_union_name = ctk.CTkEntry(
            name_col,
            width=180,
            placeholder_text="Gdrive_union",
            fg_color=BG_CARD_INNER,
            border_color=BORDER_DARK
        )
        self.entry_union_name.pack(anchor="w", pady=(4, 0))
        self.entry_union_name.insert(0, "Gdrive_union")

        # 2. Storage Strategy / Policy Dropdown
        policy_col = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        policy_col.pack(side="left", fill="x", expand=True)

        lbl_policy = ctk.CTkLabel(policy_col, text="STRATEGI PENYIMPANAN (CREATE POLICY):", font=ctk.CTkFont(size=11, weight="bold"), text_color=GOLD_PRIMARY)
        lbl_policy.pack(anchor="w")

        self.combo_policy = ctk.CTkComboBox(
            policy_col,
            values=list(POLICY_MAP.keys()),
            width=440,
            fg_color=BG_CARD_INNER,
            border_color=BORDER_DARK,
            button_color=GOLD_PRIMARY,
            button_hover_color=GOLD_HOVER,
            command=self._on_policy_change
        )
        self.combo_policy.pack(anchor="w", pady=(4, 0))

        # Policy Description Label
        self.lbl_policy_desc = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=GOLD_LIGHT,
            justify="left"
        )
        self.lbl_policy_desc.pack(anchor="w", padx=25, pady=(4, 8))

        # Checkbox & Reordering Container
        chk_header = ctk.CTkLabel(
            self,
            text="URUTAN PRIORITAS PENGISIAN AKUN:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=GOLD_PRIMARY
        )
        chk_header.pack(anchor="w", padx=25, pady=(5, 5))

        self.scroll_chk = ctk.CTkScrollableFrame(
            self,
            corner_radius=10,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_DARK
        )
        self.scroll_chk.pack(fill="both", expand=True, padx=25, pady=(0, 10))

        # Bottom Actions and Status
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=25, pady=(0, 18))

        self.btn_save = ctk.CTkButton(
            bottom_bar,
            text="💾 SIMPAN KONFIGURASI UNION",
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=GOLD_PRIMARY,
            hover_color=GOLD_HOVER,
            text_color=TEXT_DARK,
            command=self._on_save_click
        )
        self.btn_save.pack(side="left", padx=(0, 10))

        self.btn_test = ctk.CTkButton(
            bottom_bar,
            text="🧪 UJI VALIDITAS",
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=BG_CARD,
            hover_color=BG_HOVER,
            text_color=GOLD_LIGHT,
            border_width=1,
            border_color=GOLD_BORDER,
            command=self._on_test_click
        )
        self.btn_test.pack(side="left")

        self.lbl_result = ctk.CTkLabel(
            bottom_bar,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=480,
            justify="left"
        )
        self.lbl_result.pack(side="left", padx=15)

    def _on_policy_change(self, choice: str):
        policy_key = POLICY_MAP.get(choice, "epff")
        desc = POLICY_DESCRIPTIONS.get(policy_key, "")
        self.lbl_policy_desc.configure(text=desc)

    def load_union_data(self):
        settings = load_settings()
        target_union = settings.get("union_remote", "Gdrive_union")
        self.entry_union_name.delete(0, "end")
        self.entry_union_name.insert(0, target_union)

        remotes = self.config_mgr.get_all_remotes()
        current_upstreams = []
        current_policy = settings.get("create_policy", "epff")

        if target_union in remotes and remotes[target_union]["type"] == "union":
            current_upstreams = remotes[target_union].get("upstreams", [])
            current_policy = remotes[target_union].get("create_policy", current_policy)

        display_policy = REVERSE_POLICY_MAP.get(current_policy, list(POLICY_MAP.keys())[0])
        self.combo_policy.set(display_policy)
        self._on_policy_change(display_policy)

        all_gdrives = self.config_mgr.get_gdrive_remotes()
        self.ordered_accounts = []

        for acc in current_upstreams:
            if acc in all_gdrives and acc not in self.ordered_accounts:
                self.ordered_accounts.append(acc)

        for acc in all_gdrives:
            if acc not in self.ordered_accounts:
                self.ordered_accounts.append(acc)

        for acc in self.ordered_accounts:
            if acc not in self.account_checked:
                is_checked = (acc in current_upstreams) if current_upstreams else True
                self.account_checked[acc] = ctk.BooleanVar(value=is_checked)

        self._render_account_list()

    def _render_account_list(self):
        for widget in self.scroll_chk.winfo_children():
            widget.destroy()

        if not self.ordered_accounts:
            empty = ctk.CTkLabel(
                self.scroll_chk,
                text="Tidak ada akun Google Drive yang ditemukan.",
                text_color=TEXT_MUTED
            )
            empty.pack(pady=20)
            return

        total_items = len(self.ordered_accounts)
        for idx, acc in enumerate(self.ordered_accounts, start=1):
            var = self.account_checked.get(acc)
            if not var:
                var = ctk.BooleanVar(value=True)
                self.account_checked[acc] = var

            row_frame = ctk.CTkFrame(
                self.scroll_chk,
                corner_radius=8,
                fg_color=BG_CARD_INNER,
                border_width=1,
                border_color=BORDER_DARK
            )
            row_frame.pack(fill="x", padx=10, pady=4)

            left_box = ctk.CTkFrame(row_frame, fg_color="transparent")
            left_box.pack(side="left", padx=12, pady=8)

            badge_text = f"#{idx}"
            badge_lbl = ctk.CTkLabel(
                left_box,
                text=badge_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=GOLD_LIGHT,
                fg_color=BG_CARD,
                corner_radius=4,
                width=36,
                pady=2
            )
            badge_lbl.pack(side="left", padx=(0, 10))

            chk = ctk.CTkCheckBox(
                left_box,
                text=f"📁 {acc}",
                variable=var,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=TEXT_WHITE,
                checkmark_color=TEXT_DARK,
                fg_color=GOLD_PRIMARY,
                hover_color=GOLD_HOVER,
                checkbox_width=20,
                checkbox_height=20
            )
            chk.pack(side="left")

            # Right side: Move Up and Move Down buttons
            btn_box = ctk.CTkFrame(row_frame, fg_color="transparent")
            btn_box.pack(side="right", padx=12, pady=6)

            btn_up = ctk.CTkButton(
                btn_box,
                text="⬆️",
                width=40,
                height=26,
                corner_radius=6,
                font=ctk.CTkFont(size=11),
                fg_color=BG_CARD,
                hover_color=BG_HOVER,
                text_color=TEXT_WHITE,
                state="normal" if idx > 1 else "disabled",
                command=lambda a=acc: self._move_account(a, -1)
            )
            btn_up.pack(side="left", padx=(0, 6))

            btn_down = ctk.CTkButton(
                btn_box,
                text="⬇️",
                width=40,
                height=26,
                corner_radius=6,
                font=ctk.CTkFont(size=11),
                fg_color=BG_CARD,
                hover_color=BG_HOVER,
                text_color=TEXT_WHITE,
                state="normal" if idx < total_items else "disabled",
                command=lambda a=acc: self._move_account(a, 1)
            )
            btn_down.pack(side="left")

    def _move_account(self, acc: str, direction: int):
        if acc not in self.ordered_accounts:
            return
        idx = self.ordered_accounts.index(acc)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.ordered_accounts):
            self.ordered_accounts[idx], self.ordered_accounts[new_idx] = (
                self.ordered_accounts[new_idx],
                self.ordered_accounts[idx]
            )
            self._render_account_list()

    def _on_save_click(self) -> bool:
        union_name = self.entry_union_name.get().strip() or "Gdrive_union"
        selected = [acc for acc in self.ordered_accounts if self.account_checked.get(acc, ctk.BooleanVar()).get()]

        if not selected:
            self.lbl_result.configure(
                text="⚠️ Pilih minimal 1 akun untuk digabung!",
                text_color=COLOR_DANGER
            )
            return False

        chosen_policy_display = self.combo_policy.get()
        chosen_policy = POLICY_MAP.get(chosen_policy_display, "epmfs")

        ok = self.config_mgr.set_union_remote(union_name, selected, create_policy=chosen_policy)
        if ok:
            settings = load_settings()
            settings["union_remote"] = union_name
            settings["create_policy"] = chosen_policy
            save_settings(settings)

            policy_name_short = "Ratakan Kuota (epmfs)" if chosen_policy == "epmfs" else chosen_policy
            self.lbl_result.configure(
                text=f"✅ Tersimpan! {len(selected)} akun | Kebijakan: {policy_name_short}",
                text_color=COLOR_SUCCESS
            )
            return True
        else:
            self.lbl_result.configure(
                text="❌ Gagal menyimpan konfigurasi ke rclone.conf.",
                text_color=COLOR_DANGER
            )
            return False

    def _on_test_click(self):
        saved = self._on_save_click()
        if not saved:
            return

        union_name = self.entry_union_name.get().strip() or "Gdrive_union"
        self.btn_test.configure(state="disabled")
        self.lbl_result.configure(text="⏳ Memverifikasi koneksi seluruh akun ke Google...", text_color=COLOR_WARNING)

        def test_worker():
            ok, msg = self.executor.check_union_health(union_name)
            color = COLOR_SUCCESS if ok else COLOR_DANGER
            status_text = f"✅ {msg}" if ok else f"❌ {msg}"
            self.after(0, lambda: self._finish_test(status_text, color))

        threading.Thread(target=test_worker, daemon=True).start()

    def _finish_test(self, status_text: str, color: str):
        self.lbl_result.configure(text=status_text, text_color=color)
        self.btn_test.configure(state="normal")
