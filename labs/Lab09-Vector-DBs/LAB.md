# Lab 09 — CRUD Operations on Vector Databases (ChromaDB)

**Duration** ~45 min · **GPU required** No · **Backend** local embeddings + in-memory Chroma
**Verified** ✅ 2026-08-15 — 19 code cells, **0 errors**, ~15 s total.

## What this lab does
Introduces **vector embeddings** and then performs full **CRUD** (Create, Read, Update,
Delete) against a **ChromaDB** in-memory vector store, including similarity search with scores.

## Objectives
- Understand and apply word embeddings.
- Create and manage a Chroma in-memory vector store.
- Update and delete stored vectors.
- Perform CRUD operations on a vector database.

## Environment specifics
Embeddings are computed **locally in your notebook** with a HuggingFace sentence-transformer
(`sentence-transformers/all-mpnet-base-v2`, ~420 MB, downloaded on first run). This does not
need a GPU — it ran fine on CPU — but it is the one Ollama-free lab in the retrieval track.

The vector store is **in-memory**: it disappears when the kernel restarts. That is deliberate
and keeps the lab self-contained.

## Walkthrough
1. **Embeddings**
   ```python
   from langchain_huggingface.embeddings import HuggingFaceEmbeddings
   embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
   query_result = embeddings.embed_query("This is a test document.")
   len(query_result)      # 768 dimensions
   ```
   Inspect the first few numbers — this is the concrete answer to "what is an embedding".
2. **Create the store** — `Chroma.from_texts(texts=[...], embedding=embeddings)` over a small
   corpus (`"I love cats"`, `"I love programming"`, …).
3. **Read / similarity search**
   ```python
   result = vector_store.similarity_search_with_score(query="I love machine learning", k=2)
   ```
   **Lower score = closer match** — call this out, it is a common misreading.
4. **Update** — change a stored document and re-query to see ranking shift.
5. **Delete** — remove entries and confirm they no longer surface.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Long pause on first cell | Downloading the 420 MB embedding model. |
| `ModuleNotFoundError: langchain_chroma` | Install from `requirements-fdp.txt`. |
| Results look wrong after edits | The store is in-memory; re-run the creation cell after a kernel restart. |

## Teaching notes
The natural prerequisite for Labs 10 and 11. Ask participants to add a sentence about an
unrelated topic and watch the similarity scores separate — it makes semantic distance
tangible without any mathematics.
