# =============================================================
#  core/ai_engine.py
# =============================================================

import os
import time
from dataclasses import dataclass
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


@dataclass
class ChatMessage:
    role:      str
    content:   str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            from datetime import datetime
            self.timestamp = datetime.now().strftime("%H:%M")


class AIEngine:

    _MODELS      = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    _MAX_HISTORY = 10

    def __init__(self):
        if not os.getenv("GEMINI_API_KEY"):
            raise EnvironmentError("GEMINI_API_KEY not found in .env file.")
        self._doc_text: str = ""
        self._history: list[ChatMessage] = []

    def load_document(self, text: str) -> None:
        self._doc_text = text
        self._history.clear()

    def summarize(self) -> str:
        self._require_document()
        prompt = f"""أنت محلل وثائق محترف. قم بتحليل النص التالي وأعطني:

1. **ملخص تنفيذي** (فقرة واحدة)
2. **أهم النقاط** (5 نقاط كحد أقصى)
3. **الكلمات المفتاحية** (5-8 كلمات)

النص:
{self._doc_text[:8000]}
"""
        response = self._call_with_retry(prompt)
        self._history.append(ChatMessage(role="assistant", content=response))
        return response

    def chat(self, user_message: str) -> str:
        self._require_document()
        self._history.append(ChatMessage(role="user", content=user_message))
        prompt   = self._build_chat_prompt(user_message)
        response = self._call_with_retry(prompt)
        self._history.append(ChatMessage(role="assistant", content=response))
        self._trim_history()
        return response

    def clear_chat(self) -> None:
        self._history.clear()

    @property
    def history(self) -> list[ChatMessage]:
        return list(self._history)

    @property
    def has_document(self) -> bool:
        return bool(self._doc_text)

    def _build_chat_prompt(self, user_message: str) -> str:
        recent = self._history[:-1][-self._MAX_HISTORY:]
        history_text = "".join(
            f"{'المستخدم' if m.role == 'user' else 'المساعد'}: {m.content}\n\n"
            for m in recent
        )
        return f"""أنت مساعد ذكي متخصص في تحليل الوثائق.
لديك الوثيقة التالية:

--- بداية الوثيقة ---
{self._doc_text[:6000]}
--- نهاية الوثيقة ---

{f"سياق المحادثة السابقة:{chr(10)}{history_text}" if history_text else ""}

سؤال المستخدم: {user_message}

أجب بدقة بناءً على محتوى الوثيقة فقط.
إذا لم تجد الإجابة في الوثيقة، قل ذلك بوضوح.
"""

    def _call_with_retry(self, prompt: str) -> str:
        last_error = None
        for attempt in range(4):
            model_name = self._MODELS[min(attempt, len(self._MODELS) - 1)]
            try:
                model    = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                last_error = e
                err = str(e)
                if "503" in err or "UNAVAILABLE" in err:
                    wait = 8 * (attempt + 1)
                    print(f"[AIEngine] Server busy, retrying in {wait}s")
                    time.sleep(wait)
                elif "429" in err or "EXHAUSTED" in err:
                    print("[AIEngine] Quota exceeded, waiting 15s")
                    time.sleep(15)
                else:
                    raise
        raise Exception(f"All models failed.\nLast error: {last_error}")

    def _require_document(self) -> None:
        if not self._doc_text:
            raise RuntimeError("No document loaded. Call load_document() first.")

    def _trim_history(self) -> None:
        max_msgs = self._MAX_HISTORY * 2
        if len(self._history) > max_msgs:
            self._history = self._history[-max_msgs:]