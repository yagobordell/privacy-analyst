import sys
from pathlib import Path

# Permite importar módulos de src/ aunque Streamlit ejecute desde otra ubicación
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import chromadb

from src.ingestion.pipeline_ingesta import procesar_e_indexar_pdf
from src.rag.pipeline import responder_pregunta


st.set_page_config(page_title="Analista de Privacidad", page_icon="🔒", layout="wide")

# --- Inicialización de recursos (una sola vez por sesión) ---
@st.cache_resource
def obtener_coleccion():
    cliente = chromadb.PersistentClient(path="data/chroma_db")
    return cliente.get_or_create_collection(
        name="documentos_privados",
        metadata={"hnsw:space": "cosine"},
    )

coleccion = obtener_coleccion()

if "historial" not in st.session_state:
    st.session_state.historial = []

# --- Barra lateral: subida e indexación de documentos ---
with st.sidebar:
    st.header("📄 Documentos")
    st.caption("Todo el procesamiento ocurre en local. Ningún archivo sale de este ordenador.")

    archivo_subido = st.file_uploader("Sube un PDF", type=["pdf"])

    if archivo_subido is not None:
        if st.button("Procesar e indexar"):
            carpeta_uploads = Path("data")
            carpeta_uploads.mkdir(exist_ok=True)
            ruta_destino = carpeta_uploads / archivo_subido.name

            with open(ruta_destino, "wb") as f:
                f.write(archivo_subido.getbuffer())

            with st.spinner("Extrayendo texto, generando chunks e indexando..."):
                num_chunks = procesar_e_indexar_pdf(str(ruta_destino), coleccion)

            st.success(f"'{archivo_subido.name}' indexado correctamente ({num_chunks} fragmentos).")

    st.divider()
    st.subheader("Documentos indexados")
    metadatas = coleccion.get()["metadatas"]
    documentos_unicos = sorted(set(m["documento_origen"] for m in metadatas)) if metadatas else []
    if documentos_unicos:
        for doc in documentos_unicos:
            st.write(f"• {doc}")
    else:
        st.write("_Ningún documento indexado todavía._")

# --- Zona principal: chat ---
st.title("🔒 Analista de Privacidad")
st.caption("Chatea con tus documentos sensibles. 100% local, sin conexión a internet.")

for mensaje in st.session_state.historial:
    with st.chat_message(mensaje["rol"]):
        st.write(mensaje["contenido"])
        if mensaje["rol"] == "assistant" and mensaje.get("fuentes"):
            with st.expander("Ver fuentes"):
                for fuente in mensaje["fuentes"]:
                    st.write(f"📄 {fuente['documento']} — página {fuente['pagina']}")

pregunta_usuario = st.chat_input("Escribe tu pregunta sobre los documentos...")

if pregunta_usuario:
    st.session_state.historial.append({"rol": "user", "contenido": pregunta_usuario})
    with st.chat_message("user"):
        st.write(pregunta_usuario)

    with st.chat_message("assistant"):
        with st.spinner("Buscando en los documentos y generando respuesta..."):
            if not documentos_unicos:
                respuesta_texto = "Todavía no hay documentos indexados. Sube un PDF desde el panel lateral."
                fuentes = []
            else:
                resultado = responder_pregunta(pregunta_usuario, coleccion)
                respuesta_texto = resultado["respuesta"]
                fuentes = resultado["fuentes"]

        st.write(respuesta_texto)
        if fuentes:
            with st.expander("Ver fuentes"):
                for fuente in fuentes:
                    st.write(f"📄 {fuente['documento']} — página {fuente['pagina']}")

    st.session_state.historial.append({
        "rol": "assistant",
        "contenido": respuesta_texto,
        "fuentes": fuentes,
    })
