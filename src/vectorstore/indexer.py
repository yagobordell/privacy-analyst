import json
from pathlib import Path
import chromadb
import ollama


def generate_embedding(text: str, model: str = "bge-m3") -> list[float]:
    """Generates the embedding vector for a text using Ollama."""
    response = ollama.embeddings(model=model, prompt=text)
    return response["embedding"]


def index_chunks_from_list(chunks: list[dict], collection) -> None:
    """Generates embeddings and indexes a list of chunks already in memory (no disk round-trip)."""
    for chunk in chunks:
        embedding = generate_embedding(chunk["text"])
        collection.upsert(
            ids=[chunk["id"]],
            embeddings=[embedding],
            documents=[chunk["text"]],
            metadatas=[{
                "source_document": chunk["source_document"],
                "page": chunk["page"],
            }],
        )


def index_chunks(chunks_folder: str = "data/chunks", collection_name: str = "private_documents"):
    """Reads all chunks generated in the chunking step, generates their embeddings
    and stores them in a persistent ChromaDB collection."""

    client = chromadb.PersistentClient(path="data/chroma_db")

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    chunk_files = list(Path(chunks_folder).glob("*.json"))
    if not chunk_files:
        print("No chunks available. Run chunker.py first.")
        return

    total_indexed = 0
    for file_path in chunk_files:
        with open(file_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        index_chunks_from_list(chunks, collection)
        total_indexed += len(chunks)
        print(f"[{file_path.stem}] {len(chunks)} chunks indexed")

    print(f"\nTotal: {total_indexed} chunks indexed in collection '{collection_name}'")


if __name__ == "__main__":
    index_chunks()
