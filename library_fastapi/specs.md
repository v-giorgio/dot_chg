# Biblioteca Virtual — Especificação da API

## Visão Geral

API REST para cadastro e consulta de livros em uma biblioteca virtual, construída com **FastAPI**, banco de dados **SQLite** via SQLAlchemy ORM e testes unitários com **pytest**.

---

## Stack

| Componente | Tecnologia |
|---|---|
| Framework | FastAPI |
| Banco de dados | SQLite (via SQLAlchemy) |
| Validação | Pydantic v2 |
| Servidor | Uvicorn |
| Testes | pytest + httpx (TestClient) |

---

## Como executar

```bash
# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor
uvicorn app.main:app --reload

# Executar testes
python -m pytest tests/ -v
```

Documentação interativa disponível em `http://localhost:8000/docs` (Swagger UI).

---

## Estrutura do projeto

```
backend_ia/
├── app/
│   ├── main.py          # Instância FastAPI e registro de routers
│   ├── database.py      # Engine SQLite, SessionLocal e Base declarativa
│   ├── models.py        # Modelo ORM Book
│   ├── schemas.py       # Schemas Pydantic (entrada, saída, paginação)
│   └── routers/
│       └── books.py     # Endpoints de livros
├── tests/
│   └── test_books.py    # Suite de testes unitários
└── requirements.txt
```

---

## Iteração 1 — Implementação inicial

### Modelo de dados

**Tabela `books`**

| Coluna | Tipo | Restrições |
|---|---|---|
| `id` | INTEGER | PK, auto-increment, index |
| `title` | VARCHAR(255) | NOT NULL, index |
| `author` | VARCHAR(255) | NOT NULL, index |
| `publication_date` | DATE | NOT NULL |
| `summary` | TEXT | nullable |

### Endpoints

#### `GET /`
Health check. Confirma que a API está no ar.

**Resposta 200**
```json
{ "status": "ok", "message": "Biblioteca Virtual API" }
```

---

#### `POST /books/`
Cadastra um novo livro.

**Body**
```json
{
  "title": "Dom Casmurro",
  "author": "Machado de Assis",
  "publication_date": "1899-01-01",
  "summary": "Capitu traiu ou não traiu?"
}
```

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `title` | string | sim | 1–255 caracteres |
| `author` | string | sim | 1–255 caracteres |
| `publication_date` | date | sim | formato `YYYY-MM-DD` |
| `summary` | string | não | sem restrição de tamanho |

**Resposta 201**
```json
{
  "id": 1,
  "title": "Dom Casmurro",
  "author": "Machado de Assis",
  "publication_date": "1899-01-01",
  "summary": "Capitu traiu ou não traiu?"
}
```

---

#### `GET /books/`
Lista todos os livros com filtros opcionais por `title` e `author`.

**Query params**

| Param | Tipo | Descrição |
|---|---|---|
| `title` | string | Busca parcial, case-insensitive |
| `author` | string | Busca parcial, case-insensitive |

Quando ambos são informados, retorna livros que correspondam a **título OU autor**.

**Resposta 200** — lista de livros (array JSON)

---

#### `GET /books/{id}`
Retorna um livro específico pelo ID.

**Resposta 200** — objeto do livro  
**Resposta 404** — `{ "detail": "Livro não encontrado" }`

---

### Testes — Iteração 1 (18 casos)

| Classe | Casos |
|---|---|
| `TestCreateBook` | Criação com sucesso, sem resumo, campos obrigatórios ausentes, data inválida, título vazio |
| `TestListBooks` | Listagem vazia, listagem geral, busca por título (exata/parcial), busca por autor, busca combinada título+autor, sem resultados |
| `TestGetBook` | Busca por ID com sucesso, ID inexistente, ID inválido (string) |
| `TestHealthCheck` | Health check raiz |

---

## Iteração 2 — Improvements

### Alterações no modelo de dados

**Nova coluna em `books`**

| Coluna | Tipo | Restrições | Default |
|---|---|---|---|
| `is_active` | BOOLEAN | NOT NULL | `True` |

Usada para implementar soft delete: livros inativados permanecem no banco mas são omitidos de todas as consultas e operações.

