from pathlib import Path
import json

from src.ingestion.parser import process_pdf
from src.ingestion.chunker import create_chunks_from_document
from src.vectorstore.indexer import index_chunks_from_list


def process_and_index_pdf(pdf_path: str, collection) -> int:
    """Full pipeline for a single newly uploaded PDF:
    extraction -> chunking -> indexing. Returns the number of chunks indexed."""

    # 1. Text extraction (with automatic OCR detection)
    extraction_result = process_pdf(pdf_path)

    # Temporarily save the extracted JSON, since create_chunks_from_document
    # expects to read from a file (reusing the existing chunking function as-is)
    temp_folder = Path("data/processed")
    temp_folder.mkdir(exist_ok=True)
    temp_json_path = temp_folder / f"{Path(pdf_path).stem}.json"
    with open(temp_json_path, "w", encoding="utf-8") as f:
        json.dump(extraction_result, f, ensure_ascii=False, indent=2)

    # 2. Chunking
    chunks = create_chunks_from_document(str(temp_json_path))

    # 3. Indexing into ChromaDB
    index_chunks_from_list(chunks, collection)

    return len(chunks)
