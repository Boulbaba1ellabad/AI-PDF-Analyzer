import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image
import pdfplumber
import pandas as pd
import google.genai as genai
from dotenv import load_dotenv
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import threading
import time

# تحميل الإعدادات
load_dotenv()
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    # v1 stable — supports gemini-1.5-flash
    http_options={"api_version": "v1"},
)

# ============================================================
#  DESIGN TOKENS
# ============================================================
COLORS = {
    # Backgrounds
    "bg_base":       "#0D0F14",
    "bg_sidebar":    "#111318",
    "bg_card":       "#161B24",
    "bg_card_hover": "#1C2230",

    # Accent – Electric Cyan
    "accent":        "#00D4FF",
    "accent_dim":    "#0099BB",
    "accent_glow":   "#0D2A30",   # was #00D4FF22 → opaque dark-cyan tint

    # Text
    "text_primary":  "#E8EDF5",
    "text_secondary": "#7A8599",
    "text_muted":    "#3D4558",

    # Status
    "success":       "#00E5A0",
    "warning":       "#FFB547",
    "error":         "#FF4D6A",

    # Border
    "border":        "#1E2535",
    "border_active": "#1A4A5A",   # was #00D4FF55 → opaque dark-cyan border
}

# Fonts are defined as tuples to avoid "Too early to use font: no default root window"
# They get converted to CTkFont inside __init__ after the root window exists
FONT_DEFS = {
    "logo":     ("Courier New",  18, "bold"),
    "title":    ("Courier New",  20, "bold"),
    "subtitle": ("Segoe UI",     12),
    "body":     ("Segoe UI",     14),
    "small":    ("Segoe UI",     11),
    "mono":     ("Courier New",  13),
    "badge":    ("Courier New",  10, "bold"),
}

# Will be populated after root window creation
FONTS: dict = {}


# ============================================================
#  HELPER WIDGETS
# ============================================================

class Divider(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, height=1, fg_color=COLORS["border"], **kw)


class Badge(ctk.CTkLabel):
    """Pill badge (e.g. status indicators)"""
    # Maps accent colors to their dark-tint backgrounds (no alpha needed)
    _BG_MAP = {
        "#00D4FF": "#0D2A30",
        "#00E5A0": "#0A2820",
        "#FFB547": "#2A1E08",
        "#FF4D6A": "#2A0D12",
        "#7A8599": "#1A1E28",
        "#3D4558": "#151820",
    }

    def __init__(self, master, text, color=None, **kw):
        color = color or COLORS["accent"]
        bg = self._BG_MAP.get(color, COLORS["bg_card"])
        super().__init__(
            master, text=f"  {text}  ",
            font=FONTS.get("badge") or ("Courier New", 10, "bold"),
            text_color=color,
            fg_color=bg,
            corner_radius=6,
            **kw
        )


class SectionHeader(ctk.CTkLabel):
    def __init__(self, master, text, **kw):
        super().__init__(
            master, text=text.upper(),
            font=FONTS.get("badge") or ("Courier New", 10, "bold"),
            text_color=COLORS["text_muted"],
            **kw
        )


