from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import Book
from ..schemas import BookCreate


class BookRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: BookCreate) -> Book:
        book = Book(**data.model_dump())
        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)
        return book

    def get_active_by_id(self, book_id: int) -> Book | None:
        return (
            self.db.query(Book)
            .filter(Book.id == book_id, Book.is_active.is_(True))
            .first()
        )

    def list_active(
        self,
        *,
        title: str | None = None,
        author: str | None = None,
        publication_date: date | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[list[Book], int]:
        query = self.db.query(Book).filter(Book.is_active.is_(True))

        if title and author:
            query = query.filter(
                or_(Book.title.ilike(f"%{title}%"), Book.author.ilike(f"%{author}%"))
            )
        elif title:
            query = query.filter(Book.title.ilike(f"%{title}%"))
        elif author:
            query = query.filter(Book.author.ilike(f"%{author}%"))

        if publication_date:
            query = query.filter(Book.publication_date == publication_date)

        total = query.count()
        items = query.offset(offset).limit(limit).all()
        return items, total

    def update(self, book: Book, updates: dict) -> Book:
        for field, value in updates.items():
            setattr(book, field, value)
        self.db.commit()
        self.db.refresh(book)
        return book

    def soft_delete(self, book: Book) -> None:
        book.is_active = False
        self.db.commit()
