# =============================================================
#  ui/chat_panel.py
#  المسؤولية الوحيدة: واجهة المحادثة مع الـ PDF
# =============================================================

import tkinter as tk
import customtkinter as ctk
from ui.theme import ThemeManager, FONTS


class MessageBubble(ctk.CTkFrame):
    """
    فقاعة رسالة واحدة في المحادثة.
    role: "user" أو "assistant"
    """

    def __init__(self, master, content: str, role: str,
                 timestamp: str = "", **kw):
        theme = ThemeManager()
        C = theme.colors

        # نختار لون الخلفية حسب الـ role
        bg = C["chat_user_bg"] if role == "user" else C["chat_ai_bg"]

        super().__init__(
            master,
            fg_color=bg,
            corner_radius=12,
            border_width=1,
            border_color=C["border"],
            **kw
        )

        # ── Header (role + timestamp) ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 2))

        role_text = "You" if role == "user" else "✦ AI"
        role_color = C["accent"] if role == "user" else C["success"]

        ctk.CTkLabel(
            header,
            text=role_text,
            font=FONTS["badge"],
            text_color=role_color,
        ).pack(side="left")

        if timestamp:
            ctk.CTkLabel(
                header,
                text=timestamp,
                font=FONTS["chat_ts"],
                text_color=C["text_muted"],
            ).pack(side="right")

        # ── Content ──
        ctk.CTkLabel(
            self,
            text=content,
            font=FONTS["chat"],
            text_color=C["text_primary"],
            wraplength=520,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(2, 10))

        theme.subscribe(self._on_theme_change)
        self._role = role

    def _on_theme_change(self, C: dict) -> None:
        bg = C["chat_user_bg"] if self._role == "user" else C["chat_ai_bg"]
        self.configure(fg_color=bg, border_color=C["border"])


# -------------------------------------------------------------
#  ChatPanel
# -------------------------------------------------------------