---

### Alterações em `GET /books/`

#### Paginação

A resposta deixou de ser um array simples e passou a retornar um objeto paginado.

**Novos query params**

| Param | Tipo | Default | Regras |
|---|---|---|---|
| `page` | integer | `1` | mínimo 1 |
| `page_size` | integer | `10` | mínimo 1, máximo 100 |

**Novo formato de resposta 200**
```json
{
  "items": [ /* lista de livros */ ],
  "total": 42,
  "page": 1,
  "page_size": 10,
  "pages": 5
}
```

| Campo | Descrição |
|---|---|
| `items` | Livros da página atual |
| `total` | Total de livros ativos que correspondem ao filtro |
| `page` | Página atual |
| `page_size` | Itens por página |
| `pages` | Total de páginas (`ceil(total / page_size)`, `0` se não há itens) |

#### Novo filtro: `publication_date`

| Param | Tipo | Descrição |
|---|---|---|
| `publication_date` | date (`YYYY-MM-DD`) | Correspondência exata pela data de publicação |

Pode ser combinado com `title` e `author`. Todos os filtros são aplicados com `AND` — exceto `title` e `author` entre si, que continuam com `OR`.

#### Comportamento de `is_active`

O endpoint agora filtra automaticamente apenas livros com `is_active = True`. Livros inativados não aparecem nos resultados nem no `total`.

---

### Novo endpoint: `PUT /books/{id}`

Atualização parcial de um livro ativo. Apenas os campos presentes no body são alterados.

**Body** — todos os campos são opcionais, mas ao menos um deve ser fornecido.
```json
{
  "title": "Novo Título",
  "author": "Novo Autor",
  "publication_date": "2000-01-01",
  "summary": "Novo resumo."
}
```

| Campo | Tipo | Regras |
|---|---|---|
| `title` | string | 1–255 caracteres |
| `author` | string | 1–255 caracteres |
| `publication_date` | date | formato `YYYY-MM-DD` |
| `summary` | string | sem restrição |

**Resposta 200** — objeto atualizado do livro  
**Resposta 404** — livro não encontrado ou inativo  
**Resposta 422** — body vazio ou campo com valor inválido

---

### Novo endpoint: `DELETE /books/{id}`

Soft delete: seta `is_active = False` no registro. O livro permanece no banco de dados mas deixa de aparecer em qualquer consulta.

**Resposta 204** — sem corpo  
**Resposta 404** — livro não encontrado ou já inativo (idempotência negativa: segundo DELETE retorna 404)

#### Efeitos do soft delete sobre outros endpoints

| Endpoint | Comportamento após DELETE |
|---|---|
| `GET /books/` | Livro excluído da listagem e do `total` |
| `GET /books/{id}` | Retorna 404 |
| `PUT /books/{id}` | Retorna 404 |
| `DELETE /books/{id}` | Retorna 404 |

---

### Testes — Iteração 2 (26 novos casos)

| Classe | Casos |
|---|---|
| `TestListBooks` (3 novos) | Filtro por data exata, filtro sem resultado, formato de data inválido |
| `TestListBooksPagination` (8 casos) | Shape da resposta, defaults, primeira página, segunda página, página além do total, página inválida (`page=0`), page_size além do máximo, `pages=0` quando vazio |
| `TestUpdateBook` (8 casos) | Atualização de título, autor, data, resumo, múltiplos campos; body vazio retorna 422; livro inexistente; título vazio retorna 422 |
| `TestDeleteBook` (7 casos) | Soft delete com sucesso (204); GET retorna 404 após delete; livro excluído da listagem; `total` decrementado; livro inexistente; segundo DELETE retorna 404; PUT retorna 404 após delete |

**Total acumulado: 44 testes, todos passando.**

---

## Iteração 3 — Padronização de respostas e correções

### Envelope padrão `ApiResponse[T]`

Todas as rotas passaram a retornar um envelope genérico consistente no corpo da resposta.

**Novo schema em `schemas.py`**
```python
class ApiResponse(BaseModel, Generic[T]):
    status_code: int   # espelha o HTTP status code da resposta
    data: T | None     # payload tipado; None em rotas sem corpo (ex.: DELETE)
```

