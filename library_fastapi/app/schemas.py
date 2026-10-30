from datetime import date
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    status_code: int
    data: T | None = None


class HealthResponse(BaseModel):
    status: str
    message: str


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Título do livro")
    author: str = Field(..., min_length=1, max_length=255, description="Nome do autor")
    publication_date: date = Field(..., description="Data de publicação (YYYY-MM-DD)")
    summary: str | None = Field(None, description="Resumo do livro")


class BookUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255, description="Título do livro")
    author: str | None = Field(None, min_length=1, max_length=255, description="Nome do autor")
    publication_date: date | None = Field(None, description="Data de publicação (YYYY-MM-DD)")
    summary: str | None = Field(None, description="Resumo do livro")


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    publication_date: date
    summary: str | None

    model_config = {"from_attributes": True}


class PaginatedBooks(BaseModel):
    items: list[BookResponse]
    total: int
    page: int
    page_size: int
    pages: int
