# test-drive-chatbot

Local-first Retrieval-Augmented Generation chatbot that answers questions in Hebrew about 10 specific car review articles from auto.co.il. The system scrapes the articles, builds a FAISS index over sentence-transformer embeddings, and serves a Streamlit UI with per-session chat memory stored in SQLite.

## Project structure
- `data/raw/` – raw HTML and extracted plain text  
- `data/processed/` – cleaned chunk metadata (`chunks.json`)  
- `data/index/` – FAISS index (`index.faiss`) and metadata (`metadata.json`)  
- `db/chat_history.db` – SQLite chat history (auto-created)  
- `src/` – application code  
  - `config.py` – paths and parameters  
  - `urls.py` – ARTICLE_URLS constant (10 target URLs)  
  - `scraping/fetch_articles.py` – download + parse articles  
  - `ingestion/build_corpus.py` – paragraph splitting and chunking  
  - `ingestion/build_index.py` – embedding + FAISS index build  
  - `rag/embeddings.py` – sentence-transformer loader  
  - `rag/vector_store.py` – index helpers  
  - `rag/retriever.py` – search with optional car model filtering  
  - `rag/chat_orchestrator.py` – prompt assembly, OpenAI call, chat history  
  - `ui/streamlit_app.py` – minimal Streamlit interface  
- `scripts/ingest_data.py` – run scraping → corpus → index  
- `.env.example` – environment variables  
- `requirements.txt`

## Quickstart
1) Create and activate a Python 3.11+ virtualenv.  
2) Install dependencies:
```
pip install -r requirements.txt
```
3) Configure environment (if `.env.example` is missing, create `.env` manually):
```
cp .env.example .env  # or echo "OPENAI_API_KEY=..." > .env
# set OPENAI_API_KEY
```
4) Ingest data (scrape → chunks → index):
```
python scripts/ingest_data.py
```
5) Run the UI:
```
streamlit run src/ui/streamlit_app.py
```

## Notes and checks
- Scraping: verify at least one or two articles in `data/raw/*.txt` to ensure paragraph extraction in Hebrew is correct.  
- Encoding: all files are UTF-8; BeautifulSoup + requests keep encoding hints.  
- Chunking: tweak `CHUNK_SIZE`, `CHUNK_OVERLAP`, and `MIN_PARAGRAPH_LEN` in `src/config.py` if chunks are too short/long.  
- Retrieval: uses `intfloat/multilingual-e5-large` with FAISS `IndexFlatL2`.  
- Chat UI: sidebar shows existing conversations (auto-labeled with the first user message), a “Start new conversation” button, and “Delete all past conversations”. Each conversation is isolated by `session_id` (SQLite).  
- RTL: the chat area is set to RTL for Hebrew alignment.  
- Sources: each answer surfaces article title + URL of retrieved chunks.  

## Troubleshooting
- If scraping fails for a URL, it is skipped with a warning; rerun ingestion once connectivity is available.  
- If FAISS index is missing, run `python scripts/ingest_data.py` again.  
- If the UI says `OPENAI_API_KEY not set`, ensure `.env` at repo root contains `OPENAI_API_KEY=...` and rerun.  
- First run will download the embedding model (~2GB). Allow a few minutes.  

