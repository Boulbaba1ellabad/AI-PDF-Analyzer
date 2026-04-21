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


# --- التنفيذ ---
file_name = "test.pdf"  # تأكد من وضع ملف بهذا الاسم في المجلد

if os.path.exists(file_name):
    print(f"🔄 جاري معالجة المستند...")
    full_text, all_tables = process_document(file_name)

    # حفظ الجداول في Excel
    if all_tables:
        with pd.ExcelWriter("output_tables.xlsx") as writer:
            for i, df in enumerate(all_tables):
                df.to_excel(writer, sheet_name=f"Table_{i+1}", index=False)
        print("✅ تم استخراج الجداول إلى output_tables.xlsx")

    # تحليل النص بـ Gemini
    model_name = get_available_model()
    if model_name:
        print(f"🤖 جاري التحليل باستخدام {model_name}...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            f"لخص أهم 5 معلومات في هذا النص:\n\n{full_text[:8000]}")
        print("\n--- ملخص المستند ---")
        print(response.text)
else:
    print(f"⚠️ يرجى وضع ملف باسم {file_name} في المجلد.")
