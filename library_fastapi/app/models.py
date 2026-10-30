from datetime import date
from sqlalchemy import Boolean, String, Date, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[str] = mapped_column(String(255), index=True)
    publication_date: Mapped[date] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
