# =============================================================
#  app.py
#  المسؤولية الوحيدة: ربط كل المكونات وإدارة تدفق العمل
# =============================================================

import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time

import customtkinter as ctk
from arabic_reshaper import reshape
from bidi.algorithm import get_display

from ui.theme   import ThemeManager, FONTS
from ui.sidebar import Sidebar
from ui.chat_panel import ChatPanel
from core.pdf_processor import PDFProcessor
from core.ai_engine     import AIEngine


class AIAnalyzerApp(ctk.CTk):
    """
    النافذة الرئيسية للتطبيق.
    تربط Sidebar + ChatPanel + TabView مع PDFProcessor + AIEngine.
    """

    def __init__(self):
        super().__init__()

        # ── 1. Theme (أول شيء بعد super().__init__) ──
        self._theme = ThemeManager()
        self._theme.init_fonts()          # ننشئ CTkFont بعد root window
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # ── 2. Core components ──
        self._processor = PDFProcessor()
        self._engine    = AIEngine()
        self._doc       = None            # PDFDocument الحالي
        self._processing = False

        # ── 3. Window setup ──
        C = self._theme.colors
        self.title("AI Document Intelligence Pro")
        self.geometry("1280x800")
        self.minsize(980, 640)
        self.configure(fg_color=C["bg_base"])

        # ── 4. Build UI ──
        self._build_layout()

        # ── 5. Subscribe to theme changes ──
        self._theme.subscribe(self._on_theme_change)

    # ── Layout ────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self._sidebar = Sidebar(
            self,
            on_open_pdf=self._open_pdf,
            on_export=self._export_summary,
            on_theme_change=self._switch_theme,
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")

        # Main area
        self._build_main()

    def _build_main(self):
        C = self._theme.colors

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, padx=(0, 24), pady=24, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        # ── Top bar ──
        topbar = ctk.CTkFrame(main, fg_color="transparent")
        topbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        topbar.grid_columnconfigure(0, weight=1)

        self._lbl_title = ctk.CTkLabel(
            topbar,
            text="Document Analysis",
            font=FONTS["title"],
            text_color=C["text_primary"],
        )
        self._lbl_title.grid(row=0, column=0, sticky="w")

        self._lbl_file = ctk.CTkLabel(
            topbar,
            text="  No file loaded  ",
            font=FONTS["badge"],
            text_color=C["text_muted"],
            fg_color=C["bg_card"],
            corner_radius=6,
        )
        self._lbl_file.grid(row=0, column=1, sticky="e")

        # ── Progress bar ──
        progress_frame = ctk.CTkFrame(main, fg_color="transparent")
        progress_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        progress_frame.grid_columnconfigure(0, weight=1)

        self._progress = ctk.CTkProgressBar(
            progress_frame,
            height=4,
            corner_radius=2,
            fg_color=C["border"],
            progress_color=C["accent"],
        )
        self._progress.grid(row=0, column=0, sticky="ew")
        self._progress.set(0)

        self._lbl_progress = ctk.CTkLabel(
            progress_frame, text="",
            font=FONTS["small"],
            text_color=C["text_secondary"],
        )
        self._lbl_progress.grid(row=1, column=0, sticky="w", pady=(3, 0))

        # ── Tab view ──
        self._tabs = ctk.CTkTabview(
            main,
            fg_color=C["bg_card"],
            segmented_button_fg_color=C["bg_sidebar"],
            segmented_button_selected_color=C["accent"],
            segmented_button_selected_hover_color=C["accent_dim"],
            segmented_button_unselected_color=C["bg_sidebar"],
            segmented_button_unselected_hover_color=C["bg_card_hover"],
            text_color=C["text_primary"],
            border_color=C["border"],
            border_width=1,
            corner_radius=14,
        )
        self._tabs.grid(row=2, column=0, sticky="nsew")

        # Tab 1: AI Summary
        tab_summary = self._tabs.add("  ✦ AI Summary  ")
        tab_summary.grid_columnconfigure(0, weight=1)
        tab_summary.grid_rowconfigure(0, weight=1)
        self._build_summary_tab(tab_summary, C)

        # Tab 2: Chat
        tab_chat = self._tabs.add("  ◈ Chat with PDF  ")
        tab_chat.grid_columnconfigure(0, weight=1)
        tab_chat.grid_rowconfigure(0, weight=1)
        self._build_chat_tab(tab_chat)

    def _build_summary_tab(self, parent, C):
        # Empty state
        self._empty_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._empty_frame.grid(row=0, column=0, sticky="nsew")
        self._empty_frame.grid_columnconfigure(0, weight=1)
        self._empty_frame.grid_rowconfigure(0, weight=1)

        inner = ctk.CTkFrame(self._empty_frame, fg_color="transparent")
        inner.grid(row=0, column=0)

        self._empty_labels = []
        for txt, fnt in [
            ("◈",                               ctk.CTkFont(size=48)),
            ("Drop a PDF to begin",             ctk.CTkFont(family="Segoe UI", size=16)),
            ("Click  ⊕ Open PDF  in the sidebar", FONTS["small"]),
        ]:
            lbl = ctk.CTkLabel(
                inner, text=txt, font=fnt, text_color=C["text_muted"])
            lbl.pack(pady=(8, 4) if "Drop" in txt else 0)
            self._empty_labels.append(lbl)

        # Result textbox
        self._txt_summary = ctk.CTkTextbox(
            parent,
            font=FONTS["mono"],
            spacing3=10,
            corner_radius=0,
            border_width=0,
            fg_color="transparent",
            text_color=C["text_primary"],
            wrap="word",
        )
        self._txt_summary.grid(row=0, column=0, sticky="nsew",
                                padx=16, pady=8)
        self._txt_summary.grid_remove()

    def _build_chat_tab(self, parent):
        self._chat_panel = ChatPanel(
            parent,
            on_send=self._on_chat_send,
            on_clear=self._on_chat_clear,
        )
        self._chat_panel.grid(row=0, column=0, sticky="nsew")

    # ── Callbacks: PDF ────────────────────────────────────────

    def _open_pdf(self):
        if self._processing:
            return
        path = filedialog.askopenfilename(
            filetypes=[("PDF Files", "*.pdf")])
        if path:
            threading.Thread(
                target=self._process_pdf,
                args=(path,),
                daemon=True
            ).start()

    def _process_pdf(self, path: str):
        self._processing = True
        self._ui(lambda: self._sidebar.set_processing(True))
        self._ui(lambda: self._txt_summary.grid_remove())
        self._ui(lambda: self._empty_frame.grid())

        # Animation
        anim = threading.Thread(target=self._animate, daemon=True)
        anim.start()

        try:
            # Step 1: Extract PDF
            self._set_progress(0.25, "Extracting PDF content…")
            self._doc = self._processor.process(path)

            # Step 2: Load into AI engine
            self._set_progress(0.50, "Preparing AI engine…")
            self._engine.load_document(self._doc.full_text)

            # Step 3: Summarize
            self._set_progress(0.70, "Generating summary…")
            summary = self._engine.summarize()

            self._set_progress(1.0, "✓  Analysis complete")
            self._processing = False

            # Update UI
            fixed = self._fix_arabic(summary)
            def _show():
                # File badge
                self._lbl_file.configure(
                    text=f"  {self._doc.short_name}  ",
                    text_color=self._theme.colors["accent"],
                )
                # Stats
                self._sidebar.update_stats(
                    pages=self._doc.page_count,
                    words=self._doc.word_count,
                    tables=self._doc.table_count,
                    status="Done",
                    status_color=self._theme.colors["success"],
                )
                # Summary text
                self._txt_summary.delete("1.0", tk.END)
                self._txt_summary.insert("1.0", fixed)
                self._empty_frame.grid_remove()
                self._txt_summary.grid()
                self._sidebar.enable_export()

            self._ui(_show)

        except Exception as e:
            self._processing = False
            self._set_progress(0, "✗  Error occurred")
            err = str(e)
            self._ui(lambda: (
                self._sidebar.update_stats(0, 0, 0, "Err",
                    self._theme.colors["error"]),
                messagebox.showerror("Error", f"Processing failed:\n{err}")
            ))
        finally:
            self._ui(lambda: self._sidebar.set_processing(False))

    # ── Callbacks: Chat ───────────────────────────────────────

    def _on_chat_send(self, message: str):
        if not self._engine.has_document:
            messagebox.showwarning(
                "No Document",
                "Please open a PDF file first.")
            return

        # عرض رسالة المستخدم فوراً
        self._chat_panel.add_message(message, role="user")
        self._chat_panel.set_enabled(False)

        # typing indicator
        indicator = self._chat_panel.add_typing_indicator()

        def _ask():
            try:
                answer = self._engine.chat(message)
                fixed  = self._fix_arabic(answer)
                def _show():
                    self._chat_panel.remove_widget(indicator)
                    self._chat_panel.add_message(fixed, role="assistant")
                    self._chat_panel.set_enabled(True)
                self._ui(_show)
            except Exception as e:
                err = str(e)
                def _err():
                    self._chat_panel.remove_widget(indicator)
                    self._chat_panel.add_message(
                        f"⚠ Error: {err}", role="assistant")
                    self._chat_panel.set_enabled(True)
                self._ui(_err)

        threading.Thread(target=_ask, daemon=True).start()

    def _on_chat_clear(self):
        self._engine.clear_chat()

    # ── Callbacks: Export ─────────────────────────────────────

    def _export_summary(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._txt_summary.get("1.0", tk.END))
            messagebox.showinfo("Exported", "Summary saved successfully ✓")

    # ── Theme ─────────────────────────────────────────────────

    def _switch_theme(self, mode: str):
        self._theme.switch(mode)

    def _on_theme_change(self, C: dict):
        self.configure(fg_color=C["bg_base"])
        self._lbl_title.configure(text_color=C["text_primary"])
        self._lbl_file .configure(fg_color=C["bg_card"])
        self._progress .configure(fg_color=C["border"],
                                   progress_color=C["accent"])
        self._lbl_progress.configure(text_color=C["text_secondary"])
        self._tabs.configure(
            fg_color=C["bg_card"],
            segmented_button_fg_color=C["bg_sidebar"],
            segmented_button_selected_color=C["accent"],
            segmented_button_unselected_color=C["bg_sidebar"],
            border_color=C["border"],
        )
        self._txt_summary.configure(text_color=C["text_primary"])
        for lbl in self._empty_labels:
            lbl.configure(text_color=C["text_muted"])

    # ── Helpers ───────────────────────────────────────────────

    def _ui(self, fn):
        """يجدول أي UI update على الـ main thread."""
        self.after(0, fn)

    def _set_progress(self, value: float, label: str = ""):
        self.after(0, lambda v=value, l=label: (
            self._progress.set(v),
            self._lbl_progress.configure(text=l)
        ))

    def _animate(self):
        """مؤشر دوّار أثناء المعالجة."""
        frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        i = 0
        while self._processing:
            f = frames[i % len(frames)]
            self.after(0, lambda t=f"{f}  Processing…":
                       self._lbl_progress.configure(text=t))
            i += 1
            time.sleep(0.12)

    def _fix_arabic(self, text: str) -> str:
        return get_display(reshape(text))