**Formato de todas as respostas de sucesso**
```json
{
  "status_code": 200,
  "data": { ... }
}
```

**Tabela de tipos por rota**

| Método | Rota | `response_model` | `data` |
|---|---|---|---|
| `GET` | `/` | `ApiResponse[HealthResponse]` | `{"status": "ok", "message": "..."}` |
| `POST` | `/books/` | `ApiResponse[BookResponse]` | objeto do livro criado |
| `GET` | `/books/` | `ApiResponse[PaginatedBooks]` | objeto paginado |
| `GET` | `/books/{id}` | `ApiResponse[BookResponse]` | objeto do livro |
| `PUT` | `/books/{id}` | `ApiResponse[BookResponse]` | objeto atualizado |
| `DELETE` | `/books/{id}` | `ApiResponse` | `null` |

> Respostas de erro (4xx/422) permanecem no formato padrão do FastAPI: `{"detail": "..."}`.

---

### Correção: `Book.is_active = False` (tipo)

**Causa:** A coluna `is_active` era declarada com `Column(Boolean)` (forma legada), sem anotação de tipo no atributo Python, o que causava erro de tipo na atribuição direta.

**Solução:** Migração para a API declarativa moderna do SQLAlchemy 2.x com `Mapped` e `mapped_column` em todas as colunas do modelo.

```python
# antes
is_active = Column(Boolean, nullable=False, default=True)

# depois
is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

Com `Mapped[bool]`, o atributo é corretamente tipado como `bool` e `book.is_active = False` resolve sem erro. As demais colunas também foram migradas para o mesmo padrão.

Adicionalmente, os filtros `== True` foram substituídos por `.is_(True)` para evitar ambiguidade com o operador de comparação Python.

---

### Correção: atribuição de `items` em `PaginatedBooks`

**Causa:** `query.all()` retorna `list[Book]` (objetos ORM), mas `PaginatedBooks.items` espera `list[BookResponse]` (modelos Pydantic).

**Solução:** Conversão explícita com `model_validate` antes da atribuição.

```python
# antes (erro de tipo)
items=items

# depois (correto)
items=[BookResponse.model_validate(row) for row in rows]
```

`BookResponse` já possui `model_config = {"from_attributes": True}`, então `model_validate` aceita objetos ORM diretamente.

---

### Alteração: DELETE `204 → 200`

O endpoint `DELETE /books/{id}` passou de HTTP `204 No Content` para `200 OK` com corpo `{"status_code": 200, "data": null}`, alinhado ao padrão `ApiResponse` adotado nas demais rotas.

---

### Novo schema: `HealthResponse`

```python
class HealthResponse(BaseModel):
    status: str
    message: str
```

Usado como tipo de `data` na resposta do `GET /`.

---

### Impacto nos testes

Todos os testes foram atualizados para consumir o novo envelope:
- Acesso ao payload: `response.json()["data"]`
- Verificação do código no corpo: `response.json()["status_code"]`
- `TestDeleteBook`: `status_code 204 → 200`, verificação de `data == null`
- `TestHealthCheck`: verificação via `data["status"]`
- Helper `create_book()`: atualizado para retornar `response.json()["data"]` diretamente

**Total acumulado: 44 testes, todos passando.**

---

## Iteração 4 — Repository pattern, separação de testes e padrões Python

### 1. Repository pattern

Toda a lógica de acesso ao banco foi isolada em `app/repositories/book_repository.py`. O router não executa mais queries diretamente — ele delega ao repositório via injeção de dependência.

**Novo módulo:** `app/repositories/book_repository.py`

```
BookRepository
├── create(data: BookCreate) → Book
├── get_active_by_id(book_id: int) → Book | None
├── list_active(*, title, author, publication_date, offset, limit) → tuple[list[Book], int]
├── update(book: Book, updates: dict) → Book
└── soft_delete(book: Book) → None
```

**Dependência injetada no router:**
```python
def get_repo(db: Session = Depends(get_db)) -> BookRepository:
    return BookRepository(db)
