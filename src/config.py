from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Paths
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"
DB_PATH = BASE_DIR / "db" / "chat_history.db"

# Files
CHUNKS_JSON = PROCESSED_DIR / "chunks.json"
INDEX_PATH = INDEX_DIR / "index.faiss"
INDEX_METADATA = INDEX_DIR / "metadata.json"

# Chunking
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
MAX_PARAGRAPH_LEN = 800
MIN_PARAGRAPH_LEN = 50

# Retrieval
TOP_K = 5

# Embeddings
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large"

# OpenAI
OPENAI_MODEL = "gpt-4o-mini"

# UI
DEFAULT_HISTORY_K = 10

