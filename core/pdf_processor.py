# =============================================================
#  core/pdf_processor.py
#  المسؤولية الوحيدة: استخراج كل البيانات من ملف PDF
# =============================================================

import pdfplumber
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


# -------------------------------------------------------------
#  PDFDocument  —  Data Class يحمل نتائج الاستخراج
# -------------------------------------------------------------

@dataclass
class PDFDocument:
    """
    كائن بيانات بسيط يحمل كل ما استُخرج من الـ PDF.
    dataclass تولّد __init__ و __repr__ تلقائياً.
    """
    file_path:  str
    page_count: int = 0
    word_count: int = 0
    table_count: int = 0
    full_text:  str = ""
    tables:     list = field(default_factory=list)
    # قائمة نصوص كل صفحة على حدة — مفيدة للـ Chat لاحقاً
    pages_text: list[str] = field(default_factory=list)

    @property
    def filename(self) -> str:
        """اسم الملف فقط بدون المسار الكامل."""
        import os
        return os.path.basename(self.file_path)

    @property
    def short_name(self) -> str:
        """اسم مقصور لعرضه في الـ UI (28 حرف max)."""
        name = self.filename
        return name if len(name) <= 28 else name[:25] + "…"


# -------------------------------------------------------------
#  PDFProcessor  —  الـ Class الرئيسية
# -------------------------------------------------------------

class PDFProcessor:
    """
    تستقبل مسار ملف PDF وتستخرج منه:
      - النص الكامل
      - نص كل صفحة على حدة
      - الجداول (مع حفظها كـ Excel اختيارياً)
      - إحصائيات (عدد الصفحات، الكلمات، الجداول)

    الاستخدام:
        processor = PDFProcessor()
        doc = processor.process("path/to/file.pdf")
        print(doc.full_text)
    """

    def __init__(self, excel_output: str = "extracted_data.xlsx"):
        """
        excel_output: مسار ملف Excel لحفظ الجداول فيه.
                      ضع None لو لا تريد الحفظ.
        """
        self._excel_output = excel_output

    # ── Public ────────────────────────────────────────────────

    def process(self, file_path: str) -> PDFDocument:
        """
        الدالة الرئيسية — تستدعى من الخارج.
        ترجع PDFDocument مكتملاً أو ترفع Exception.
        """
        doc = PDFDocument(file_path=file_path)

        with pdfplumber.open(file_path) as pdf:
            doc.page_count = len(pdf.pages)
            doc.pages_text, doc.tables = self._extract_pages(pdf)

        doc.full_text = " ".join(doc.pages_text)
        doc.word_count = len(doc.full_text.split())
        doc.table_count = len(doc.tables)

        if doc.tables and self._excel_output:
            self._save_tables_excel(doc.tables)

        return doc

    # ── Private ───────────────────────────────────────────────

    def _extract_pages(self, pdf) -> tuple[list[str], list]:
        """
        يمر على كل صفحة ويستخرج النص والجداول.
        يرجع (قائمة نصوص, قائمة جداول).
        """
        pages_text = []
        all_tables = []

        for page in pdf.pages:
            # ── نص الصفحة ──
            text = page.extract_text()
            if text:
                pages_text.append(text.strip())

            # ── جداول الصفحة ──
            table = page.extract_table()
            if table and len(table) > 1:   # نتجاهل الجداول الفارغة
                all_tables.append(table)

        return pages_text, all_tables

    def _save_tables_excel(self, tables: list) -> None:
        """
        يحفظ أول جدول مكتمل كـ Excel.
        يتجاهل الأخطاء بصمت لأنها ليست حرجة.
        """
        try:
            for table in tables:
                if table and table[0]:   # تأكد من وجود header
                    df = pd.DataFrame(table[1:], columns=table[0])
                    df.to_excel(self._excel_output, index=False)
                    break
        except Exception as e:
            print(f"[PDFProcessor] Excel export skipped: {e}")
