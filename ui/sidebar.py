# =============================================================
#  ui/sidebar.py
#  المسؤولية الوحيدة: الشريط الجانبي بالكامل
# =============================================================

import customtkinter as ctk
from ui.theme import ThemeManager, FONTS


class StatCard(ctk.CTkFrame):
    """بطاقة إحصائية صغيرة تعرض قيمة ووصف."""

    def __init__(self, master, label: str, value: str = "—",
                 accent: str = None, **kw):
        theme = ThemeManager()
        C = theme.colors
        accent = accent or C["accent"]

        super().__init__(
            master,
            fg_color=C["bg_card"],
            corner_radius=10,
            border_width=1,
            border_color=C["border"],
            **kw
        )
        self._accent = accent

        self.val_label = ctk.CTkLabel(
            self, text=value,
            font=("Courier New", 22, "bold"),
            text_color=accent,
        )
        self.val_label.pack(pady=(12, 2))

        ctk.CTkLabel(
            self, text=label,
            font=("Segoe UI", 11),
            text_color=C["text_secondary"],
        ).pack(pady=(0, 12))

        # نسجل في ThemeManager لتحديث الألوان تلقائياً
        theme.subscribe(self._on_theme_change)

    def update_value(self, value: str, color: str = None) -> None:
        self.val_label.configure(
            text=value,
            text_color=color or self._accent
        )

    def _on_theme_change(self, C: dict) -> None:
        self.configure(fg_color=C["bg_card"], border_color=C["border"])


# -------------------------------------------------------------
#  Sidebar
# -------------------------------------------------------------

