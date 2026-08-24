import json
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter


def create_chunks_from_document(json_path: str, chunk_size: int = 1200, chunk_overlap: int = 150) -> list[dict]:
    """Reads a processed JSON (output of parser.py) and splits it into chunks with metadata."""
    with open(json_path, "r", encoding="utf-8") as f:
        document = json.load(f)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for page in document["pages"]:
        text_fragments = splitter.split_text(page["text"])
        for i, fragment in enumerate(text_fragments):
            chunks.append({
                "id": f"{document['file']}_p{page['page']}_c{i}",
                "text": fragment,
                "source_document": document["file"],
                "page": page["page"],
            })

    return chunks


if __name__ == "__main__":
    processed_folder = Path("data/processed")
    output_folder = Path("data/chunks")
    output_folder.mkdir(exist_ok=True)

    json_files = list(processed_folder.glob("*.json"))
    if not json_files:
        print("No processed documents found. Run parser.py first.")

    for json_path in json_files:
        chunks = create_chunks_from_document(str(json_path))
        output_path = output_folder / json_path.name
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print(f"[{json_path.stem}] {len(chunks)} chunks generated -> {output_path}")
