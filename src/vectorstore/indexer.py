import json
from pathlib import Path
import chromadb
import ollama


def generar_embedding(texto: str, modelo: str = "bge-m3") -> list[float]:
    """Genera el vector de embedding de un texto usando Ollama."""
    respuesta = ollama.embeddings(model=modelo, prompt=texto)
    return respuesta["embedding"]

def indexar_chunks(carpeta_chunks: str = "data/chunks", nombre_coleccion: str = "documentos_privados"):
    """Lee todos los chunks generados en la Fase 3, genera sus embeddings
    y los guarda en una colección persistente de ChromaDB."""

    cliente = chromadb.PersistentClient(path="data/chroma_db")

    coleccion = cliente.get_or_create_collection(
    name=nombre_coleccion,
    metadata={"hnsw:space": "cosine"},)

    archivos_chunks = list(Path(carpeta_chunks).glob("*.json"))
    if not archivos_chunks:
        print("No hay chunks disponibles. Ejecuta primero chunker.py")
        return

    total_indexados = 0
    for ruta_archivo in archivos_chunks:
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        for chunk in chunks:
            embedding = generar_embedding(chunk["texto"])

            coleccion.upsert(
                ids=[chunk["id"]],
                embeddings=[embedding],
                documents=[chunk["texto"]],
                metadatas=[{
                    "documento_origen": chunk["documento_origen"],
                    "pagina": chunk["pagina"],
                }],
            )
            total_indexados += 1

        print(f"[{ruta_archivo.stem}] {len(chunks)} chunks indexados")

    print(f"\nTotal: {total_indexados} chunks indexados en la colección '{nombre_coleccion}'")


if __name__ == "__main__":
    indexar_chunks()