class Sidebar(ctk.CTkFrame):
    """
    الشريط الجانبي الكامل.

    Callbacks (تُمرر من app.py):
        on_open_pdf   : يُستدعى عند الضغط على Open PDF
        on_export     : يُستدعى عند الضغط على Export Summary
        on_theme_change: يُستدعى عند تغيير الثيم (يمرر "Dark"/"Light")
    """

    def __init__(self, master,
                 on_open_pdf,
                 on_export,
                 on_theme_change,
                 **kw):
        self._theme = ThemeManager()
        C = self._theme.colors

        super().__init__(
            master,
            width=240,
            corner_radius=0,
            fg_color=C["bg_sidebar"],
            border_width=0,
            **kw
        )
        self.grid_propagate(False)
        self.grid_rowconfigure(8, weight=1)   # spacer

        # نحفظ الـ callbacks
        self._on_open_pdf    = on_open_pdf
        self._on_export      = on_export
        self._on_theme_change = on_theme_change

        self._build()

        # نسجل للتحديث التلقائي عند تغيير الثيم
        self._theme.subscribe(self._on_theme_change_internal)

    # ── Build ─────────────────────────────────────────────────

    def _build(self):
        C = self._theme.colors
        self._build_logo(C)
        self._build_divider(row=1)
        self._build_actions(C)
        self._build_divider(row=5)
        self._build_stats(C)
        self._build_divider(row=9)
        self._build_theme_switcher(C)

    def _build_logo(self, C):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, padx=20, pady=(28, 4), sticky="w")

        ctk.CTkLabel(
            frame, text="◈",
            font=ctk.CTkFont(size=26),
            text_color=C["accent"],
        ).pack(side="left", padx=(0, 8))

        col = ctk.CTkFrame(frame, fg_color="transparent")
        col.pack(side="left")

        self._lbl_name = ctk.CTkLabel(
            col, text="AI ANALYZER",
            font=FONTS["logo"],
            text_color=C["text_primary"],
        )
        self._lbl_name.pack(anchor="w")

        self._lbl_sub = ctk.CTkLabel(
            col, text="Document Intelligence",
            font=FONTS["small"],
            text_color=C["text_secondary"],
        )
        self._lbl_sub.pack(anchor="w")

    def _build_actions(self, C):
        self._lbl_actions = ctk.CTkLabel(
            self, text="ACTIONS",
            font=FONTS["badge"],
            text_color=C["text_muted"],
        )
        self._lbl_actions.grid(row=2, column=0, padx=24, sticky="w")

        self.btn_open = ctk.CTkButton(
            self,
            text="  ⊕  Open PDF",
            command=self._on_open_pdf,
            height=44,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=C["accent"],
            hover_color=C["accent_dim"],
            text_color="#0D0F14",
            corner_radius=10,
        )
        self.btn_open.grid(row=3, column=0, padx=20,
                           pady=(10, 6), sticky="ew")

        self.btn_export = ctk.CTkButton(
            self,
            text="  ↓  Export Summary",
            command=self._on_export,
            state="disabled",
            height=40,
            font=FONTS["body"],
            fg_color="transparent",
            border_width=1,
            border_color=C["border_active"],
            text_color=C["text_secondary"],
            hover_color=C["bg_card_hover"],
            corner_radius=10,
        )
        self.btn_export.grid(row=4, column=0, padx=20,
                             pady=(0, 20), sticky="ew")

    def _build_stats(self, C):
        self._lbl_stats = ctk.CTkLabel(
            self, text="ANALYSIS STATS",
            font=FONTS["badge"],
            text_color=C["text_muted"],
        )
        self._lbl_stats.grid(row=6, column=0, padx=24, sticky="w")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.grid(row=7, column=0, padx=16, pady=(10, 0), sticky="ew")
        grid.grid_columnconfigure((0, 1), weight=1)

        self.stat_pages  = StatCard(grid, "Pages")
        self.stat_words  = StatCard(grid, "Words",  accent=C["success"])
        self.stat_tables = StatCard(grid, "Tables", accent=C["warning"])
        self.stat_status = StatCard(grid, "Status",
                                    value="Idle", accent=C["text_secondary"])

        self.stat_pages .grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        self.stat_words .grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        self.stat_tables.grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        self.stat_status.grid(row=1, column=1, padx=4, pady=4, sticky="ew")

    def _build_theme_switcher(self, C):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=10, column=0, padx=20, pady=(0, 20), sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        self._lbl_theme = ctk.CTkLabel(
            frame, text="Theme",
            font=FONTS["small"],
            text_color=C["text_secondary"],
        )
        self._lbl_theme.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self._seg_theme = ctk.CTkSegmentedButton(
            frame,
            values=["Dark", "Light"],
            command=self._on_theme_change,
            font=FONTS["small"],
            height=28,
        )
        self._seg_theme.set("Dark")
        self._seg_theme.grid(row=0, column=1, sticky="ew")

    def _build_divider(self, row: int):
        ctk.CTkFrame(
            self, height=1, fg_color=self._theme.colors["border"]
        ).grid(row=row, column=0, sticky="ew", padx=20, pady=(8, 8))

    # ── Public API ────────────────────────────────────────────

    def set_processing(self, is_processing: bool) -> None:
        """يعطّل أو يفعّل الأزرار أثناء المعالجة."""
        state = "disabled" if is_processing else "normal"
        self.btn_open.configure(state=state)

    def update_stats(self, pages: int, words: int,
                     tables: int, status: str,
                     status_color: str = None) -> None:
        """يحدث بطاقات الإحصائيات دفعة واحدة."""
        C = self._theme.colors
        self.stat_pages .update_value(str(pages))
        self.stat_words .update_value(f"{words:,}")
        self.stat_tables.update_value(str(tables))
        self.stat_status.update_value(
            status, color=status_color or C["text_secondary"])

    def enable_export(self) -> None:
        C = self._theme.colors
        self.btn_export.configure(
            state="normal",
            text_color=C["accent"],
            border_color=C["border_active"],
        )

    # ── Theme ─────────────────────────────────────────────────

    def _on_theme_change_internal(self, C: dict) -> None:
        """يحدث ألوان الـ Sidebar عند تغيير الثيم."""
        self.configure(fg_color=C["bg_sidebar"])
        self._lbl_name   .configure(text_color=C["text_primary"])
        self._lbl_sub    .configure(text_color=C["text_secondary"])
        self._lbl_actions.configure(text_color=C["text_muted"])
        self._lbl_stats  .configure(text_color=C["text_muted"])
        self._lbl_theme  .configure(text_color=C["text_secondary"])
        self.btn_open    .configure(fg_color=C["accent"],
                                    hover_color=C["accent_dim"])
        self.btn_export  .configure(border_color=C["border_active"],
                                    text_color=C["text_secondary"],
                                    hover_color=C["bg_card_hover"])