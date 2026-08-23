import chromadb
import unicodedata
from sentence_transformers import CrossEncoder
import ollama


_reranker = None

def obtener_reranker() -> CrossEncoder:
    """Carga el modelo de reranking una sola vez (lazy loading)."""
    global _reranker
    if _reranker is None:
        print("Cargando modelo de reranking (solo la primera vez)...")
        _reranker = CrossEncoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    return _reranker


def rerank_chunks(pregunta: str, chunks: list[dict], top_n: int = 4) -> list[dict]:
    """Reordena los chunks recuperados usando un cross-encoder, más preciso
    que la similitud de embeddings para descartar falsos positivos semánticos."""
    if not chunks:
        return chunks

    reranker = obtener_reranker()
    pares = [(pregunta, chunk["texto"]) for chunk in chunks]
    puntuaciones = reranker.predict(pares)

    chunks_con_puntuacion = list(zip(chunks, puntuaciones))
    chunks_ordenados = sorted(chunks_con_puntuacion, key=lambda x: x[1], reverse=True)

    # Añadimos la puntuación del reranker a cada chunk, útil para depurar
    resultado = []
    for chunk, puntuacion in chunks_ordenados[:top_n]:
        chunk_con_score = dict(chunk)
        chunk_con_score["score_reranker"] = float(puntuacion)
        resultado.append(chunk_con_score)

    return resultado


PLANTILLA_PROMPT = """Eres un asistente que responde preguntas basándote ÚNICAMENTE en el contexto proporcionado.

Reglas estrictas:
- Cada fragmento de contexto está etiquetado con [Fuente: nombre_archivo, página X]. Ese nombre de archivo identifica de qué documento proviene el fragmento, aunque esa palabra no aparezca dentro del propio texto.
- Si varios documentos del contexto contienen datos relevantes pero distintos entre sí (por ejemplo, varias nóminas con importes diferentes), no elijas uno arbitrariamente: menciona el dato de CADA documento por separado, indicando su fuente.
- Si la respuesta no está en el contexto, di explícitamente "No encuentro esa información en los documentos proporcionados". No inventes datos.
- Cita siempre el documento y la página de donde sacas cada dato, usando el formato (Fuente: nombre_archivo, página X).
- No uses información externa ni conocimiento general, solo lo que aparece en el contexto.

Contexto:
{contexto}

Pregunta: {pregunta}

Respuesta:"""


def recuperar_contexto(pregunta: str, coleccion, modelo_embeddings: str = "bge-m3", n_resultados: int = 6, filtro_documento: str | None = None, umbral_distancia: float = 0.58) -> list[dict]:
    """Genera el embedding de la pregunta y recupera los chunks más relevantes.
    Descarta chunks por encima de umbral_distancia (poco relevantes = ruido)."""
    embedding_pregunta = ollama.embeddings(model=modelo_embeddings, prompt=pregunta)["embedding"]

    kwargs = {"query_embeddings": [embedding_pregunta], "n_results": n_resultados}
    if filtro_documento:
        kwargs["where"] = {"documento_origen": filtro_documento}

    resultados = coleccion.query(**kwargs)

    chunks_recuperados = []
    for doc, meta, distancia in zip(resultados["documents"][0], resultados["metadatas"][0], resultados["distances"][0]):
        if distancia <= umbral_distancia:
            chunks_recuperados.append({
                "texto": doc,
                "documento": meta["documento_origen"],
                "pagina": meta["pagina"],
                "distancia": distancia,
            })
    return chunks_recuperados


def construir_contexto(chunks: list[dict]) -> str:
    """Formatea los chunks recuperados como texto para insertar en el prompt."""
    bloques = []
    for chunk in chunks:
        bloques.append(f"[Fuente: {chunk['documento']}, página {chunk['pagina']}]\n{chunk['texto']}")
    return "\n\n---\n\n".join(bloques)


def generar_respuesta(pregunta: str, contexto: str, modelo_llm: str = "llama3.1:8b") -> str:
    """Llama al LLM con el prompt ya construido."""
    prompt_final = PLANTILLA_PROMPT.format(contexto=contexto, pregunta=pregunta)

    respuesta = ollama.generate(
        model=modelo_llm,
        prompt=prompt_final,
        stream=False,
        options={"temperature": 0.1},
    )
    return respuesta["response"]


def quitar_tildes(texto: str) -> str:
    """Normaliza el texto quitando tildes/diacríticos, para comparaciones robustas."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def detectar_documento_mencionado(pregunta: str, coleccion) -> str | None:
    """Comprueba si la pregunta menciona palabras clave del nombre de un documento conocido."""
    metadatas = coleccion.get()["metadatas"]
    documentos_disponibles = set(m["documento_origen"] for m in metadatas)

    pregunta_normalizada = quitar_tildes(pregunta.lower())

    for doc in documentos_disponibles:
        nombre_base = doc.replace(".pdf", "").replace("_", " ").lower()
        palabras_clave = quitar_tildes(nombre_base).split()
        palabras_clave = [p for p in palabras_clave if p not in ("nomina", "contrato")]
        if any(palabra in pregunta_normalizada for palabra in palabras_clave):
            return doc
    return None


def responder_pregunta(pregunta: str, coleccion, n_candidatos: int = 10, n_finales: int = 4) -> dict:
    """Pipeline completo: recuperación amplia + reranking + generación."""
    filtro = detectar_documento_mencionado(pregunta, coleccion)

    # Recuperación inicial amplia (candidatos)
    chunks_candidatos = recuperar_contexto(pregunta, coleccion, n_resultados=n_candidatos, filtro_documento=filtro)

    # Reranking: nos quedamos con los top_n más relevantes de verdad
    chunks_finales = rerank_chunks(pregunta, chunks_candidatos, top_n=n_finales)

    contexto = construir_contexto(chunks_finales)
    respuesta = generar_respuesta(pregunta, contexto)

    return {
        "pregunta": pregunta,
        "respuesta": respuesta,
        "filtro_aplicado": filtro,
        "fuentes": [{"documento": c["documento"], "pagina": c["pagina"],
                     "distancia": c["distancia"], "score_reranker": c.get("score_reranker")}
                    for c in chunks_finales],
    }


if __name__ == "__main__":
    cliente = chromadb.PersistentClient(path="data/chroma_db")
    coleccion = cliente.get_collection("documentos_privados")

    preguntas_prueba = [
        "¿Cuánto se descuenta de IRPF en la nómina estándar?",
        "¿Qué parte de mi sueldo se va a Hacienda?",
        "¿Cuál es la duración del contrato de trabajo?",
        "¿Cuánto cuesta un billete de avión a Tokio?",  # pregunta sin respuesta en los documentos
    ]

    for pregunta in preguntas_prueba:
        resultado = responder_pregunta(pregunta, coleccion)
        print(f"\n{'='*60}")
        print(f"PREGUNTA: {resultado['pregunta']}")
        print(f"{'='*60}")
        print(f"RESPUESTA:\n{resultado['respuesta']}")
        print(f"\nFuentes usadas:")
        for fuente in resultado["fuentes"]:
	        print(f"  - {fuente['documento']} (pág {fuente['pagina']}, distancia {fuente['distancia']:.3f}, score_reranker: {fuente['score_reranker']:.3f})")
