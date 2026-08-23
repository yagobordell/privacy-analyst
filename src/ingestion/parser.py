import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path
import json


def extraer_texto_nativo(ruta_pdf: str) -> list[dict]:
    """Intenta extraer texto directamente del PDF (caso rápido y preciso)."""
    paginas = []
    with pdfplumber.open(ruta_pdf) as pdf:
        for i, pagina in enumerate(pdf.pages):
            texto = pagina.extract_text() or ""
            paginas.append({"pagina": i + 1, "texto": texto})
    return paginas


def extraer_texto_ocr(ruta_pdf: str, idioma: str = "spa") -> list[dict]:
    """Fallback: convierte cada página a imagen y aplica OCR."""
    imagenes = convert_from_path(ruta_pdf)
    paginas = []
    for i, imagen in enumerate(imagenes):
        texto = pytesseract.image_to_string(imagen, lang=idioma)
        paginas.append({"pagina": i + 1, "texto": texto})
    return paginas


def procesar_pdf(ruta_pdf: str, umbral_caracteres: int = 20) -> dict:
    """
    Extrae el texto de un PDF, detectando automáticamente si necesita OCR.
    umbral_caracteres: si una página nativa tiene menos texto que esto,
    se considera "vacía" y se re-procesa con OCR.
    """
    nombre_archivo = Path(ruta_pdf).name
    paginas = extraer_texto_nativo(ruta_pdf)

    texto_total = sum(len(p["texto"].strip()) for p in paginas)
    promedio_por_pagina = texto_total / max(len(paginas), 1)

    metodo_usado = "nativo"
    if promedio_por_pagina < umbral_caracteres:
        print(f"[{nombre_archivo}] Poco texto detectado ({promedio_por_pagina:.0f} car/pág) → aplicando OCR")
        paginas = extraer_texto_ocr(ruta_pdf)
        metodo_usado = "ocr"

    return {
        "archivo": nombre_archivo,
        "metodo": metodo_usado,
        "num_paginas": len(paginas),
        "paginas": paginas,
    }


if __name__ == "__main__":
    carpeta_datos = Path("data")
    carpeta_salida = Path("data/procesados")
    carpeta_salida.mkdir(exist_ok=True)

    pdfs = list(carpeta_datos.glob("*.pdf"))
    if not pdfs:
        print("No se encontraron PDFs en data/. Añade alguno antes de continuar.")

    for ruta_pdf in pdfs:
        resultado = procesar_pdf(str(ruta_pdf))
        salida = carpeta_salida / f"{ruta_pdf.stem}.json"
        with open(salida, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        print(f"[{resultado['archivo']}] procesado con método '{resultado['metodo']}' → {salida}")
