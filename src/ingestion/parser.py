import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path
import json


def extract_native_text(pdf_path: str) -> list[dict]:
    """Attempts to extract text directly from the PDF (fast, accurate path)."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            pages.append({"page": i + 1, "text": text})
    return pages


def extract_text_ocr(pdf_path: str, language: str = "spa") -> list[dict]:
    """Fallback: converts each page to an image and applies OCR."""
    images = convert_from_path(pdf_path)
    pages = []
    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image, lang=language)
        pages.append({"page": i + 1, "text": text})
    return pages


def process_pdf(pdf_path: str, char_threshold: int = 20) -> dict:
    """
    Extracts text from a PDF, automatically detecting whether OCR is needed.
    char_threshold: if a native page has fewer characters than this,
    it's considered "empty" and reprocessed with OCR.
    """
    file_name = Path(pdf_path).name
    pages = extract_native_text(pdf_path)

    total_chars = sum(len(p["text"].strip()) for p in pages)
    avg_chars_per_page = total_chars / max(len(pages), 1)

    method_used = "native"
    if avg_chars_per_page < char_threshold:
        print(f"[{file_name}] Low text detected ({avg_chars_per_page:.0f} chars/page) -> applying OCR")
        pages = extract_text_ocr(pdf_path)
        method_used = "ocr"

    return {
        "file": file_name,
        "method": method_used,
        "num_pages": len(pages),
        "pages": pages,
    }


if __name__ == "__main__":
    data_folder = Path("data")
    output_folder = Path("data/processed")
    output_folder.mkdir(exist_ok=True)

    pdfs = list(data_folder.glob("*.pdf"))
    if not pdfs:
        print("No PDFs found in data/. Add one before continuing.")

    for pdf_path in pdfs:
        result = process_pdf(str(pdf_path))
        output_path = output_folder / f"{pdf_path.stem}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[{result['file']}] processed with method '{result['method']}' -> {output_path}")
