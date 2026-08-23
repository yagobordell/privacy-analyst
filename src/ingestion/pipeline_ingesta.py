from pathlib import Path
import json

from src.ingestion.parser import procesar_pdf
from src.ingestion.chunker import crear_chunks_de_documento
from src.vectorstore.indexer import indexar_chunks_de_lista


def procesar_e_indexar_pdf(ruta_pdf: str, coleccion) -> int:
    """Pipeline completo para un único PDF recién subido:
    extracción -> chunking -> indexación. Devuelve el nº de chunks indexados."""

    # 1. Extracción de texto (con detección automática de OCR)
    resultado_extraccion = procesar_pdf(ruta_pdf)

    # Guardamos temporalmente el JSON extraído, porque crear_chunks_de_documento
    # espera leer de un archivo (reutilizamos la función de la Fase 3 tal cual)
    carpeta_temp = Path("data/procesados")
    carpeta_temp.mkdir(exist_ok=True)
    ruta_json_temp = carpeta_temp / f"{Path(ruta_pdf).stem}.json"
    with open(ruta_json_temp, "w", encoding="utf-8") as f:
        json.dump(resultado_extraccion, f, ensure_ascii=False, indent=2)

    # 2. Chunking
    chunks = crear_chunks_de_documento(str(ruta_json_temp))

    # 3. Indexación en ChromaDB
    indexar_chunks_de_lista(chunks, coleccion)

    return len(chunks)
