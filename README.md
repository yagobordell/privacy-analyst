# Analista de Privacidad — RAG 100% Local

Sistema de Generación Aumentada por Recuperación (RAG) para consultar documentos
sensibles (nóminas, contratos, historiales médicos) mediante chat, garantizando
que ningún dato sale del ordenador. Todo el procesamiento —extracción de texto,
embeddings, búsqueda semántica y generación de respuestas— ocurre en local,
sin llamadas a APIs externas.

## Motivación

Los sistemas RAG basados en APIs de terceros (OpenAI, Anthropic, etc.) no son
viables para documentos altamente sensibles: el contenido del documento viaja
a servidores externos en cada consulta. Este proyecto resuelve ese problema
ejecutando cada componente del pipeline —desde el modelo de lenguaje hasta la
base de datos vectorial— en el propio hardware del usuario.

## Estado del proyecto

En desarrollo activo. Progreso actual:

- [x] Fase 0 — Entorno de desarrollo
- [x] Fase 1 — Motor LLM local (Ollama)
- [x] Fase 2 — Ingesta y extracción de texto de PDFs
- [x] Fase 3 — Chunking de documentos
- [x] Fase 4 — Embeddings y base de datos vectorial
- [x] Fase 5 — Pipeline RAG completo
- [ ] Fase 6 — Interfaz de chat
- [ ] Fase 7 — Pulido, pruebas y verificación de privacidad

## Arquitectura
Usuario → Interfaz de chat (Streamlit)
↓
┌─────────────────────────────────────┐
│ Tu ordenador (offline) │
│ │
│ Ingesta → Base vectorial → LLM local │
│ (PDF→chunks) (ChromaDB) (Ollama) │
└─────────────────────────────────────┘

Ningún componente requiere conexión a internet una vez descargados los modelos.

## Stack tecnológico

| Componente | Herramienta | Motivo |
|---|---|---|
| Motor LLM | Ollama + Llama 3.1 8B (Q4_K_M) | Ejecuta modelos cuantizados en CPU sin GPU dedicada |
| Embeddings | bge-m3 (vía Ollama) | Modelo multilingüe, buen rendimiento en español (ver Decisiones técnicas) |
| Base vectorial | ChromaDB (métrica coseno) | Embebida, sin servidor externo, persistencia en disco |
| Extracción de PDF | pdfplumber + pytesseract (OCR) | Detección automática de texto nativo vs. escaneado |
| Chunking | langchain-text-splitters | Troceado recursivo con solapamiento |
| Interfaz | Streamlit (pendiente de integrar) | Chat web sin necesidad de frontend dedicado |

## Requisitos de hardware

Probado en:
- CPU de consumo (sin GPU dedicada)
- 16 GB de RAM
- Rendimiento observado: ~67 tokens/s con Llama 3.1 8B (Q4_K_M) — ver sección de benchmarks

## Instalación

### Requisitos previos

- Windows 10/11 con WSL2
- Windows 11 22H2+ recomendado (necesario para el modo de red "mirrored", ver Troubleshooting)

### 1. Instalar WSL2

Desde PowerShell como administrador:

```powershell
wsl --install
```

Reiniciar el ordenador tras la instalación.

### 2. Configurar el entorno dentro de WSL (Ubuntu)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git build-essential
sudo apt install -y tesseract-ocr tesseract-ocr-spa poppler-utils

git clone https://github.com/yagobordell/privacy-analyst.git
cd privacy-analyst

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Instalar Ollama (en Windows nativo)

