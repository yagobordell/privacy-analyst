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
- [ ] Fase 4 — Embeddings y base de datos vectorial
- [ ] Fase 5 — Pipeline RAG completo
- [ ] Fase 6 — Interfaz de chat
- [ ] Fase 7 — Pulido, pruebas y verificación de privacidad

## Arquitectura
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
- [ ] Fase 4 — Embeddings y base de datos vectorial
- [ ] Fase 5 — Pipeline RAG completo
- [ ] Fase 6 — Interfaz de chat
- [ ] Fase 7 — Pulido, pruebas y verificación de privacidad

## Arquitectura
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
- [ ] Fase 4 — Embeddings y base de datos vectorial
- [ ] Fase 5 — Pipeline RAG completo
- [ ] Fase 6 — Interfaz de chat
- [ ] Fase 7 — Pulido, pruebas y verificación de privacidad

## Arquitectura
Usuario → Interfaz de chat (Streamlit)
↓
┌─────────────────────────────────────┐
│ Tu ordenador (offline) │
│ │
│ Ingesta → Base vectorial → LLM local│
│ (PDF→chunks) (ChromaDB) (Ollama) │
└─────────────────────────────────────┘


Ningún componente requiere conexión a internet una vez descargados los modelos.

## Stack tecnológico

| Componente | Herramienta | Motivo |
|---|---|---|
| Motor LLM | Ollama + Llama 3.1 8B (Q4_K_M) | Ejecuta modelos cuantizados en CPU sin GPU dedicada |
| Embeddings | nomic-embed-text (pendiente de integrar) | Modelo ligero, corre en CPU |
| Base vectorial | ChromaDB (pendiente de integrar) | Embebida, sin servidor externo, persistencia en disco |
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

### 4. Descargar el modelo LLM

Desde PowerShell:

```powershell
ollama pull llama3.1:8b
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
python3 src/ingestion/parser.py    # extrae texto de los PDFs en data/
python3 src/ingestion/chunker.py   # trocea el texto extraído
```

## Estructura del proyecto
privacy-analyst/
├── data/ # PDFs de prueba (no versionado, ver .gitignore)
│ └── procesados/ # JSONs con texto extraído por página
│ └── chunks/ # JSONs con texto troceado
├── src/
│ ├── ingestion/ # parsing de PDF, OCR, chunking
│ ├── embeddings/ # generación de embeddings (pendiente)
│ ├── vectorstore/ # integración con ChromaDB (pendiente)
│ ├── rag/ # pipeline de recuperación + generación (pendiente)
│ └── ui/ # interfaz Streamlit (pendiente)
├── notebooks/ # experimentación
├── tests/
└── README.md


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

## Privacidad

Este proyecto está diseñado para que, tras la configuración inicial (descarga
de modelos), no se realice ninguna conexión de red saliente durante el uso
normal. _(Pendiente de verificación y documentación formal en la Fase 7 —
se incluirán capturas o logs de red confirmando ausencia de tráfico externo)._

## Licencia

_(Pendiente de decidir)_
