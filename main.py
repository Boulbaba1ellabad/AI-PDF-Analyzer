import os
import google.generativeai as genai
from dotenv import load_dotenv
import pdfplumber
import pandas as pd

# تحميل الإعدادات
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def get_available_model():
    """البحث عن نموذج متاح لتجنب خطأ 404"""
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            return m.name
    return None


def process_document(path):
    text = ""
    tables = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
            table = page.extract_table()
            if table:
                tables.append(pd.DataFrame(table[1:], columns=table[0]))
    return text, tables


# --- التنفيذ المطور ---
file_name = "test.pdf"

if os.path.exists(file_name):
    print(f"🔍 جاري محاولة قراءة: {file_name}...")
    full_text, all_tables = process_document(file_name)

    # التحقق من وجود نص
    if not full_text.strip():
        print("❌ فشل استخراج النص! قد يكون الملف عبارة عن صور فقط أو محمي.")
    else:
        print(f"✅ تم استخراج {len(full_text)} حرف بنجاح.")

        model_name = get_available_model()
        if model_name:
            print(f"🤖 جاري التحليل باستخدام {model_name}...")
            model = genai.GenerativeModel(model_name)

            # إرسال النص مع التأكد من دمج البرومبت بشكل صحيح
            prompt = f"حلل النص التالي بدقة ولخص أهم النقاط:\n\n{full_text}"
            response = model.generate_content(prompt)

            # حفظ في ملف لضمان قراءة العربية بوضوح
            with open("summary.txt", "w", encoding="utf-8") as f:
                f.write(response.text)

            print("✨ مبروك! افتح ملف summary.txt لتجد التلخيص.")
else:
    print(f"⚠️ لم أجد ملف {file_name}")
