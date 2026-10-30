import math
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories.book_repository import BookRepository
from ..schemas import ApiResponse, BookCreate, BookResponse, BookUpdate, PaginatedBooks

router = APIRouter(prefix="/books", tags=["books"])


def get_repo(db: Session = Depends(get_db)) -> BookRepository:
    return BookRepository(db)


@router.post("/", response_model=ApiResponse[BookResponse], status_code=201, summary="Cadastrar livro")
def create_book(book: BookCreate, repo: BookRepository = Depends(get_repo)) -> ApiResponse[BookResponse]:
    """
    Cadastra um novo livro na biblioteca virtual.

    - **title**: Título do livro (obrigatório)
    - **author**: Nome do autor (obrigatório)
    - **publication_date**: Data de publicação no formato YYYY-MM-DD (obrigatório)
    - **summary**: Resumo do livro (opcional)
    """
    db_book = repo.create(book)
    return ApiResponse(status_code=201, data=BookResponse.model_validate(db_book))


@router.get("/", response_model=ApiResponse[PaginatedBooks], summary="Consultar livros")
def list_books(
    title: str | None = Query(None, description="Filtrar por título (busca parcial)"),
    author: str | None = Query(None, description="Filtrar por autor (busca parcial)"),
    publication_date: date | None = Query(None, description="Filtrar por data de publicação exata (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(10, ge=1, le=100, description="Itens por página (máx. 100)"),
    repo: BookRepository = Depends(get_repo),
) -> ApiResponse[PaginatedBooks]:
    """
    Consulta livros ativos cadastrados na biblioteca virtual com paginação.

    - **title**: Filtra livros cujo título contenha o texto informado (parcial, case-insensitive).
    - **author**: Filtra livros cujo autor contenha o texto informado (parcial, case-insensitive).
    - **publication_date**: Filtra por data de publicação exata (YYYY-MM-DD).
    - Quando `title` e `author` são informados juntos, retorna livros que correspondam a **título OU autor**.
    - **page**: Página desejada (começa em 1).
    - **page_size**: Quantidade de itens por página (padrão 10, máximo 100).
    """
    rows, total = repo.list_active(
        title=title,
        author=author,
        publication_date=publication_date,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    paginated = PaginatedBooks(
        items=[BookResponse.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )
    return ApiResponse(status_code=200, data=paginated)


@router.get("/{book_id}", response_model=ApiResponse[BookResponse], summary="Buscar livro por ID")
def get_book(book_id: int, repo: BookRepository = Depends(get_repo)) -> ApiResponse[BookResponse]:
    """
    Retorna os detalhes de um livro ativo específico pelo seu ID.
    """
    book = repo.get_active_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return ApiResponse(status_code=200, data=BookResponse.model_validate(book))


@router.put("/{book_id}", response_model=ApiResponse[BookResponse], summary="Atualizar livro")
def update_book(
    book_id: int, payload: BookUpdate, repo: BookRepository = Depends(get_repo)
) -> ApiResponse[BookResponse]:
    """
    Atualiza parcialmente um livro ativo pelo seu ID.

    Apenas os campos informados no corpo da requisição serão alterados.
    Ao menos um campo deve ser fornecido.
    """
    book = repo.get_active_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Nenhum campo fornecido para atualização")

    updated = repo.update(book, updates)
    return ApiResponse(status_code=200, data=BookResponse.model_validate(updated))


@router.delete("/{book_id}", response_model=ApiResponse, status_code=200, summary="Remover livro (soft delete)")
def delete_book(book_id: int, repo: BookRepository = Depends(get_repo)) -> ApiResponse:
    """
    Desativa um livro pelo seu ID (soft delete).

    O livro permanece no banco de dados, mas não aparece mais nas consultas.
    """
    book = repo.get_active_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")

    repo.soft_delete(book)
    return ApiResponse(status_code=200, data=None)
