import json
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter


def crear_chunks_de_documento(ruta_json: str, tamano_chunk: int = 600, solapamiento: int = 100) -> list[dict]:
    """Lee un JSON procesado (salida de parser.py) y lo trocea en chunks con metadata."""
    with open(ruta_json, "r", encoding="utf-8") as f:
        documento = json.load(f)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=tamano_chunk,
        chunk_overlap=solapamiento,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for pagina in documento["paginas"]:
        fragmentos_texto = splitter.split_text(pagina["texto"])
        for i, fragmento in enumerate(fragmentos_texto):
            chunks.append({
                "id": f"{documento['archivo']}_p{pagina['pagina']}_c{i}",
                "texto": fragmento,
                "documento_origen": documento["archivo"],
                "pagina": pagina["pagina"],
            })

    return chunks


if __name__ == "__main__":
    carpeta_procesados = Path("data/procesados")
    carpeta_salida = Path("data/chunks")
    carpeta_salida.mkdir(exist_ok=True)

    jsons = list(carpeta_procesados.glob("*.json"))
    if not jsons:
        print("No hay documentos procesados. Ejecuta primero parser.py")

    for ruta_json in jsons:
        chunks = crear_chunks_de_documento(str(ruta_json))
        salida = carpeta_salida / ruta_json.name
        with open(salida, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print(f"[{ruta_json.stem}] {len(chunks)} chunks generados → {salida}")
