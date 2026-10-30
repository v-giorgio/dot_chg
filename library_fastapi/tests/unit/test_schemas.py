"""
Unit tests for Pydantic schemas.

These tests exercise field validation rules in complete isolation — no database,
no HTTP client, no I/O. Fast and deterministic.
"""

import pytest
from datetime import date
from pydantic import ValidationError

from library_fastapi.app.schemas import ApiResponse, BookCreate, BookResponse, BookUpdate


@pytest.mark.unit
class TestBookCreateSchema:
    def test_valid_data_passes_validation(self):
        book = BookCreate(
            title="Dom Casmurro",
            author="Machado de Assis",
            publication_date=date(1899, 1, 1),
            summary="Romance brasileiro.",
        )
        assert book.title == "Dom Casmurro"
        assert book.author == "Machado de Assis"
        assert book.publication_date == date(1899, 1, 1)
        assert book.summary == "Romance brasileiro."

    def test_summary_is_optional(self):
        book = BookCreate(
            title="Dom Casmurro",
            author="Machado de Assis",
            publication_date=date(1899, 1, 1),
            summary=None,
        )
        assert book.summary is None

    def test_missing_title_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookCreate(
                author="Autor",
                publication_date=date(2000, 1, 1),
                summary="Resumo válido para teste.",
            )

    def test_missing_author_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookCreate(
                title="Título",
                publication_date=date(2000, 1, 1),
                summary="Resumo válido para teste.",
            )

    def test_missing_publication_date_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookCreate(
                title="Título",
                author="Autor",
                summary="Resumo válido para teste.",
            )

    def test_empty_title_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookCreate(title="", author="Autor", publication_date=date(2000, 1, 1))

    def test_empty_author_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookCreate(title="Título", author="", publication_date=date(2000, 1, 1))

    def test_title_exceeding_max_length_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookCreate(title="x" * 256, author="Autor", publication_date=date(2000, 1, 1))

    def test_author_exceeding_max_length_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookCreate(title="Título", author="x" * 256, publication_date=date(2000, 1, 1))

    def test_title_at_max_length_is_valid(self):
        book = BookCreate(
            title="x" * 255,
            author="Autor",
            publication_date=date(2000, 1, 1),
            summary="Resumo válido.",
        )
        assert len(book.title) == 255

    def test_invalid_date_string_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookCreate(title="Título", author="Autor", publication_date="31/12/1999")


@pytest.mark.unit
class TestBookUpdateSchema:
    def test_empty_body_is_valid(self):
        update = BookUpdate()
        assert update.title is None
        assert update.author is None
        assert update.publication_date is None
        assert update.summary is None

    def test_partial_update_with_title_only(self):
        update = BookUpdate(title="Novo Título")
        assert update.title == "Novo Título"
        assert update.author is None
        assert update.summary is None

    def test_partial_update_with_multiple_fields(self):
        update = BookUpdate(title="Título", author="Autor", summary="Novo resumo.")
        assert update.title == "Título"
        assert update.author == "Autor"
        assert update.summary == "Novo resumo."

    def test_empty_title_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookUpdate(title="")

    def test_empty_author_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookUpdate(author="")

    def test_title_exceeding_max_length_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookUpdate(title="x" * 256)

    def test_invalid_date_format_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookUpdate(publication_date="01/01/2000")


@pytest.mark.unit
class TestBookResponseSchema:
    def test_valid_response_from_dict(self):
        response = BookResponse(
            id=1,
            title="Dom Casmurro",
            author="Machado de Assis",
            publication_date=date(1899, 1, 1),
            summary="Romance realista brasileiro.",
        )
        assert response.id == 1
        assert response.summary == "Romance realista brasileiro."

    def test_valid_response_without_summary(self):
        response = BookResponse(
            id=2,
            title="Duna",
            author="Frank Herbert",
            publication_date=date(1965, 8, 1),
            summary=None,
        )
        assert response.summary is None

    def test_missing_id_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BookResponse(
                title="Título",
                author="Autor",
                publication_date=date(2000, 1, 1),
                summary="Resumo válido.",
            )


@pytest.mark.unit
class TestApiResponseSchema:
    def test_response_with_data(self):
        response = ApiResponse(status_code=200, data={"key": "value"})
        assert response.status_code == 200
        assert response.data == {"key": "value"}

    def test_response_without_data_defaults_to_none(self):
        response = ApiResponse(status_code=200)
        assert response.data is None

    def test_missing_status_code_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ApiResponse()

    def test_delete_response_shape(self):
        response = ApiResponse(status_code=200, data=None)
        assert response.status_code == 200
        assert response.data is None
