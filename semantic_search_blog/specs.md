# Semantic Search Blog — Especificações

## Objetivo
Sistema de busca semântica de documentos que rastreia o blog https://dotgroup.com.br/blog via web crawling, gera embeddings dos artigos e os indexa no FAISS. Expõe uma API REST para consultas semânticas por similaridade vetorial.

## Stack
| Componente | Tecnologia |
|------------|-----------|
| Framework web | Flask 3.x |
| Web crawling | requests + BeautifulSoup4 + lxml |
| Embeddings | Ollama `nomic-embed-text` (dim 768, local, sem custo) |
| Vector store | FAISS (faiss-cpu, local, sem Docker) |
| Chunking | Janela deslizante — 900 chars, overlap 120 chars |
| Config | python-dotenv |

## Estrutura de Arquivos
```
semantic_search_blog/
├── index_blog.py       — CLI para rodar o pipeline de indexação
├── requirements.txt
├── .env.example
├── specs.md
└── app/
    ├── __init__.py
    ├── main.py         — Flask: POST /search, GET /stats
    ├── crawler.py      — paginação + scraping dos posts
    ├── embeddings.py   — chunk_text() + embed() via Ollama (local)
    └── vector_store.py — FAISSStore (IndexFlatIP + L2 norm = cosine similarity)
```

## Fluxo de Indexação
```
crawl() → BlogPost {url, title, content}
    └─→ chunk_text(content)   → list[str]  (janelas de 900 chars)
    └─→ embed(chunks)         → list[vec768]
    └─→ FAISSStore.insert()   → blog_index.faiss + blog_meta.json
```

## Fluxo de Busca
```
query string
    └─→ embed([query])        → vec768
    └─→ FAISSStore.search()   → top-k hits por similaridade COSINE
    └─→ resposta JSON com score, url, title, chunk
```

## Endpoints
| Método | URL | Descrição |
|--------|-----|-----------|
| `POST` | `/search` | Busca semântica nos chunks indexados |
| `GET`  | `/stats` | Contagem de chunks no vector store |

**Request** `POST /search`
```json
{"query": "pesquisa sobre aprendizagem no brasil", "top_k": 5}
```

**Response 200**
```json
{
  "query": "pesquisa sobre aprendizagem no brasil",
  "results": [
    {
      "score": 0.9134,
      "url": "https://dotgroup.com.br/blog/pesquisa-maturidade-aprendizagem-brasil",
      "title": "Pesquisa Maturidade de Aprendizagem no Brasil",
      "chunk": "...",
      "chunk_index": 0
    }
  ]
}
```

## FAISS
- Índice salvo em `blog_index.faiss` + metadados em `blog_meta.json` (raiz do projeto)
- Sem servidor, sem Docker — funciona nativamente no Windows
- Caminhos configuráveis via `FAISS_INDEX_PATH` e `FAISS_META_PATH` no `.env`

## Como executar

```bash
cd semantic_search_blog
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Pré-requisito: Ollama rodando com o modelo baixado
# https://ollama.com/download
ollama pull nomic-embed-text

# 1. Indexar o blog
python index_blog.py

# Testar com apenas 5 posts
python index_blog.py --max-posts 5

# Re-indexar do zero
python index_blog.py --reset

# 2. Subir a API
flask --app app.main run --debug
```

## Exemplo de busca
```bash
curl -X POST http://127.0.0.1:5000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "transformação digital nas empresas", "top_k": 3}'
```
