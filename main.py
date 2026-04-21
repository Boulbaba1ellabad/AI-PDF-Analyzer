import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
import google.generativeai as genai
from dotenv import load_dotenv
import pdfplumber
import pandas as pd
import arabic_reshaper
from bidi.algorithm import get_display

# 1. إعدادات البيئة والذكاء الاصطناعي
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


class DocumentAIApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # إعدادات النافذة
        self.title("AI Document Intelligence Pro v1.0")
        self.geometry("700x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # واجهة المستخدم (UI Elements)
        self.label = ctk.CTkLabel(
            self, text="AI Document Analyzer", font=("Helvetica", 24, "bold"))
        self.label.pack(pady=20)

        self.btn_select = ctk.CTkButton(
            self, text="Select PDF File", command=self.select_file, height=40, font=("Helvetica", 14, "bold"))
        self.btn_select.pack(pady=10)

        self.status_label = ctk.CTkLabel(
            self, text="Status: Ready", text_color="gray")
        self.status_label.pack(pady=5)

        self.output_text = ctk.CTkTextbox(
            self, width=600, height=300, font=("Helvetica", 15))
        self.output_text.pack(pady=15)

        self.btn_save = ctk.CTkButton(
            self, text="Save Summary to File", command=self.save_to_file, state="disabled")
        self.btn_save.pack(pady=10)

        self.last_summary = ""

    def select_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.process_document(file_path)

    def process_document(self, path):
        try:
            self.status_label.configure(
                text="🔄 Reading PDF & Extracting Data...", text_color="yellow")
            self.update()

            text = ""
            tables = []

            # استخراج النصوص والجداول
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
                    tbl = page.extract_table()
                    if tbl:
                        tables.append(pd.DataFrame(tbl[1:], columns=tbl[0]))

            # حفظ الجداول في اكسل إذا وجدت
            if tables:
                excel_name = "extracted_data.xlsx"
                with pd.ExcelWriter(excel_name) as writer:
                    for i, df in enumerate(tables):
                        df.to_excel(
                            writer, sheet_name=f"Table_{i+1}", index=False)
                print(f"✅ Tables saved to {excel_name}")

            # التحليل عبر الذكاء الاصطناعي
            if text.strip():
                self.status_label.configure(
                    text="🤖 AI is analyzing content...", text_color="cyan")
                self.update()

                # اختيار أفضل نموذج متاح تلقائياً لتجنب خطأ 404
                try:
                    available_models = [m.name for m in genai.list_models(
                    ) if 'generateContent' in m.supported_generation_methods]
                    selected_model = available_models[0] if available_models else "models/gemini-pro"
                    model = genai.GenerativeModel(selected_model)

                    # البرومبت الاحترافي
                    professional_prompt = f"قم بتلخيص هذا المستند بدقة كخبير محلل بيانات وبنقاط احترافية واضحة:\n\n{text[:10000]}"
                    response = model.generate_content(professional_prompt)

                    self.last_summary = response.text

                    # معالجة اللغة العربية للعرض بشكل صحيح
                    reshaped_text = arabic_reshaper.reshape(self.last_summary)
                    bidi_text = get_display(reshaped_text)

                    self.output_text.delete("1.0", "end")
                    self.output_text.insert("1.0", bidi_text)

                    self.status_label.configure(
                        text=f"✅ Analysis Complete", text_color="green")
                    self.btn_save.configure(state="normal")

                except Exception as ai_error:
                    if "429" in str(ai_error):
                        messagebox.showwarning(
                            "Quota Limit", "تجاوزت حد الطلبات المسموح به. انتظر دقيقة ثم حاول مجدداً.")
                        self.status_label.configure(
                            text="⚠️ Quota Exceeded - Wait 1 min", text_color="orange")
                    else:
                        messagebox.showerror(
                            "AI Error", f"خطأ في الذكاء الاصطناعي: {str(ai_error)}")
                        self.status_label.configure(
                            text="❌ AI Error", text_color="red")
            else:
                messagebox.showwarning(
                    "Warning", "لم يتم العثور على نص داخل ملف الـ PDF.")
                self.status_label.configure(
                    text="⚠️ No Text Found", text_color="orange")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self.status_label.configure(text="❌ Error", text_color="red")

    def save_to_file(self):
        if self.last_summary:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")],
                initialfile="ai_summary.txt"
            )
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.last_summary)
                messagebox.showinfo("Saved", "تم حفظ التلخيص بنجاح!")


if __name__ == "__main__":
    app = DocumentAIApp()
    app.mainloop()