Descargar desde [ollama.com/download](https://ollama.com/download) e instalar
con las opciones por defecto. Ollama queda corriendo como servicio en
`http://localhost:11434`.

### 4. Descargar los modelos necesarios

Desde PowerShell:

```powershell
ollama pull llama3.1:8b
ollama pull bge-m3
```

### 5. Verificar la conexión WSL ↔ Ollama

Desde la terminal de Ubuntu (WSL):

```bash
curl http://localhost:11434
```

Debería devolver `Ollama is running`. Si falla, ver la sección de
Troubleshooting más abajo.

## Uso

_(Pendiente — se documentará al completar la Fase 6, interfaz de chat)_

```bash
source venv/bin/activate
python3 src/ingestion/parser.py      # extrae texto de los PDFs en data/
python3 src/ingestion/chunker.py     # trocea el texto extraído
python3 src/vectorstore/indexer.py   # genera embeddings e indexa en ChromaDB
```

## Estructura del proyecto
privacy-analyst/
├── data/ # PDFs de prueba (no versionado, ver .gitignore)
│ └── procesados/ # JSONs con texto extraído por página
│ └── chunks/ # JSONs con texto troceado
│ └── chroma_db/ # Base de datos vectorial persistente (no versionado)
├── src/
│ ├── ingestion/ # parsing de PDF, OCR, chunking
│ ├── vectorstore/ # generación de embeddings e indexación en ChromaDB
│ ├── rag/ # pipeline de recuperación + generación (pendiente)
│ └── ui/ # interfaz Streamlit (pendiente)
├── notebooks/ # experimentación
├── tests/
└── README.md

## Decisiones técnicas

### Cambio de modelo de embeddings: nomic-embed-text → bge-m3

Durante la Fase 4 se probó primero `nomic-embed-text` como modelo de embeddings.
Al evaluar la recuperación con preguntas en español que no compartían vocabulario
literal con los documentos (ej. "¿qué parte de mi sueldo se va a Hacienda?" para
recuperar chunks sobre IRPF), el sistema devolvía consistentemente fragmentos
irrelevantes (un contrato de trabajo) por delante de los relevantes (nóminas
con las deducciones fiscales).

**Diagnóstico**: se midieron las distancias de todos los chunks frente a la
consulta. El rango de distancias era muy estrecho (0.399–0.511 con métrica
coseno) para un corpus con contenidos claramente distintos, lo que indicaba
que el modelo no discriminaba bien el significado en español. Chunks que
contenían literalmente la palabra "IRPF" aparecían peor rankeados que
fragmentos sin relación temática.

**Causa probable**: `nomic-embed-text` está entrenado mayoritariamente en
corpus en inglés, con soporte multilingüe débil.

**Solución**: se cambió a `bge-m3`, un modelo de embeddings multilingüe
(100+ idiomas, incluido español) de BAAI. Tras reindexar, el rango de
distancias se amplió (0.476–0.650) y las nóminas relevantes pasaron a
ocupar las primeras posiciones, con el contrato relegado al final del
ranking — el comportamiento esperado.

**Trade-off**: `bge-m3` genera vectores de mayor dimensión (1024 vs. 768)
y es un modelo más pesado computacionalmente que `nomic-embed-text`. Para
el volumen de documentos de este proyecto, el impacto en rendimiento es
despreciable frente a la mejora en calidad de recuperación.

### Métrica de distancia en ChromaDB: euclidiana → coseno

Por defecto, ChromaDB usa distancia euclidiana. Con embeddings no
normalizados a longitud unitaria, esta métrica se ve afectada por la
magnitud de los vectores además de su dirección semántica, degradando
la calidad de la búsqueda. Se configuró la colección explícitamente con
`metadata={"hnsw:space": "cosine"}`, que solo considera el ángulo entre
vectores (el significado), ignorando su magnitud.

## Troubleshooting

### WSL2 no se conecta a Ollama (`localhost:11434`)

Por defecto, WSL2 puede no resolver `localhost` correctamente hacia servicios
corriendo en Windows nativo (como Ollama), incluso estando en la misma máquina.

**Síntoma:**
curl http://localhost:11434
curl: (7) Failed to connect to localhost port 11434

**Solución aplicada:** activar el modo de red "mirrored" de WSL2, que unifica
el stack de red de WSL con el de Windows (requiere Windows 11 22H2+).

1. Crear/editar `C:\Users\<usuario>\.wslconfig`:
```ini
   [wsl2]
   networkingMode=mirrored
```
2. Reiniciar WSL desde PowerShell:
```powershell
   wsl --shutdown
```
3. Verificar desde la terminal de Ubuntu:
```bash
   curl http://localhost:11434
   # Debería devolver: "Ollama is running"
```

**Alternativa** (si tu versión de Windows no soporta `mirrored`): usar la IP
del host Windows en vez de `localhost`, obtenida con `cat /etc/resolv.conf`
desde WSL.

### Caracteres con acentos corruptos en PowerShell (`n�mina` en vez de `nómina`)

La consola de PowerShell no interpreta UTF-8 por defecto. Ejecutar al inicio
de cada sesión:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

## Benchmarks

| Modelo | Cuantización | Tokens/s (CPU, sin GPU) |
|---|---|---|
| Llama 3.1 8B | Q4_K_M | ~67 tok/s |

## Limitaciones conocidas

- **Extracción de tablas**: `pdfplumber` extrae el texto de tablas (como las
  de conceptos de nómina) como texto corrido, no como estructura de filas y
  columnas. Los valores permanecen asociados a sus conceptos, pero preguntas
  que requieran sumar varias líneas de la tabla podrían necesitar una
  extracción más estructurada con `extract_table()`. Pendiente de evaluar si
  es necesario tras probar el pipeline completo.
- **Codificación de caracteres especiales**: en algunos PDFs, caracteres como
  `º` se extraen incorrectamente como `?`, probablemente por la tabla de
  fuentes embebida en el PDF de origen. Afecta a casos puntuales, no a la
  legibilidad general del texto.
- **Corpus de prueba reducido**: la validación de la Fase 4 se hizo con un
  corpus de solo 11 chunks. Es suficiente para detectar problemas evidentes
  de discriminación semántica, pero no para medir con precisión estadística
  la calidad de la recuperación a mayor escala.
- **Preguntas ambiguas entre múltiples documentos similares**: cuando una
  pregunta no especifica el documento (ej. "¿qué parte de mi sueldo se va
  a Hacienda?" con varias nóminas y un contrato indexados), el sistema
  puede fallar en identificar el contexto correcto. Diagnóstico completo:
  - El pipeline de recuperación (embeddings + ChromaDB) funciona
    correctamente en general, pero para este vocabulario concreto, un
    chunk del contrato (que menciona una cifra de dinero) obtiene una
    distancia semántica *menor* que las nóminas con el dato de IRPF
    realmente relevante — el modelo de embeddings confunde "dinero en
    general" con "retención fiscal específica".
  - Un filtro por umbral de distancia no resuelve esto, porque el chunk
    problemático no es "ruido lejano" sino un falso positivo con alta
    similitud aparente.
  - Con el contexto limpiado manualmente (solo las nóminas), el LLM sí
    logra comparar y listar los tres valores por documento, aunque con
    algún error conceptual (confunde base imponible con cuota retenida
    en un caso).
  - **Mitigación funcional**: preguntas que especifican el documento
    (ej. "en la nómina estándar") se resuelven correctamente mediante
    filtrado por metadata, implementado en el pipeline.
  - **Mejoras futuras posibles**: un reranker con cross-encoder tras la
    recuperación inicial (mencionado en el diseño original del stack)
    probablemente distinguiría mejor este tipo de falso positivo que la
    búsqueda por embeddings puros.
- **Extracción de tablas**: ver sección de la Fase 2/3.
- **Codificación de caracteres especiales**: ver sección de la Fase 2.
  Se implementó además un reranker con cross-encoder multilingüe
  (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) para mitigar falsos
  positivos del bi-encoder. Resultado: el cross-encoder **coincide** con
  el bi-encoder en puntuar el chunk del contrato como más relevante que
  las nóminas para esta pregunta concreta (score -3.94 vs. -5.4 a -5.7),
  lo que indica que el problema no es un fallo aislado de un modelo, sino
  que la pregunta, en términos de vocabulario, comparte más campo
  semántico general ("sueldo", "dinero") con el contrato que con la
  terminología técnica de las nóminas ("IRPF", "retención"). Una posible
  solución sería *query rewriting* (reformular la pregunta con
  vocabulario técnico antes de la búsqueda), no implementado por quedar
  fuera del alcance de este proyecto.
## Privacidad

Este proyecto está diseñado para que, tras la configuración inicial (descarga
de modelos), no se realice ninguna conexión de red saliente durante el uso
normal. _(Pendiente de verificación y documentación formal en la Fase 7 —
se incluirán capturas o logs de red confirmando ausencia de tráfico externo)._

## Licencia

_(Pendiente de decidir)_
