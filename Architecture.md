# Architecture & Design Walkthrough (test-drive-chatbot)



## High-level architecture
- **Data source**: 10 fixed article URLs (see `src/urls.py`).
- **Scraping**: `requests` + `BeautifulSoup` extract title and paragraphs; raw HTML + JSON text stored under `data/raw/`.
- **Corpus building**: paragraphs cleaned/chunked with length rules; metadata saved to `data/processed/chunks.json`.
- **Embeddings**: Sentence-Transformers `intfloat/multilingual-e5-large` (Hebrew-capable), normalized vectors.
- **Vector store**: Local FAISS `IndexFlatL2` + sidecar metadata JSON under `data/index/`.
- **Retriever**: optional car-model filter; top-k similarity search.
- **Orchestrator**: builds prompt with context + history; calls OpenAI `gpt-4o-mini`; stores turns in SQLite `db/chat_history.db`.
- **UI**: Streamlit chat UI with RTL styling for Hebrew, session picker, new conversation, delete-all, and source display.
- **Config**: `src/config.py` centralizes paths, chunking params, top-k, models, DB path.

                          ┌───────────────────────────┐
                          │  1. Article URLs (10x)     │
                          │  src/urls.py               │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                      ┌─────────────────────────────────────┐
                      │ 2. Scraping Layer                    │
                      │  fetch_articles.py                   │
                      │  - requests HTML                     │
                      │  - BeautifulSoup extraction          │
                      │  - title + paragraphs                │
                      └─────────────┬───────────────────────┘
                                    │
                                    ▼
                   ┌────────────────────────────────────────────┐
                   │ 3. Raw Data Storage                        │
                   │  data/raw/*.html + *.txt                   │
                   └───────────────────┬────────────────────────┘
                                       │
                                       ▼
               ┌─────────────────────────────────────────────────────────┐
               │ 4. Corpus Builder                                       │
               │  build_corpus.py                                        │
               │  - paragraph splitting                                  │
               │  - smart chunking (sub-split long, merge short)         │
               │  - metadata: {url, title, car_model, chunk_id, text}    │
               └───────────────────────────┬─────────────────────────────┘
                                           │
                                           ▼
                     ┌──────────────────────────────────────────┐
                     │ 5. Processed Chunks                      │
                     │  data/processed/chunks.json              │
                     └─────────────┬────────────────────────────┘
                                   │
                                   ▼
                ┌──────────────────────────────────────────────────┐
                │ 6. Embeddings                                    │
                │  embeddings.py                                   │
                │  Model: intfloat/multilingual-e5-large           │
                │  - embed chunk_texts                             │
                │  - normalize vectors                             │
                └────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
           ┌────────────────────────────────────────────────────────────────┐
           │ 7. Vector Store (FAISS)                                         │
           │  vector_store.py + metadata.json                                │
           │  - IndexFlatL2 (local)                                          │
           │  - store embeddings                                             │
           │  - store metadata (chunk_id → url/title/car model/text)         │
           └──────────────────────┬─────────────────────────────────────────┘
                                  │
                                  ▼
       ┌──────────────────────────────────────────────────────────────────────┐
       │ 8. Retriever                                                         │
       │  retriever.py                                                        │
       │  - detect car model mentioned in query (optional filter)             │
       │  - embed user query                                                  │
       │  - FAISS similarity search top_k                                     │
       │  - return ranked chunks + distances + metadata                       │
       └───────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
             ┌──────────────────────────────────────────────────────────────┐
             │ 9. Chat Orchestrator                                         │
             │  chat_orchestrator.py                                        │
             │  - load recent chat history (SQLite)                         │
             │  - assemble SYSTEM + CONTEXT + HISTORY + USER messages       │
             │  - context = top retrieved chunks                            │
             │  - call OpenAI mini-4o                                       │
             │  - store new turn in chat_history.db                         │
             └───────────────────────────┬──────────────────────────────────┘
                                         │
                                         ▼
                ┌────────────────────────────────────────────────────────┐
                │ 10. Chat History Store                                 │
                │  SQLite: db/chat_history.db                            │
                │  - session-based conversation memory                   │
                │  - list sessions / create / append / load history      │
                └────────────────────────┬────────────────────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────────────┐
                      │ 11. Streamlit UI                             │
                      │  ui/streamlit_app.py                         │
                      │  - Hebrew RTL interface                      │
                      │  - conversation selector                     │
                      │  - new conversation                          │
                      │  - delete all history                        │
                      │  - display sources per answer                │
                      └──────────────────────────────────────────────┘



## Why these choices
- **Local-first vector store**: FAISS is lightweight, fast, and avoids managed services; good for offline/edge or interview constraints. Pinecone was not used to keep dependencies minimal and avoid external service setup.
- **Sentence-Transformers multilingual-e5-large**: strong performance on multilingual (Hebrew) retrieval; widely used; easy to run locally with CPU/GPU.
- **SQLite for chat history**: zero setup, file-based, sufficient for per-session memory and list of past conversations.
- **Streamlit UI**: rapid prototyping, built-in chat widgets, easy RTL tweaks; good for demo.
- **Explicit .env loading**: `dotenv` loads from repo root to avoid CWD issues with Streamlit.
- **Chunking heuristics**: balance between recall and precision; paragraph-based, sub-chunking long paragraphs, skipping/merging very short ones.

## Detailed pipeline
1) **Scraping (`src/scraping/fetch_articles.py`)**
   - Iterates `ARTICLE_URLS`.
   - `requests.get` (with timeout), set encoding from `apparent_encoding`.
   - `BeautifulSoup` removes `script/style/header/footer/nav/aside`.
   - Extracts title (`h1` or `<title>`) and all `<p>` texts.
   - Saves:
     - HTML → `data/raw/<slug>.html`
     - JSON (`url`, `title`, `paragraphs`) → `data/raw/<slug>.txt`
   - Errors are caught and logged; scraping continues.

2) **Corpus building (`src/ingestion/build_corpus.py`)**
   - Loads all `data/raw/*.txt`.
   - Rules:
     - If paragraph length > `MAX_PARAGRAPH_LEN` (800), split into overlapping chunks (`CHUNK_SIZE` 500, overlap 100).
     - If paragraph length < `MIN_PARAGRAPH_LEN` (50), buffer/merge with next.
   - Metadata per chunk:
     - `chunk_id`, `article_title`, `article_url`, `car_model` (regex guess from title), `chunk_text`.
   - Saves all chunks to `data/processed/chunks.json`.
   - Prints count and average length for quick sanity check (adjust `CHUNK_SIZE`/`CHUNK_OVERLAP` if needed).

3) **Embeddings (`src/rag/embeddings.py`)**
   - Singleton loader via `lru_cache`.
   - `model.encode(..., normalize_embeddings=True)` returns `np.ndarray`.

4) **Index build (`src/ingestion/build_index.py`)**
   - Loads chunks JSON.
   - Embeds all `chunk_text`s.
   - Builds FAISS `IndexFlatL2` (L2 on normalized vectors ≈ cosine).
   - Persists:
     - `data/index/index.faiss`
     - `data/index/metadata.json` (same structure as chunks).

5) **Vector store helpers (`src/rag/vector_store.py`)**
   - Load/save FAISS index and metadata; ensure helpful errors if missing.

6) **Retriever (`src/rag/retriever.py`)**
   - Extract candidate car-model tokens from titles/metadata.
   - Detect model mentions in query (case-insensitive substring).
   - If models detected → filter metadata to matching articles; else search all.
   - Embed query, FAISS search top_k (`TOP_K` default 5).
   - Return (chunk, distance) pairs.

7) **Chat orchestrator (`src/rag/chat_orchestrator.py`)**
   - Ensures `db/chat_history.db` table: `(id, session_id, user_message, assistant_message, created_at)`.
   - `list_sessions`: returns session ids + first user message for labeling.
   - `fetch_history(session_id, k=DEFAULT_HISTORY_K)`: recent turns for context.
   - `answer(user_query, session_id)`:
     1. Retrieve relevant chunks.
     2. Fetch recent history.
     3. Build messages:
        - SYSTEM: "You are an assistant answering questions about Hebrew car reviews from auto.co.il. Use only the provided context. Do not hallucinate."
        - SYSTEM: "Context: ... (chunks + metadata + distance)"
        - HISTORY: alternating user/assistant pairs.
        - USER: current query.
     4. Call OpenAI `gpt-4o-mini`.
     5. Store turn in SQLite.
     6. Return assistant reply + list of sources (title, url, chunk_id, distance).
   - `.env` loaded explicitly from repo root (`BASE_DIR/.env`).

8) **UI (`src/ui/streamlit_app.py`)**
   - RTL styling for Hebrew chat.
   - Sidebar:
     - Button: “Start new conversation” (new `session_id`, rerun).
     - Radio list of existing conversations labeled by first user message (or ID); selecting reruns and loads that history.
     - “Delete all past conversations” clears SQLite and starts fresh.
   - Main area:
     - Displays history (user/assistant chat bubbles).
     - `st.chat_input` for new message; answers shown with sources (expandable).
   - Uses `session_id` to isolate histories.

9) **Scripts**
   - `scripts/ingest_data.py`: orchestrates fetch → corpus → index.

10) **Configuration (`src/config.py`)**
    - Paths (data, index, db).
    - Chunk params (`CHUNK_SIZE`, `CHUNK_OVERLAP`, `MAX_PARAGRAPH_LEN`, `MIN_PARAGRAPH_LEN`).
    - Retrieval `TOP_K`.
    - Model names (`EMBEDDING_MODEL_NAME`, `OPENAI_MODEL`).

## Data flow summary
`ARTICLE_URLS` → scrape (HTML + paragraphs) → `data/raw/*.txt` → chunking/metadata → `data/processed/chunks.json` → embed → `data/index/index.faiss` + `metadata.json` → runtime retriever → orchestrator builds prompt → OpenAI → response + sources → stored in SQLite.

## How to run (quick)
```
pip install -r requirements.txt
echo "OPENAI_API_KEY=..." > .env
python scripts/ingest_data.py      # scrape → corpus → index
streamlit run src/ui/streamlit_app.py
```
First run downloads the embedding model (~2GB).

## Reasons behind choices
- **Why FAISS over Pinecone**: Local, zero external deps, predictable latency, fits offline/demo constraints. Pinecone is great for managed scale, but here simplicity and local-first were requirements.
- **Why multilingual-e5-large**: Strong multilingual retrieval (Hebrew), good community benchmarks, easy to fine-tune/replace.
- **Chunking heuristics**: Paragraph-first to respect semantic boundaries; sub-chunk long paragraphs to avoid context dilution; skip/merge tiny ones to reduce noise.
- **Filtering by car model**: Simple, fast heuristic to improve relevance when the query names a model; falls back to full search otherwise.
- **SQLite for history**: Minimal setup, good enough for single-user/multi-session; easy to migrate later to Postgres if multi-user scale is needed.
- **Prompt design**: Strict system message to reduce hallucinations; includes distances and sources to encourage grounded answers.
- **Hebrew/RTL support**: UI CSS to align chat messages RTL; model choice supports Hebrew embeddings.
- **Error handling**: Scraper logs and continues on failures; missing index/metadata surfaces clear errors.

## Possible extensions
- Replace FAISS with a managed vector DB (Pinecone, Qdrant, Weaviate) for multi-user scale and hybrid search.
- Add reranking (e.g., cross-encoder) to refine top-k.
- Add evals: synthetic Q/A generation and retrieval accuracy checks.
- Add auth and per-user namespacing for sessions in SQLite/Postgres.
- Add caching for embeddings and OpenAI responses if cost/latency matters.

## For the detailed system architecture, see Architecture.md.



