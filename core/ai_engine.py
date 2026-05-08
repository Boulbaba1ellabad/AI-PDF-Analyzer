# =============================================================
#  core/ai_engine.py
#  المسؤولية الوحيدة: كل تواصل مع Gemini API
#  التلخيص + Chat مع الـ PDF + إدارة تاريخ المحادثة
# =============================================================

import os
import time
from dataclasses import dataclass, field
from typing import Optional
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()


# -------------------------------------------------------------
#  ChatMessage  —  يمثل رسالة واحدة في المحادثة
# -------------------------------------------------------------

@dataclass
class ChatMessage:
    """
    رسالة واحدة في المحادثة.
    role: "user" أو "assistant"
    """
    role:      str
    content:   str
    timestamp: str = ""

    def __post_init__(self):
        """يُستدعى تلقائياً بعد __init__ في dataclass."""
        if not self.timestamp:
            from datetime import datetime
            self.timestamp = datetime.now().strftime("%H:%M")


# -------------------------------------------------------------
#  AIEngine  —  الـ Class الرئيسية
# -------------------------------------------------------------

class AIEngine:
    """
    واجهة موحدة للتحدث مع Gemini API.

    المسؤوليات:
      - تلخيص نص PDF
      - الإجابة على أسئلة المستخدم بناءً على محتوى الـ PDF
      - حفظ تاريخ المحادثة وإرساله مع كل سؤال (context window)

    الاستخدام:
        engine = AIEngine()
        engine.load_document(doc.full_text)
        summary = engine.summarize()
        answer  = engine.chat("ما هي الأطراف المذكورة في العقد؟")
    """

    # الموديلات مرتبة حسب الأولوية — سيجرب الأول ثم الثاني إن فشل
    _MODELS = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.0-pro",
    ]

    # حد أقصى لعدد الرسائل المحفوظة في الـ context
    # (لتجنب تجاوز حد الـ tokens)
    _MAX_HISTORY = 10

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY not found. Add it to your .env file.")
        self._client        = genai.Client(api_key=api_key)
        self._doc_text: str = ""
        self._history: list[ChatMessage] = []

    # ── Public API ────────────────────────────────────────────

    def load_document(self, text: str) -> None:
        """
        يحمّل نص الـ PDF ويمسح تاريخ المحادثة السابق.
        يُستدعى كلما فتح المستخدم ملفاً جديداً.
        """
        self._doc_text = text
        self._history.clear()

    def summarize(self) -> str:
        """
        يولّد ملخصاً احترافياً للوثيقة المحملة.
        يرجع النص أو يرفع Exception.
        """
        self._require_document()

        prompt = f"""أنت محلل وثائق محترف. قم بتحليل النص التالي وأعطني:

1. **ملخص تنفيذي** (فقرة واحدة)
2. **أهم النقاط** (5 نقاط كحد أقصى)
3. **الكلمات المفتاحية** (5-8 كلمات)

النص:
{self._doc_text[:8000]}
"""
        response = self._call_with_retry(prompt)

        # نحفظ الملخص كأول رسالة في تاريخ المحادثة
        self._history.append(
            ChatMessage(role="assistant", content=response))
        return response

    def chat(self, user_message: str) -> str:
        """
        يستقبل سؤال المستخدم ويرجع إجابة مبنية على محتوى الـ PDF.
        يحتفظ بسياق المحادثة كاملاً.
        """
        self._require_document()

        # نضيف رسالة المستخدم للتاريخ
        self._history.append(
            ChatMessage(role="user", content=user_message))

        # نبني الـ prompt مع السياق الكامل
        prompt = self._build_chat_prompt(user_message)
        response = self._call_with_retry(prompt)

        # نحفظ رد الـ AI
        self._history.append(
            ChatMessage(role="assistant", content=response))

        # نحافظ على حجم التاريخ معقولاً
        self._trim_history()

        return response

    def clear_chat(self) -> None:
        """يمسح تاريخ المحادثة مع الإبقاء على الوثيقة المحملة."""
        self._history.clear()

    @property
    def history(self) -> list[ChatMessage]:
        """نسخة للقراءة فقط من تاريخ المحادثة."""
        return list(self._history)

    @property
    def has_document(self) -> bool:
        return bool(self._doc_text)

    # ── Private ───────────────────────────────────────────────

    def _build_chat_prompt(self, user_message: str) -> str:
        """
        يبني الـ prompt الكامل مع:
        - تعليمات الـ system
        - محتوى الوثيقة
        - تاريخ المحادثة (آخر N رسالة)
        - سؤال المستخدم
        """
        # نأخذ آخر _MAX_HISTORY رسائل فقط (بدون الرسالة الحالية)
        recent = self._history[:-1][-self._MAX_HISTORY:]

        history_text = ""
        for msg in recent:
            prefix = "المستخدم" if msg.role == "user" else "المساعد"
            history_text += f"{prefix}: {msg.content}\n\n"

        prompt = f"""أنت مساعد ذكي متخصص في تحليل الوثائق.
لديك الوثيقة التالية:

--- بداية الوثيقة ---
{self._doc_text[:6000]}
--- نهاية الوثيقة ---

{f"سياق المحادثة السابقة:{chr(10)}{history_text}" if history_text else ""}

سؤال المستخدم: {user_message}

أجب بدقة بناءً على محتوى الوثيقة فقط.
إذا لم تجد الإجابة في الوثيقة، قل ذلك بوضوح.
"""
        return prompt

    def _call_with_retry(self, prompt: str) -> str:
        """
        يستدعي الـ API مع retry تلقائي عند:
        - 503 UNAVAILABLE (سيرفر مشغول)
        - 429 EXHAUSTED   (تجاوز الـ quota)
        يجرب الموديلات بالترتيب عند الفشل.
        """
        last_error = None

        for attempt in range(4):
            model = self._MODELS[min(attempt, len(self._MODELS) - 1)]
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                return response.text

            except Exception as e:
                last_error = e
                err = str(e)

                if "503" in err or "UNAVAILABLE" in err:
                    wait = 8 * (attempt + 1)
                    print(f"[AIEngine] Server busy, retrying in {wait}s...")
                    time.sleep(wait)

                elif "429" in err or "EXHAUSTED" in err:
                    print("[AIEngine] Quota exceeded, waiting 15s...")
                    time.sleep(15)

                else:
                    # خطأ غير معروف — لا فائدة من الانتظار
                    raise

        raise Exception(
            f"All {len(self._MODELS)} models failed.\nLast error: {last_error}")

    def _require_document(self) -> None:
        """يرفع خطأ واضح لو حاول أحد استخدام الـ engine بدون وثيقة."""
        if not self._doc_text:
            raise RuntimeError(
                "No document loaded. Call load_document() first.")

    def _trim_history(self) -> None:
        """يحافظ على تاريخ المحادثة في حدود معقولة."""
        max_messages = self._MAX_HISTORY * 2   # user + assistant
        if len(self._history) > max_messages:
            # نحذف الرسائل القديمة ونبقي الأحدث
            self._history = self._history[-max_messages:]