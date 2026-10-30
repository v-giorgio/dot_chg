# Backend IA — Projects

Three independent Python backend projects covering REST APIs, LLMs, and semantic search.

---

## Projects

| # | Project | Main Stack |
|---|---------|------------|
| 1 | [Library FastAPI](#1-library-fastapi) | FastAPI · SQLite · SQLAlchemy · pytest |
| 2 | [Chatbot Python](#2-chatbot-python) | Flask · LangChain · GPT-4o · LangSmith |
| 3 | [Semantic Search Blog](#3-semantic-search-blog) | Flask · FAISS · Ollama · BeautifulSoup4 |

---

## 1. Library FastAPI

REST API for managing a virtual library. Supports creating, listing, updating, and soft-deleting books, with pagination, filters, and a generic `ApiResponse[T]` response envelope applied to every route.

### Technologies

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI + Uvicorn |
| Database | SQLite via SQLAlchemy 2.x (`Mapped` / `mapped_column`) |
| Validation | Pydantic v2 |
| Data access | Repository pattern (`BookRepository`) |
| Tests | pytest + httpx — 88 cases (unit + integration) |

### Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/books/` | Create a book |
| `GET` | `/books/` | List books with filters and pagination |
| `PUT` | `/books/{id}` | Partial update |
| `DELETE` | `/books/{id}` | Soft delete (`is_active = False`) |
| `GET` | `/books/{id}` | Get book by ID |

### Flow

```mermaid
flowchart TD
    Client([HTTP Client])
    Router["FastAPI Router\nbooks.py"]
    Repo["BookRepository\nbook_repository.py"]
    DB[(SQLite\nlibrary.db)]

    Client -->|GET / POST / PUT / DELETE| Router
    Router -->|Depends injection| Repo
    Repo -->|SQLAlchemy session| DB
    DB -->|Book ORM rows| Repo
    Repo -->|BookResponse| Router
    Router -->|ApiResponse T| Client
```

---

## 2. Chatbot Python

Stateless REST API specialized in Python-related answers. Built with Flask and LangChain, with LangSmith tracing on every inference call. Each request is independent — no conversation history is kept between calls. Input and output guardrails protect against prompt injection and sensitive data leakage.

### Technologies

| Layer | Technology |
|-------|-----------|
| Framework | Flask 3.x |
| LLM | OpenAI GPT-4o via LangChain (`temperature=0.3`, `max_tokens=800`) |
| Tracing | LangSmith (`@traceable` decorator) |
| Token counting | tiktoken `cl100k_base` |
| Guardrails | 16 input injection patterns + 6 output sensitive-data patterns |
| Config | python-dotenv |

### Guardrails

| Direction | Checks |
|-----------|--------|
| Input | Max 2000 chars, max 500 tokens, 16 prompt-injection regex patterns |
| Output | API keys (`sk-`, `AKIA`), Bearer tokens, credit card, SSN, system prompt leakage |

### Flow

```mermaid
flowchart LR
    Client([HTTP Client])
    App["Flask App\napp.py"]
    GI["Input Guardrails\nguardrails.py"]
    Chain["LangChain Chain\nllm.py"]
    GPT["OpenAI GPT-4o"]
    LS["LangSmith Tracing"]
    GO["Output Guardrails\nguardrails.py"]

    Client -->|POST /api/inference/| App
    App --> GI
    GI -->|char limit, token limit, injection check| Chain
    Chain -.->|traceable| LS
    Chain -->|system prompt + message| GPT
    GPT -->|raw response| Chain
    Chain --> GO
    GO -->|clean response| App
    App -->|200 / 400 / 422 / 503| Client
```

---

## 3. Semantic Search Blog

Semantic search system that crawls articles from the [dotgroup.com.br](https://dotgroup.com.br/blog) blog, generates embeddings locally with Ollama, and indexes them in a FAISS vector store using cosine similarity. Exposes a Flask REST API for similarity-based queries.

### Technologies

| Layer | Technology |
|-------|-----------|
| Framework | Flask |
| Web crawling | requests + BeautifulSoup4 + lxml |
| Embeddings | Ollama `nomic-embed-text` (dim 768, runs locally) |
| Vector store | FAISS `IndexFlatIP` + L2 normalization (cosine similarity) |
| Persistence | `blog_index.faiss` + `blog_meta.json` |
| Chunking | Sliding window — 900 chars, 120 chars overlap |

### Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/search` | Semantic search over indexed chunks |
| `GET` | `/stats` | Returns total number of indexed chunks |

### Indexing Flow

```mermaid
flowchart LR
    Blog(["dotgroup.com.br\n/blog"])
    Crawler["crawler.py\npagination + scraping"]
    Chunker["embeddings.py\nchunk_text"]
    Embed["embeddings.py\nOllama embed"]
    Store["vector_store.py\nFAISSStore.insert"]
    FAISS[("FAISS\nblog_index.faiss")]

    Blog -->|HTTP GET paginated| Crawler
    Crawler -->|BlogPost: url, title, content| Chunker
    Chunker -->|chunks of 900 chars| Embed
    Embed -->|list of vec768| Store
    Store -->|IndexFlatIP + L2 norm| FAISS
```

### Search Flow

```mermaid
flowchart LR
    Client([HTTP Client])
    App["Flask App\nmain.py"]
    Embed["embeddings.py\nOllama embed"]
    Store["vector_store.py\nFAISSStore.search"]
    FAISS[("FAISS\nblog_index.faiss")]

    Client -->|POST /search| App
    App --> Embed
    Embed -->|query vec768| Store
    Store --> FAISS
    FAISS -->|top-k cosine results| Store
    Store -->|score, url, title, chunk| App
    App -->|200 results| Client
```

---

## Getting Started

Each project has its own `requirements.txt` and `specs.md` with detailed setup instructions.

```
backend_ia/
├── library_fastapi/       # Virtual library REST API
├── chatbot_python/        # Stateless Python chatbot with guardrails
└── semantic_search_blog/  # Semantic search over Dots Digital Group blog
```
