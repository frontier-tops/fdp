# Lab 11 — RAG with Open WebUI (no code)

**Duration** ~30 min · **GPU required** No · **Tool** Open WebUI at **http://10.79.253.112:3000**
**Verified** ✅ Documentation-only notebook (0 code cells).

## What this lab does
The same RAG idea as Lab 10, but entirely through the **Open WebUI** interface — upload
documents, query them, and see grounded answers without writing code.

## Objectives
- Understand the RAG architecture and how it improves response accuracy.
- Navigate Open WebUI as a retrieval-augmented query interface.
- Explore model selection and interact with the RAG pipeline.
- Submit queries and retrieve document-grounded answers.
- Validate the integration of Open WebUI, the RAG pipeline and FAISS vector search.

## Access
**http://10.79.253.112:3000** — reachable on the participant VPN (verified 2026-08-15).
There is also a dedicated RAG service at **http://10.79.253.112:8090**; ask the facilitator
which one the session is using.

## Walkthrough
1. **Log in** to Open WebUI.
2. **Upload a document** (or select a pre-loaded collection) so it is chunked, embedded and
   indexed.
3. **Select a model** — any of the ten on the Ollama server.
4. **Query the documents** — ask something answerable only from the uploaded content.
5. **Inspect grounding** — check the citations/sources the interface shows.
6. **Test several queries** and judge accuracy and relevance.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Page will not load | VPN down or wrong network. |
| Upload succeeds but answers ignore it | The document may still be indexing; wait and retry. |
| Answers not grounded | Confirm the RAG/document mode is actually selected, not plain chat. |

## Teaching notes
Run straight after Lab 10 so faculty see the same pipeline twice — once built by hand, once
as a product. Emphasise that the UI is doing exactly the chunk → embed → retrieve → generate
steps they coded, which demystifies commercial RAG tools.