class ChatPanel(ctk.CTkFrame):
    """
    لوحة المحادثة الكاملة:
      - منطقة عرض الرسائل (scrollable)
      - حقل إدخال + زر إرسال
      - زر مسح المحادثة

    Callbacks:
        on_send(message: str) → يُستدعى عند إرسال رسالة
        on_clear()            → يُستدعى عند مسح المحادثة
    """

    def __init__(self, master, on_send, on_clear, **kw):
        theme = ThemeManager()
        C = theme.colors

        super().__init__(
            master,
            fg_color=C["bg_card"],
            corner_radius=14,
            border_width=1,
            border_color=C["border"],
            **kw
        )
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._on_send  = on_send
        self._on_clear = on_clear
        self._theme    = theme

        self._build()
        theme.subscribe(self._on_theme_change)

    # ── Build ─────────────────────────────────────────────────

    def _build(self):
        C = self._theme.colors
        self._build_header(C)
        self._build_messages_area(C)
        self._build_input_area(C)

    def _build_header(self, C):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="  ◈  Chat with PDF",
            font=FONTS["title"],
            text_color=C["text_primary"],
        ).grid(row=0, column=0, sticky="w")

        self._btn_clear = ctk.CTkButton(
            header,
            text="Clear",
            width=60,
            height=28,
            font=FONTS["small"],
            fg_color="transparent",
            border_width=1,
            border_color=C["border"],
            text_color=C["text_secondary"],
            hover_color=C["bg_card_hover"],
            corner_radius=8,
            command=self._handle_clear,
        )
        self._btn_clear.grid(row=0, column=1, sticky="e")

        # خط فاصل
        ctk.CTkFrame(
            self, height=1, fg_color=C["border"]
        ).grid(row=1, column=0, sticky="ew", padx=0, pady=0)

    def _build_messages_area(self, C):
        """منطقة الرسائل القابلة للتمرير."""
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent_dim"],
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self._scroll.grid_columnconfigure(0, weight=1)

        # Empty state
        self._empty_frame = ctk.CTkFrame(
            self._scroll, fg_color="transparent")
        self._empty_frame.grid(row=0, column=0, sticky="nsew")

        self._lbl_empty = ctk.CTkLabel(
            self._empty_frame,
            text="◈\n\nاسأل أي سؤال عن محتوى الـ PDF\nمثال: ما هي الأطراف المذكورة في هذا العقد؟",
            font=FONTS["body"],
            text_color=C["text_muted"],
            justify="center",
        )
        self._lbl_empty.pack(expand=True, pady=60)

        self._message_row = 1   # row counter للرسائل

    def _build_input_area(self, C):
        """حقل الإدخال وزر الإرسال."""
        input_frame = ctk.CTkFrame(
            self,
            fg_color=C["chat_input_bg"],
            corner_radius=0,
        )
        input_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        input_frame.grid_columnconfigure(0, weight=1)

        self._input = ctk.CTkTextbox(
            input_frame,
            height=70,
            font=FONTS["chat"],
            fg_color="transparent",
            border_width=0,
            text_color=C["text_primary"],
            wrap="word",
        )
        self._input.grid(row=0, column=0, sticky="ew",
                         padx=(12, 4), pady=10)

        self._btn_send = ctk.CTkButton(
            input_frame,
            text="↑",
            width=44,
            height=44,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=C["accent"],
            hover_color=C["accent_dim"],
            text_color="#0D0F14",
            corner_radius=10,
            command=self._handle_send,
        )
        self._btn_send.grid(row=0, column=1, padx=(0, 12), pady=10)

        # Enter يرسل، Shift+Enter يضيف سطر جديد
        self._input.bind("<Return>",       self._on_enter)
        self._input.bind("<Shift-Return>", self._on_shift_enter)

    # ── Public API ────────────────────────────────────────────

    def add_message(self, content: str, role: str,
                    timestamp: str = "") -> None:
        """يضيف فقاعة رسالة جديدة ويتمرر للأسفل."""
        # نخفي الـ empty state عند أول رسالة
        self._empty_frame.grid_remove()

        bubble = MessageBubble(
            self._scroll,
            content=content,
            role=role,
            timestamp=timestamp,
        )
        bubble.grid(
            row=self._message_row, column=0,
            sticky="ew", padx=8, pady=4
        )
        self._message_row += 1
        self._scroll_to_bottom()

    def add_typing_indicator(self) -> ctk.CTkLabel:
        """يعرض مؤشر 'AI is typing...' ويرجعه لإزالته لاحقاً."""
        self._empty_frame.grid_remove()
        C = self._theme.colors
        lbl = ctk.CTkLabel(
            self._scroll,
            text="  ✦  AI is thinking…",
            font=FONTS["small"],
            text_color=C["text_muted"],
        )
        lbl.grid(row=self._message_row, column=0,
                 sticky="w", padx=20, pady=4)
        self._message_row += 1
        self._scroll_to_bottom()
        return lbl

    def remove_widget(self, widget) -> None:
        """يزيل أي widget (مثل typing indicator) من المحادثة."""
        widget.grid_remove()

    def clear_messages(self) -> None:
        """يمسح كل الرسائل ويعيد الـ empty state."""
        for widget in self._scroll.winfo_children():
            if widget != self._empty_frame:
                widget.destroy()
        self._message_row = 1
        self._empty_frame.grid()
        self._lbl_empty.pack(expand=True, pady=60)

    def set_enabled(self, enabled: bool) -> None:
        """يعطّل أو يفعّل حقل الإدخال وزر الإرسال."""
        state = "normal" if enabled else "disabled"
        self._btn_send.configure(state=state)
        self._input.configure(state=state)

    def get_input_text(self) -> str:
        return self._input.get("1.0", tk.END).strip()

    def clear_input(self) -> None:
        self._input.delete("1.0", tk.END)

    # ── Handlers ──────────────────────────────────────────────

    def _handle_send(self) -> None:
        text = self.get_input_text()
        if text:
            self.clear_input()
            self._on_send(text)

    def _handle_clear(self) -> None:
        self.clear_messages()
        self._on_clear()

    def _on_enter(self, event) -> str:
        self._handle_send()
        return "break"   # يمنع إضافة سطر جديد

    def _on_shift_enter(self, event) -> None:
        pass   # السلوك الافتراضي — يضيف سطر جديد

    def _scroll_to_bottom(self) -> None:
        self._scroll.after(50, lambda: self._scroll._parent_canvas.yview_moveto(1.0))

    # ── Theme ─────────────────────────────────────────────────

    def _on_theme_change(self, C: dict) -> None:
        self.configure(fg_color=C["bg_card"], border_color=C["border"])
        self._lbl_empty.configure(text_color=C["text_muted"])
        self._btn_send.configure(
            fg_color=C["accent"], hover_color=C["accent_dim"])
        self._btn_clear.configure(
            border_color=C["border"], text_color=C["text_secondary"],
            hover_color=C["bg_card_hover"])
        self._input.configure(text_color=C["text_primary"])