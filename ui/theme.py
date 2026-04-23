# =============================================================
#  ui/theme.py
#  المسؤولية الوحيدة: الألوان، الخطوط، وإدارة التبديل بينهما
# =============================================================

import customtkinter as ctk


# -------------------------------------------------------------
#  PALETTES  —  كل theme عبارة عن dictionary مستقل
# -------------------------------------------------------------

_DARK = {
    "bg_base":        "#0D0F14",
    "bg_sidebar":     "#111318",
    "bg_card":        "#161B24",
    "bg_card_hover":  "#1C2230",
    "accent":         "#00D4FF",
    "accent_dim":     "#0099BB",
    "accent_bg":      "#0D2A30",
    "text_primary":   "#E8EDF5",
    "text_secondary": "#7A8599",
    "text_muted":     "#3D4558",
    "success":        "#00E5A0",
    "warning":        "#FFB547",
    "error":          "#FF4D6A",
    "border":         "#1E2535",
    "border_active":  "#1A4A5A",
    # Chat-specific
    "chat_user_bg":   "#1A2A35",
    "chat_ai_bg":     "#161B24",
    "chat_input_bg":  "#111318",
}

_LIGHT = {
    "bg_base":        "#F0F2F7",
    "bg_sidebar":     "#E4E8F0",
    "bg_card":        "#FFFFFF",
    "bg_card_hover":  "#EBF0FA",
    "accent":         "#0088AA",
    "accent_dim":     "#006688",
    "accent_bg":      "#CCF0FA",
    "text_primary":   "#111827",
    "text_secondary": "#4B5563",
    "text_muted":     "#9CA3AF",
    "success":        "#059669",
    "warning":        "#D97706",
    "error":          "#DC2626",
    "border":         "#D1D5DB",
    "border_active":  "#7DD3F0",
    # Chat-specific
    "chat_user_bg":   "#D6EEF8",
    "chat_ai_bg":     "#FFFFFF",
    "chat_input_bg":  "#E4E8F0",
}


# -------------------------------------------------------------
#  FONT DEFINITIONS  —  tuples لأن CTkFont يحتاج root window
#  سيتم تحويلها إلى CTkFont objects عند استدعاء init_fonts()
# -------------------------------------------------------------

_FONT_DEFS = {
    "logo":    ("Courier New", 18, "bold"),
    "title":   ("Courier New", 20, "bold"),
    "body":    ("Segoe UI",    14),
    "small":   ("Segoe UI",    11),
    "mono":    ("Courier New", 13),
    "badge":   ("Courier New", 10, "bold"),
    "chat":    ("Segoe UI",    13),
    "chat_ts": ("Segoe UI",     9),   # timestamp
}

# هذا الـ dict هو ما يستخدمه باقي الكود
FONTS: dict = {}


# -------------------------------------------------------------
#  ThemeManager  —  الـ class المسؤولة عن كل شيء
# -------------------------------------------------------------

class ThemeManager:
    """
    Singleton يدير الـ active palette ويخطر المشتركين عند التغيير.

    الاستخدام:
        theme = ThemeManager()
        C = theme.colors          # dict الألوان الحالية
        theme.subscribe(callback)  # callback يُستدعى عند تغيير الثيم
        theme.switch("Light")
    """

    _instance = None   # Singleton pattern

    def __new__(cls):
        # نضمن وجود instance واحدة فقط في التطبيق كله
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._mode = "Dark"
        self.colors: dict = dict(_DARK)   # نسخة قابلة للتعديل
        self._subscribers: list = []       # قائمة callbacks
        self._initialized = True

    # ── Public API ────────────────────────────────────────────

    def init_fonts(self):
        """
        يُستدعى مرة واحدة بعد إنشاء root window.
        يحوّل _FONT_DEFS إلى CTkFont objects حقيقية.
        """
        for key, spec in _FONT_DEFS.items():
            if len(spec) == 3:
                FONTS[key] = ctk.CTkFont(
                    family=spec[0], size=spec[1], weight=spec[2])
            else:
                FONTS[key] = ctk.CTkFont(
                    family=spec[0], size=spec[1])

    def switch(self, mode: str):
        """
        يبدّل بين Dark و Light ويخطر جميع المشتركين.
        """
        if mode not in ("Dark", "Light"):
            raise ValueError(f"Unknown mode: {mode}")
        self._mode = mode
        new_palette = _DARK if mode == "Dark" else _LIGHT
        self.colors.update(new_palette)
        ctk.set_appearance_mode(mode)
        self._notify()

    def subscribe(self, callback):
        """
        أي widget يريد التحديث عند تغيير الثيم يسجّل نفسه هنا.
        callback يستقبل dict الألوان الجديدة.
        """
        self._subscribers.append(callback)

    def unsubscribe(self, callback):
        self._subscribers.remove(callback)

    @property
    def mode(self) -> str:
        return self._mode

    # ── Private ───────────────────────────────────────────────

    def _notify(self):
        for cb in self._subscribers:
            try:
                cb(self.colors)
            except Exception as e:
                print(f"[ThemeManager] callback error: {e}")
