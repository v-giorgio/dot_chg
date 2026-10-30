"""
Integration tests for BookRepository.

Each test gets a fresh in-memory SQLite database via the db_session fixture.
Tests exercise real SQL queries without going through the HTTP layer.
"""

import pytest
from datetime import date

from library_fastapi.app.repositories.book_repository import BookRepository
from library_fastapi.app.schemas import BookCreate


def _make_book(
    db_session,
    title="Livro Teste",
    author="Autor Teste",
    pub_date=date(2000, 1, 1),
    summary: str | None = None,
):
    repo = BookRepository(db_session)
    return repo.create(
        BookCreate(title=title, author=author, publication_date=pub_date, summary=summary)
    )


@pytest.mark.integration
class TestBookRepositoryCreate:
    def test_create_persists_book_with_correct_fields(self, db_session):
        repo = BookRepository(db_session)
        data = BookCreate(
            title="Duna",
            author="Frank Herbert",
            publication_date=date(1965, 8, 1),
            summary="Épico de ficção científica ambientado no planeta Arrakis.",
        )

        book = repo.create(data)

        assert book.id is not None
        assert book.title == "Duna"
        assert book.author == "Frank Herbert"
        assert book.publication_date == date(1965, 8, 1)
        assert book.summary == "Épico de ficção científica ambientado no planeta Arrakis."

    def test_create_sets_is_active_true_by_default(self, db_session):
        book = _make_book(db_session, summary="Resumo do livro.")
        assert book.is_active is True

    def test_create_with_summary(self, db_session):
        repo = BookRepository(db_session)
        data = BookCreate(
            title="Título",
            author="Autor",
            publication_date=date(2000, 1, 1),
            summary="Resumo do livro.",
        )
        book = repo.create(data)
        assert book.summary == "Resumo do livro."


@pytest.mark.integration
class TestBookRepositoryGetActiveById:
    def test_returns_book_when_found(self, db_session):
        created = _make_book(db_session, summary="Resumo do livro.")
        repo = BookRepository(db_session)

        result = repo.get_active_by_id(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.summary == "Resumo do livro."

    def test_returns_none_when_book_not_found(self, db_session):
        repo = BookRepository(db_session)
        assert repo.get_active_by_id(9999) is None

    def test_returns_none_for_inactive_book(self, db_session):
        created = _make_book(db_session, summary="Resumo.")
        repo = BookRepository(db_session)
        repo.soft_delete(created)

        result = repo.get_active_by_id(created.id)

        assert result is None


@pytest.mark.integration
class TestBookRepositoryListActive:
    def test_returns_empty_when_no_books(self, db_session):
        repo = BookRepository(db_session)
        items, total = repo.list_active()
        assert items == []
        assert total == 0

    def test_returns_only_active_books(self, db_session):
        active = _make_book(db_session, title="Ativo", summary="Resumo ativo.")
        inactive = _make_book(db_session, title="Inativo", summary="Resumo inativo.")
        repo = BookRepository(db_session)
        repo.soft_delete(inactive)

        items, total = repo.list_active()

        assert total == 1
        assert items[0].id == active.id

    def test_filter_by_title_partial_case_insensitive(self, db_session):
        _make_book(db_session, title="Dom Casmurro", summary="Romance realista.")
        _make_book(db_session, title="Duna", summary="Ficção científica.")
        repo = BookRepository(db_session)

        items, total = repo.list_active(title="dom")

        assert total == 1
        assert items[0].title == "Dom Casmurro"

    def test_filter_by_author_partial(self, db_session):
        _make_book(db_session, author="Machado de Assis", summary="Obra brasileira.")
        _make_book(db_session, author="Frank Herbert", summary="Obra americana.")
        repo = BookRepository(db_session)

        items, total = repo.list_active(author="Machado")

        assert total == 1
        assert items[0].author == "Machado de Assis"

    def test_filter_by_title_and_author_returns_union(self, db_session):
        _make_book(db_session, title="Dom Casmurro", author="Machado de Assis", summary="Romance.")
        _make_book(db_session, title="Duna", author="Frank Herbert", summary="Sci-fi.")
        _make_book(db_session, title="Fundação", author="Isaac Asimov", summary="Clássico.")
        repo = BookRepository(db_session)

        items, total = repo.list_active(title="Dom", author="Herbert")

        assert total == 2

    def test_filter_by_publication_date_exact(self, db_session):
        _make_book(db_session, title="Livro A", pub_date=date(1899, 1, 1), summary="Séc. XIX.")
        _make_book(db_session, title="Livro B", pub_date=date(1965, 8, 1), summary="Séc. XX.")
        repo = BookRepository(db_session)

        items, total = repo.list_active(publication_date=date(1899, 1, 1))

        assert total == 1
        assert items[0].title == "Livro A"

    def test_pagination_offset_and_limit(self, db_session):
        for i in range(5):
            _make_book(db_session, title=f"Livro {i:02d}", summary=f"Resumo {i}.")
        repo = BookRepository(db_session)

        items, total = repo.list_active(offset=0, limit=2)
        assert len(items) == 2
        assert total == 5

        items_p2, _ = repo.list_active(offset=2, limit=2)
        assert len(items_p2) == 2
        assert items_p2[0].id != items[0].id

    def test_returns_correct_total_with_filter(self, db_session):
        _make_book(db_session, title="Dom Casmurro", summary="Clássico brasileiro.")
        _make_book(db_session, title="Duna", summary="Ficção científica.")
        repo = BookRepository(db_session)

        _, total = repo.list_active(title="duna")

        assert total == 1


@pytest.mark.integration
class TestBookRepositoryUpdate:
    def test_update_single_field(self, db_session):
        created = _make_book(db_session, title="Título Original", summary="Resumo original.")
        repo = BookRepository(db_session)

        updated = repo.update(created, {"title": "Título Atualizado"})

        assert updated.title == "Título Atualizado"

    def test_update_preserves_unchanged_fields(self, db_session):
        created = _make_book(db_session, title="Título", author="Autor Original", summary="Resumo.")
        repo = BookRepository(db_session)

        updated = repo.update(created, {"title": "Novo Título"})

        assert updated.author == "Autor Original"

    def test_update_multiple_fields(self, db_session):
        created = _make_book(db_session, summary="Resumo original.")
        repo = BookRepository(db_session)

        updated = repo.update(created, {"title": "Novo", "author": "Novo Autor"})

        assert updated.title == "Novo"
        assert updated.author == "Novo Autor"


@pytest.mark.integration
class TestBookRepositorySoftDelete:
    def test_soft_delete_sets_is_active_false(self, db_session):
        created = _make_book(db_session, summary="Resumo.")
        repo = BookRepository(db_session)

        repo.soft_delete(created)

        assert created.is_active is False

    def test_soft_deleted_book_not_returned_by_get_active(self, db_session):
        created = _make_book(db_session, summary="Resumo.")
        repo = BookRepository(db_session)
        repo.soft_delete(created)

        result = repo.get_active_by_id(created.id)

        assert result is None

    def test_soft_deleted_book_excluded_from_list(self, db_session):
        active = _make_book(db_session, title="Ativo", summary="Resumo ativo.")
        deleted = _make_book(db_session, title="Deletado", summary="Resumo deletado.")
        repo = BookRepository(db_session)
        repo.soft_delete(deleted)

        items, total = repo.list_active()

        assert total == 1
        assert items[0].id == active.id
