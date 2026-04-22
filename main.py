import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image
import pdfplumber
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from arabic_reshaper import reshape
from bidi.algorithm import get_display

# تحميل الإعدادات
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# إعداد المظهر
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AIAnalyzerPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Document Intelligence Pro")
        self.geometry("1100x750")

        # تقسيم الشاشة (Sidebar & Main)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- القائمة الجانبية (Sidebar) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="AI ANALYZER",
                                       font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 40))

        self.select_btn = ctk.CTkButton(self.sidebar_frame, text="Select PDF File",
                                        command=self.select_file, height=40, font=("Segoe UI", 13, "bold"))
        self.select_btn.grid(row=1, column=0, padx=20, pady=10)

        self.save_btn = ctk.CTkButton(self.sidebar_frame, text="Save Summary",
                                      command=self.save_summary, state="disabled",
                                      fg_color="transparent", border_width=2)
        self.save_btn.grid(row=2, column=0, padx=20, pady=10)

        self.appearance_mode_label = ctk.CTkLabel(
            self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Dark", "Light"],
                                                             command=self.change_appearance_mode)
        self.appearance_mode_optionemenu.grid(
            row=6, column=0, padx=20, pady=(10, 20))

        # --- المنطقة الأساسية (Main) ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=30, pady=30, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        self.title_label = ctk.CTkLabel(self.main_frame, text="Document Analysis Dashboard",
                                        font=ctk.CTkFont(size=22, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w", pady=(0, 20))

        # شريط التقدم
        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        self.progress_bar.set(0)

        # منطقة عرض النص
        self.result_text = ctk.CTkTextbox(self.main_frame, font=("Segoe UI", 15),
                                          spacing3=12, corner_radius=15, border_width=1)
        self.result_text.grid(row=2, column=0, sticky="nsew")

        self.current_file = None

    def fix_arabic(self, text):
        reshaped_text = reshape(text)
        return get_display(reshaped_text)

    def change_appearance_mode(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def select_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.current_file = file_path
            self.process_document()

    def process_document(self):
        self.progress_bar.set(0.3)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", self.fix_arabic(
            "جاري تحليل الملف... يرجى الانتظار"))
        self.update()

        try:
            # 1. استخراج الجداول
            tables_data = []
            with pdfplumber.open(self.current_file) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        tables_data.extend(table)

            if tables_data:
                df = pd.DataFrame(tables_data[1:], columns=tables_data[0])
                df.to_excel("extracted_data.xlsx", index=False)

            self.progress_bar.set(0.6)

            # 2. تحليل AI
            model = genai.GenerativeModel('gemini-2.5-flash')
            # (نفس منطق استخراج النص السابق يوضع هنا)
            text_content = ""
            with pdfplumber.open(self.current_file) as pdf:
                text_content = " ".join([p.extract_text()
                                        for p in pdf.pages if p.extract_text()])

            response = model.generate_content(
                f"قم بتلخيص هذا النص بشكل احترافي مع نقاط واضحة: {text_content}")

            self.progress_bar.set(1.0)
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert("1.0", self.fix_arabic(response.text))
            self.save_btn.configure(state="normal")

        except Exception as e:
            self.progress_bar.set(0)
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def save_summary(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.result_text.get("1.0", tk.END))
            messagebox.showinfo("Success", "Summary saved successfully!")


if __name__ == "__main__":
    app = AIAnalyzerPro()
    app.mainloop()