```

Cada endpoint recebe `repo: BookRepository = Depends(get_repo)` e não importa mais `Session` diretamente.

---

### 2. Separação de testes

```
tests/
├── conftest.py                         # Fixtures compartilhadas
├── unit/
│   └── test_schemas.py                 # Validação de schemas Pydantic (sem DB)
└── integration/
    ├── test_book_repository.py         # Repository com SQLite in-memory
    └── test_books_api.py               # API completa com TestClient
```

#### `tests/conftest.py` — fixtures compartilhadas

| Fixture | Descrição |
|---|---|
| `db_engine` | SQLite in-memory com `StaticPool`; cria/derruba tabelas por teste |
| `db_session` | Sessão SQLAlchemy sobre `db_engine` |
| `client` | `TestClient` com override de `get_db` apontando para `db_engine` |
| `sample_book` | Payload de livro de exemplo |

**`StaticPool`** garante que todas as conexões da sessão de teste usem o mesmo banco in-memory, evitando o problema de cada conexão enxergar um banco diferente.

#### Testes unitários (`tests/unit/`) — `@pytest.mark.unit`

Testam regras de validação dos schemas Pydantic em puro Python — sem banco, sem HTTP.

| Classe | O que testa |
|---|---|
| `TestBookCreateSchema` | Campos obrigatórios, limites de tamanho, formato de data, summary opcional |
| `TestBookUpdateSchema` | Body vazio é válido no schema; campos opcionais; limites |
| `TestBookResponseSchema` | Campos obrigatórios na resposta |
| `TestApiResponseSchema` | Envelope genérico com e sem `data` |

#### Testes de integração (`tests/integration/`) — `@pytest.mark.integration`

**`test_book_repository.py`** — testa o repositório diretamente via `db_session`:

| Classe | Cenários |
|---|---|
| `TestBookRepositoryCreate` | Persistência de campos, `is_active=True` padrão, com summary |
| `TestBookRepositoryGetActiveById` | Encontrado, não encontrado, inativo retorna `None` |
| `TestBookRepositoryListActive` | Filtros (título, autor, data, união), paginação, total, excluir inativos |
| `TestBookRepositoryUpdate` | Campo único, múltiplos campos, preservação de campos não alterados |
| `TestBookRepositorySoftDelete` | `is_active=False`, excluído de `get_active` e `list_active` |

**`test_books_api.py`** — testa a API completa via `TestClient` (mesmos cenários das iterações anteriores).

---

### 3. Padrões Python aplicados

**`pyproject.toml`** — configuração centralizada substituindo flags avulsas:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: fast isolated tests with no external dependencies",
    "integration: tests that require a real database or HTTP client",
]
```

**Execução por camada:**
```bash
pytest tests/unit/          # só unitários (sem DB, rápidos)
pytest tests/integration/   # só integração
pytest -m unit              # por marker
pytest -m integration
pytest                      # suite completa
```

**Total acumulado: 88 testes, todos passando.**
- 24 unitários (schemas Pydantic)
- 20 integração — repositório
- 44 integração — API HTTP

---

## Iteração 5 — Postman Collection

Arquivo `biblioteca_virtual.postman_collection.json` gerado na raiz de `library_fastapi/` para importação direta no Postman.

### Variáveis de coleção

| Variável | Valor padrão | Descrição |
|---|---|---|
| `base_url` | `http://localhost:8000` | URL base da API |
| `book_id` | `1` | ID usado nos requests de GET/PUT/DELETE por ID |

### Cobertura

| Rota | Método | Status cobertos |
|---|---|---|
| `/` | GET | 200, 500 |
| `/books/` | POST | 201, 422 (campo ausente, title vazio, data inválida), 500 |
| `/books/` | GET | 200 (com resultados, vazia, filtro por título, segunda página), 422 (page=0, page_size=101, publication_date inválida), 500 |
| `/books/{id}` | GET | 200, 404, 422 (ID não numérico), 500 |
| `/books/{id}` | PUT | 200, 404, 422 (body vazio, title vazio, ID não numérico), 500 |
| `/books/{id}` | DELETE | 200, 404, 422 (ID não numérico), 500 |

Cada request contém exemplos de resposta salvos (response examples) para todos os status listados acima, incluindo o body exato retornado pela API.