class StatCard(ctk.CTkFrame):
    """Small metric card shown in sidebar"""

    def __init__(self, master, label, value="—", accent=COLORS["accent"], **kw):
        super().__init__(
            master,
            fg_color=COLORS["bg_card"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
            **kw
        )
        self.val_label = ctk.CTkLabel(
            self, text=value,
            font=("Courier New", 22, "bold"),
            text_color=accent,
        )
        self.val_label.pack(pady=(12, 2))
        ctk.CTkLabel(
            self, text=label,
            font=("Segoe UI", 11),
            text_color=COLORS["text_secondary"],
        ).pack(pady=(0, 12))

    def update_value(self, value):
        self.val_label.configure(text=value)


# ============================================================
#  MAIN APPLICATION
# ============================================================

class AIAnalyzerPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Build CTkFont objects NOW — root window already exists at this point
        global FONTS
        for key, spec in FONT_DEFS.items():
            if len(spec) == 3:
                FONTS[key] = ctk.CTkFont(
                    family=spec[0], size=spec[1], weight=spec[2])
            else:
                FONTS[key] = ctk.CTkFont(family=spec[0], size=spec[1])

        self.title("AI Document Intelligence Pro")
        self.geometry("1200x780")
        self.minsize(960, 640)
        self.configure(fg_color=COLORS["bg_base"])

        # State
        self.current_file = None
        self.is_processing = False
        self._dot_count = 0

        self._build_layout()

    # --------------------------------------------------------
    #  LAYOUT BUILDER
    # --------------------------------------------------------

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    # ---- SIDEBAR ----
    def _build_sidebar(self):
        self._sb = ctk.CTkFrame(
            self, width=240, corner_radius=0,
            fg_color=COLORS["bg_sidebar"],
            border_width=0,
        )
        self._sb.grid(row=0, column=0, sticky="nsew")
        self._sb.grid_propagate(False)
        self._sb.grid_rowconfigure(8, weight=1)
        sb = self._sb

        # ── Logo block ──
        logo_frame = ctk.CTkFrame(sb, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(28, 4), sticky="w")

        ctk.CTkLabel(
            logo_frame, text="◈",
            font=ctk.CTkFont(size=26),
            text_color=COLORS["accent"],
        ).pack(side="left", padx=(0, 8))

        title_col = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_col.pack(side="left")
        self._logo_name_label = ctk.CTkLabel(
            title_col, text="AI ANALYZER",
            font=FONTS["logo"],
            text_color=COLORS["text_primary"],
        )
        self._logo_name_label.pack(anchor="w")
        self._logo_sub_label = ctk.CTkLabel(
            title_col, text="Document Intelligence",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        )
        self._logo_sub_label.pack(anchor="w")

        # ── Thin separator ──
        Divider(sb).grid(row=1, column=0, sticky="ew", padx=20, pady=(16, 20))

        # ── Section label ──
        self._section_actions = SectionHeader(sb, "Actions")
        self._section_actions.grid(row=2, column=0, padx=24, sticky="w")

        # ── Primary CTA ──
        self.select_btn = ctk.CTkButton(
            sb,
            text="  ⊕  Open PDF",
            command=self.select_file,
            height=44,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            text_color="#0D0F14",
            corner_radius=10,
        )
        self.select_btn.grid(row=3, column=0, padx=20,
                             pady=(10, 6), sticky="ew")

        # ── Secondary CTA ──
        self.save_btn = ctk.CTkButton(
            sb,
            text="  ↓  Export Summary",
            command=self.save_summary,
            state="disabled",
            height=40,
            font=FONTS["body"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_active"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["bg_card_hover"],
            corner_radius=10,
        )
        self.save_btn.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")

        # ── Separator ──
        Divider(sb).grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 16))

        # ── Stats section ──
        self._section_stats = SectionHeader(sb, "Analysis Stats")
        self._section_stats.grid(row=6, column=0, padx=24, sticky="w")

        stats_frame = ctk.CTkFrame(sb, fg_color="transparent")
        stats_frame.grid(row=7, column=0, padx=16, pady=(10, 0), sticky="ew")
        stats_frame.grid_columnconfigure((0, 1), weight=1)

        self.stat_pages = StatCard(stats_frame, "Pages")
        self.stat_pages.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        self.stat_words = StatCard(
            stats_frame, "Words", accent=COLORS["success"])
        self.stat_words.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        self.stat_tables = StatCard(
            stats_frame, "Tables", accent=COLORS["warning"])
        self.stat_tables.grid(row=1, column=0, padx=4, pady=4, sticky="ew")

        self.stat_status = StatCard(
            stats_frame, "Status", value="Idle", accent=COLORS["text_secondary"])
        self.stat_status.grid(row=1, column=1, padx=4, pady=4, sticky="ew")

        # ── Bottom: Appearance ──
        Divider(sb).grid(row=9, column=0, sticky="ew", padx=20, pady=(0, 12))

        bottom = ctk.CTkFrame(sb, fg_color="transparent")
        bottom.grid(row=10, column=0, padx=20, pady=(0, 20), sticky="ew")
        bottom.grid_columnconfigure(1, weight=1)

        self._theme_label = ctk.CTkLabel(
            bottom, text="Theme",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        )
        self._theme_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.appearance_menu = ctk.CTkSegmentedButton(
            bottom,
            values=["Dark", "Light"],
            command=self.change_appearance_mode,
            font=FONTS["small"],
            height=28,
        )
        self.appearance_menu.set("Dark")
        self.appearance_menu.grid(row=0, column=1, sticky="ew")

    # ---- MAIN PANEL ----
    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, padx=(0, 24), pady=24, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)

        # ── Top bar ──
        topbar = ctk.CTkFrame(main, fg_color="transparent")
        topbar.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        topbar.grid_columnconfigure(0, weight=1)

        self._title_label = ctk.CTkLabel(
            topbar,
            text="Document Analysis",
            font=FONTS["title"],
            text_color=COLORS["text_primary"],
        )
        self._title_label.grid(row=0, column=0, sticky="w")

        self.file_badge = Badge(topbar, "No file loaded",
                                color=COLORS["text_muted"])
        self.file_badge.grid(row=0, column=1, sticky="e")

        # ── Progress row ──
        progress_row = ctk.CTkFrame(main, fg_color="transparent")
        progress_row.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        progress_row.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(
            progress_row,
            height=4,
            corner_radius=2,
            fg_color=COLORS["border"],
            progress_color=COLORS["accent"],
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_row, text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        )
        self.progress_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        # ── Tab view (Summary / Raw Text) ──
        self.tab_view = ctk.CTkTabview(
            main,
            fg_color=COLORS["bg_card"],
            segmented_button_fg_color=COLORS["bg_sidebar"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_dim"],
            segmented_button_unselected_color=COLORS["bg_sidebar"],
            segmented_button_unselected_hover_color=COLORS["bg_card_hover"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=14,
        )
        self.tab_view.grid(row=3, column=0, sticky="nsew")

        tab_summary = self.tab_view.add("  ✦ AI Summary  ")
        tab_summary.grid_columnconfigure(0, weight=1)
        tab_summary.grid_rowconfigure(0, weight=1)

        # Empty state placeholder
        self.empty_state = ctk.CTkFrame(tab_summary, fg_color="transparent")
        self.empty_state.grid(row=0, column=0, sticky="nsew")
        self.empty_state.grid_columnconfigure(0, weight=1)
        self.empty_state.grid_rowconfigure(0, weight=1)

        inner = ctk.CTkFrame(self.empty_state, fg_color="transparent")
        inner.grid(row=0, column=0)
        self._empty_labels = []
        for txt, fnt in [
            ("◈",                              ctk.CTkFont(size=48)),
            ("Drop a PDF to begin",            ctk.CTkFont(
                family="Segoe UI", size=16)),
            ("Click  ⊕ Open PDF  in the sidebar", FONTS["small"]),
        ]:
            lbl = ctk.CTkLabel(inner, text=txt, font=fnt,
                               text_color=COLORS["text_muted"])
            lbl.pack(pady=(8, 4) if txt == "Drop a PDF to begin" else 0)
            self._empty_labels.append(lbl)

        # Result textbox (hidden until content ready)
        self.result_text = ctk.CTkTextbox(
            tab_summary,
            font=FONTS["mono"],
            spacing3=10,
            corner_radius=0,
            border_width=0,
            fg_color="transparent",
            text_color=COLORS["text_primary"],
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent_dim"],
            wrap="word",
        )
        # grid but hidden initially
        self.result_text.grid(row=0, column=0, sticky="nsew", padx=16, pady=8)
        self.result_text.grid_remove()

    # --------------------------------------------------------
    #  LOGIC
    # --------------------------------------------------------

    def fix_arabic(self, text):
        reshaped_text = reshape(text)
        return get_display(reshaped_text)

    # Light theme palette
    COLORS_LIGHT = {
        "bg_base":       "#F0F2F7",
        "bg_sidebar":    "#E4E8F0",
        "bg_card":       "#FFFFFF",
        "bg_card_hover": "#EBF0FA",
        "accent":        "#0088AA",
        "accent_dim":    "#006688",
        "accent_glow":   "#CCF0FA",
        "text_primary":  "#111827",
        "text_secondary": "#4B5563",
        "text_muted":    "#9CA3AF",
        "success":       "#059669",
        "warning":       "#D97706",
        "error":         "#DC2626",
        "border":        "#D1D5DB",
        "border_active": "#7DD3F0",
    }

    COLORS_DARK = {
        "bg_base":       "#0D0F14",
        "bg_sidebar":    "#111318",
        "bg_card":       "#161B24",
        "bg_card_hover": "#1C2230",
        "accent":        "#00D4FF",
        "accent_dim":    "#0099BB",
        "accent_glow":   "#0D2A30",
        "text_primary":  "#E8EDF5",
        "text_secondary": "#7A8599",
        "text_muted":    "#3D4558",
        "success":       "#00E5A0",
        "warning":       "#FFB547",
        "error":         "#FF4D6A",
        "border":        "#1E2535",
        "border_active": "#1A4A5A",
    }

    def change_appearance_mode(self, mode):
        ctk.set_appearance_mode(mode)
        p = self.COLORS_LIGHT if mode == "Light" else self.COLORS_DARK
        COLORS.update(p)

        # ── Root window ──
        self.configure(fg_color=p["bg_base"])

        # ── Sidebar frame ──
        self._sb.configure(fg_color=p["bg_sidebar"])

        # ── Sidebar labels ──
        self._logo_name_label.configure(text_color=p["text_primary"])
        self._logo_sub_label.configure(text_color=p["text_secondary"])
        self._section_actions.configure(text_color=p["text_muted"])
        self._section_stats.configure(text_color=p["text_muted"])
        self._theme_label.configure(text_color=p["text_secondary"])

        # ── Buttons ──
        self.select_btn.configure(
            fg_color=p["accent"], hover_color=p["accent_dim"])
        self.save_btn.configure(
            border_color=p["border_active"], text_color=p["text_secondary"],
            hover_color=p["bg_card_hover"])

        # ── Stat cards ──
        for card in (self.stat_pages, self.stat_words,
                     self.stat_tables, self.stat_status):
            card.configure(fg_color=p["bg_card"], border_color=p["border"])

        # ── Main area ──
        self._title_label.configure(text_color=p["text_primary"])
        self.progress_bar.configure(
            fg_color=p["border"], progress_color=p["accent"])
        self.progress_label.configure(text_color=p["text_secondary"])

        # ── Tab view ──
        self.tab_view.configure(
            fg_color=p["bg_card"],
            segmented_button_fg_color=p["bg_sidebar"],
            segmented_button_selected_color=p["accent"],
            segmented_button_unselected_color=p["bg_sidebar"],
            border_color=p["border"],
        )

        # ── Textbox ──
        self.result_text.configure(text_color=p["text_primary"])

        # ── Empty state labels ──
        for lbl in self._empty_labels:
            lbl.configure(text_color=p["text_muted"])

    def select_file(self):
        if self.is_processing:
            return
        file_path = filedialog.askopenfilename(
            filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.current_file = file_path
            fname = os.path.basename(file_path)
            short = fname if len(fname) <= 28 else fname[:25] + "…"
            self.file_badge.configure(
                text=f"  {short}  ", text_color=COLORS["accent"])
            threading.Thread(target=self.process_document, daemon=True).start()

    def _set_progress(self, value, label=""):
        """Thread-safe progress update via main thread."""
        self.after(0, lambda v=value, l=label: (
            self.progress_bar.set(v),
            self.progress_label.configure(text=l)
        ))

    def _ui(self, fn):
        """Schedule any UI callable on the main thread."""
        self.after(0, fn)

    def _animate_processing(self):
        """Dot animation — only schedules label updates on main thread."""
        dots = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0
        while self.is_processing:
            d = dots[idx % len(dots)]
            self.after(0, lambda t=f"{d}  Analyzing document…":
                       self.progress_label.configure(text=t))
            idx += 1
            time.sleep(0.12)

    def process_document(self):
        # All initial UI touches must go through after()
        self.is_processing = True
        self._ui(lambda: self.select_btn.configure(state="disabled"))
        self._ui(lambda: self.stat_status.update_value("…"))
        self._ui(lambda: self.result_text.grid_remove())
        self._ui(lambda: self.empty_state.grid())

        # Animate dots in background
        anim_thread = threading.Thread(
            target=self._animate_processing, daemon=True)
        anim_thread.start()

        try:
            # Step 1: Extract tables
            self._set_progress(0.2, "Extracting tables…")
            tables_data = []
            page_count = 0
            word_count = 0
            table_count = 0

            with pdfplumber.open(self.current_file) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        tables_data.extend(table)
                        table_count += 1

            if tables_data:
                df = pd.DataFrame(tables_data[1:], columns=tables_data[0])
                df.to_excel("extracted_data.xlsx", index=False)

            # Step 2: Extract text
            self._set_progress(0.45, "Reading text content…")
            text_content = ""
            with pdfplumber.open(self.current_file) as pdf:
                text_content = " ".join(
                    [p.extract_text() for p in pdf.pages if p.extract_text()]
                )
            word_count = len(text_content.split())

            # Step 3: AI analysis — with retry + model fallback
            self._set_progress(0.65, "Sending to AI…")
            models_to_try = ["gemini-2.5-flash",
                             "gemini-1.5-flash", "gemini-1.0-pro"]
            response = None
            last_error = None
            for attempt in range(4):           # up to 4 attempts total
                model_name = models_to_try[min(
                    attempt, len(models_to_try) - 1)]
                try:
                    self._set_progress(0.65 + attempt * 0.05,
                                       f"Attempt {attempt+1} → {model_name}…")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=f"قم بتلخيص هذا النص بشكل احترافي مع نقاط واضحة:\n\n{text_content}"
                    )
                    break   # success — exit loop
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    # 503 = overloaded, 429 = quota → wait then retry
                    if "503" in err_str or "UNAVAILABLE" in err_str:
                        wait = 8 * (attempt + 1)
                        self._set_progress(
                            0.65, f"Server busy — retrying in {wait}s…")
                        time.sleep(wait)
                    elif "429" in err_str or "EXHAUSTED" in err_str:
                        self._set_progress(
                            0.65, "Quota exceeded — waiting 15s…")
                        time.sleep(15)
                    else:
                        raise   # unknown error → surface immediately

            if response is None:
                raise Exception(f"All retry attempts failed.\n{last_error}")

            self._set_progress(1.0, "✓  Analysis complete")
            self.is_processing = False

            # Update stats + show result — all via main thread
            fixed = self.fix_arabic(response.text)

            def _show_result():
                self.stat_pages.update_value(str(page_count))
                self.stat_words.update_value(f"{word_count:,}")
                self.stat_tables.update_value(str(table_count))
                self.stat_status.update_value("Done")
                self.stat_status.val_label.configure(
                    text_color=COLORS["success"])
                self.result_text.delete("1.0", tk.END)
                self.result_text.insert("1.0", fixed)
                self.empty_state.grid_remove()
                self.result_text.grid()
                self.save_btn.configure(
                    state="normal",
                    text_color=COLORS["accent"],
                    border_color=COLORS["border_active"],
                )
            self._ui(_show_result)

        except Exception as e:
            self.is_processing = False
            self._set_progress(0, "✗  An error occurred")
            err_msg = str(e)

            def _show_error():
                self.stat_status.update_value("Err")
                self.stat_status.val_label.configure(
                    text_color=COLORS["error"])
                messagebox.showerror("Error", f"Processing failed:\n{err_msg}")
            self._ui(_show_error)
        finally:
            self._ui(lambda: self.select_btn.configure(state="normal"))

    def save_summary(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.result_text.get("1.0", tk.END))
            messagebox.showinfo("Exported", "Summary saved successfully ✓")


if __name__ == "__main__":
    app = AIAnalyzerPro()
    app.mainloop()
