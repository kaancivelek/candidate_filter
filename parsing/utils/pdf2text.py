"""
utils/pdf2text.py

PDF'den metin çıkarır.
Önce normal text extraction dener (hızlı).
Metin boş veya çok kısaysa image-based PDF'dir → OCR fallback (pytesseract).

Gereksinimler:
    pip install pymupdf pytesseract pillow
    + sistem: tesseract-ocr
"""

import io
import os
import pytesseract

# Windows için Tesseract yolunu belirt (varsayılan kurulum dizini)
tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

# ── Text extraction (hızlı yol) ──────────────────────────────────────────────
def _extract_text_native(pdf_path: str) -> str:
    """pypdf ile standart text extraction."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )
    except Exception as e:
        print(f"[pdf2text] native extraction failed: {e}")
        return ""


# ── OCR fallback (yavaş ama evrensel) ────────────────────────────────────────
def _extract_text_ocr(pdf_path: str, dpi: int = 200, lang: str = "eng") -> str:
    """
    PyMuPDF ile sayfayı rasterize et, Tesseract ile OCR yap.
    
    dpi=200 → hız/kalite dengesi. Kalite sorununda 250-300'e çık.
    lang    → "eng" | "tur" | "eng+tur" (tesseract dil paketi kurulu olmalı)
    """
    try:
        import fitz                          # PyMuPDF
        import pytesseract
        from PIL import Image
    except ImportError as e:
        print(f"[pdf2text] OCR dependency missing: {e}")
        print("  pip install pymupdf pytesseract pillow")
        return ""

    try:
        doc = fitz.open(pdf_path)
        pages_text = []

        for page_num, page in enumerate(doc):
            pix  = page.get_pixmap(dpi=dpi)
            img  = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, lang=lang)
            pages_text.append(text)
            print(f"[pdf2text] OCR page {page_num + 1}/{len(doc)}")

        doc.close()
        return "\n".join(pages_text)

    except Exception as e:
        print(f"[pdf2text] OCR failed: {e}")
        return ""


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────
def get_Text(pdf_path: str,
             ocr_threshold: int = 50,
             ocr_lang: str = "eng") -> str:
    """
    PDF'den metin çıkarır.

    Params:
        pdf_path      : PDF dosya yolu
        ocr_threshold : Native extraction bu karakten azını döndürürse
                        OCR'a geç. (image-based PDF tespiti)
        ocr_lang      : Tesseract dil kodu. Türkçe için "tur", ikisi için "eng+tur"

    Returns:
        Düz metin string'i. Başarısızsa boş string.
    """
    print(f"[pdf2text] Reading: {pdf_path}")

    # 1. Önce normal extraction dene
    text = _extract_text_native(pdf_path)

    if len(text.strip()) >= ocr_threshold:
        print(f"[pdf2text] Native OK ({len(text)} chars)")
        return text

    # 2. Metin çok kısaysa → image-based PDF, OCR yap
    print(f"[pdf2text] Native too short ({len(text.strip())} chars) → OCR fallback")
    text = _extract_text_ocr(pdf_path, lang=ocr_lang)

    if text.strip():
        print(f"[pdf2text] OCR OK ({len(text)} chars)")
    else:
        print(f"[pdf2text] Both methods failed for: {pdf_path}")

    return text