import unicodedata
import chromadb
import ollama
from sentence_transformers import CrossEncoder


PROMPT_TEMPLATE = """You are an assistant that answers questions based EXCLUSIVELY on the provided context.

Strict rules:
- Each context fragment is labeled with [Source: file_name, page X]. That file name identifies which document the fragment comes from, even if that word doesn't appear within the text itself.
- If multiple documents in the context contain relevant but different data (e.g. several payslips with different amounts), do not pick one arbitrarily: mention the data from EACH document separately, citing its source.
- If the answer is not in the context, explicitly say "I cannot find that information in the provided documents." Do not make up data.
- Always cite the document and page you took each piece of data from, using the format (Source: file_name, page X).
- Do not use external information or general knowledge, only what appears in the context.

Context:
{context}

Question: {question}

Answer:"""


_reranker = None

def get_reranker() -> CrossEncoder:
    """Loads the reranking model once (lazy loading)."""
    global _reranker
    if _reranker is None:
        print("Loading reranking model (first time only)...")
        _reranker = CrossEncoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    return _reranker


def remove_accents(text: str) -> str:
    """Normalizes text by removing accents/diacritics, for robust comparisons."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def detect_mentioned_document(question: str, collection) -> str | None:
    """Checks whether the question mentions a keyword unique to a known document's name.
    Words shared across multiple document names are treated as generic and ignored."""
    metadatas = collection.get()["metadatas"]
    available_documents = sorted(set(m["source_document"] for m in metadatas))

    # Build word -> set of documents that contain that word in their name
    word_to_docs: dict[str, set[str]] = {}
    for doc in available_documents:
        base_name = remove_accents(doc.replace(".pdf", "").replace("_", " ").lower())
        for word in base_name.split():
            word_to_docs.setdefault(word, set()).add(doc)

    normalized_question = remove_accents(question.lower())

    for doc in available_documents:
        base_name = remove_accents(doc.replace(".pdf", "").replace("_", " ").lower())
        unique_keywords = [w for w in base_name.split() if len(word_to_docs[w]) == 1]
        if any(keyword in normalized_question for keyword in unique_keywords):
            return doc
    return None


def retrieve_context(question: str, collection, embedding_model: str = "bge-m3", n_results: int = 10, document_filter: str | None = None) -> list[dict]:
    """Generates the question's embedding and retrieves the most relevant chunks."""
    question_embedding = ollama.embeddings(model=embedding_model, prompt=question)["embedding"]

    kwargs = {"query_embeddings": [question_embedding], "n_results": n_results}
    if document_filter:
        kwargs["where"] = {"source_document": document_filter}

    results = collection.query(**kwargs)

    retrieved_chunks = []
    for doc, meta, distance in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        retrieved_chunks.append({
            "text": doc,
            "document": meta["source_document"],
            "page": meta["page"],
            "distance": distance,
        })
    return retrieved_chunks


def rerank_chunks(question: str, chunks: list[dict], top_n: int = 4) -> list[dict]:
    """Reorders retrieved chunks using a cross-encoder, more precise than
    embedding similarity for filtering out semantic false positives."""
    if not chunks:
        return chunks

    reranker = get_reranker()
    pairs = [(question, chunk["text"]) for chunk in chunks]
    scores = reranker.predict(pairs)

    scored_chunks = list(zip(chunks, scores))
    sorted_chunks = sorted(scored_chunks, key=lambda x: x[1], reverse=True)

    result = []
    for chunk, score in sorted_chunks[:top_n]:
        chunk_with_score = dict(chunk)
        chunk_with_score["reranker_score"] = float(score)
        result.append(chunk_with_score)

    return result


def build_context(chunks: list[dict]) -> str:
    """Formats retrieved chunks as text to insert into the prompt."""
    blocks = []
    for chunk in chunks:
        blocks.append(f"[Source: {chunk['document']}, page {chunk['page']}]\n{chunk['text']}")
    return "\n\n---\n\n".join(blocks)


def generate_answer(question: str, context: str, llm_model: str = "llama3.1:8b") -> str:
    """Calls the LLM with the already-built prompt."""
    final_prompt = PROMPT_TEMPLATE.format(context=context, question=question)

    response = ollama.generate(
        model=llm_model,
        prompt=final_prompt,
        stream=False,
        options={"temperature": 0.1},
    )
    return response["response"]


def answer_question(question: str, collection, n_candidates: int = 10, n_final: int = 4) -> dict:
    """Full pipeline: broad retrieval + reranking + generation."""
    document_filter = detect_mentioned_document(question, collection)

    candidate_chunks = retrieve_context(question, collection, n_results=n_candidates, document_filter=document_filter)
    final_chunks = rerank_chunks(question, candidate_chunks, top_n=n_final)

    context = build_context(final_chunks)
    answer = generate_answer(question, context)

    return {
        "question": question,
        "answer": answer,
        "filter_applied": document_filter,
        "sources": [{"document": c["document"], "page": c["page"],
                     "distance": c["distance"], "reranker_score": c.get("reranker_score")}
                    for c in final_chunks],
    }


if __name__ == "__main__":
    client = chromadb.PersistentClient(path="data/chroma_db")
    collection = client.get_collection("private_documents")

    test_questions = [
        "How much IRPF is deducted in the standard payslip?",
        "What part of my salary goes to the tax authority?",
        "What is the duration of the employment contract?",
        "How much does a plane ticket to Tokyo cost?",  # question with no answer in the documents
    ]

    for question in test_questions:
        result = answer_question(question, collection)
        print(f"\n{'='*60}")
        print(f"QUESTION: {result['question']}")
        print(f"{'='*60}")
        print(f"ANSWER:\n{result['answer']}")
        print(f"\nSources used:")
        for source in result["sources"]:
            print(f"  - {source['document']} (page {source['page']}, distance {source['distance']:.3f}, reranker_score: {source['reranker_score']:.3f})")
