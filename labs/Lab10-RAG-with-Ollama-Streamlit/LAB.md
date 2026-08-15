# Lab 10 — Retrieval-Augmented Generation with Ollama + LangChain

**Duration** ~60 min · **GPU required** No · **Backend** Ollama (`http://10.79.253.112:11434`) + FAISS
**Verified** ✅ 8 cells, 1 headless error only — an `input()` chat loop, which works
interactively.

## What this lab does
Builds a **conversational RAG** system: PDFs are chunked, embedded into FAISS, and a
history-aware retriever feeds relevant context to the LLM so answers stay grounded.

## Objectives
- Load and process PDF documents into embeddings using FAISS.
- Implement a history-aware retriever for conversational context.
- Construct a RAG pipeline for document Q&A.
- Run an interactive chat loop over document content.

## 🚨 Patched pip cells
The upstream notebook starts with dependency installs that **break the environment**:
```python
!pip install numpy==1.26.4 --force-reinstall     # ← force-reinstall churns the ABI
!pip install faiss-cpu==1.7.4
!pip install langchain-community==0.0.38         # ← catastrophic downgrade
!pip install langchain-text-splitters
```
`langchain-community==0.0.38` against `langchain-core 0.3.x` is wildly incompatible — this is
where the `langchain-community 0.0.38 requires langchain-core<0.2.0` conflict comes from.
These lines are **commented out and tagged `[FDP-PATCHED]`** in this pack. Install from
`requirements-fdp.txt` instead.

## Prerequisite — you must supply documents
The notebook reads from a **`./data` directory** that does not exist in the repo:
```python
pdf_directory = "./data"
loader = PyPDFDirectoryLoader(pdf_directory)
```
Create it and add at least one PDF before running:
```bash
mkdir -p data && cp /path/to/your.pdf data/
```
Any PDF works — course notes or a research paper make the demo more meaningful.

## Walkthrough
1. **Imports** — `ChatOllama`, `OllamaEmbeddings`, `RecursiveCharacterTextSplitter`,
   `PyPDFDirectoryLoader`, `FAISS`, `create_retrieval_chain`; then `nest_asyncio.apply()`.
2. **Load** PDFs from `./data`.
3. **Chunk** — `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`. The
   overlap is what stops answers being cut in half at a boundary.
4. **Embed + store** — embeddings via `nomic-embed-text:latest` on the Ollama server, indexed
   into FAISS.
5. **History-aware retriever** — a first prompt rewrites a follow-up question into a
   standalone one (so *"and what about its cost?"* becomes self-contained before retrieval).
6. **RAG chain** — `create_retrieval_chain` + `create_stuff_documents_chain`.
7. **Chat loop** — `main()` runs an interactive loop; this is the cell that cannot run
   headlessly.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `StdinNotImplementedError` | Run interactively — the loop uses `input()`. |
| Empty / no documents | `./data` missing or has no PDFs. |
| Nonsense answers | Chunk size too large or too few retrieved docs; tune `k` and `chunk_size`. |
| Conflict errors from langchain | A patched pip cell was re-enabled. Reinstall from `requirements-fdp.txt`. |

## Teaching notes
The single most important architecture in the programme — Session 5 of the curriculum. Show
a question the base model answers wrongly, then the same question answered correctly from the
PDF. That contrast is the entire argument for RAG.
