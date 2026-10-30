"""
Integration tests for the books API.

Tests go through the full HTTP stack (FastAPI router → repository → SQLite).
Each test gets a fresh in-memory database via the shared client fixture in conftest.py.
"""

import pytest


def create_book(client, title, author, date="2000-01-01", summary=None):
    payload = {"title": title, "author": author, "publication_date": date}
    if summary:
        payload["summary"] = summary
    return client.post("/books/", json=payload).json()["data"]


@pytest.mark.integration
class TestCreateBook:
    def test_create_book_success(self, client, sample_book):
        response = client.post("/books/", json=sample_book)
        assert response.status_code == 201
        body = response.json()
        assert body["status_code"] == 201
        data = body["data"]
        assert data["title"] == sample_book["title"]
        assert data["author"] == sample_book["author"]
        assert data["publication_date"] == sample_book["publication_date"]
        assert data["summary"] == sample_book["summary"]
        assert "id" in data

    def test_create_book_without_summary(self, client):
        book = {"title": "Duna", "author": "Frank Herbert", "publication_date": "1965-08-01"}
        response = client.post("/books/", json=book)
        assert response.status_code == 201
        assert response.json()["data"]["summary"] is None

    def test_create_book_missing_title(self, client, sample_book):
        del sample_book["title"]
        assert client.post("/books/", json=sample_book).status_code == 422

    def test_create_book_missing_author(self, client, sample_book):
        del sample_book["author"]
        assert client.post("/books/", json=sample_book).status_code == 422

    def test_create_book_missing_publication_date(self, client, sample_book):
        del sample_book["publication_date"]
        assert client.post("/books/", json=sample_book).status_code == 422

    def test_create_book_invalid_date_format(self, client, sample_book):
        sample_book["publication_date"] = "29/07/1954"
        assert client.post("/books/", json=sample_book).status_code == 422

    def test_create_book_empty_title(self, client, sample_book):
        sample_book["title"] = ""
        assert client.post("/books/", json=sample_book).status_code == 422


@pytest.mark.integration
class TestListBooks:
    def test_list_all_books_empty(self, client):
        response = client.get("/books/")
        assert response.status_code == 200
        body = response.json()
        assert body["status_code"] == 200
        assert body["data"]["items"] == []
        assert body["data"]["total"] == 0

    def test_list_all_books(self, client):
        create_book(client, "Livro A", "Autor X")
        create_book(client, "Livro B", "Autor Y")
        data = client.get("/books/").json()["data"]
        assert len(data["items"]) == 2
        assert data["total"] == 2

    def test_search_by_title_exact(self, client):
        create_book(client, "Dom Casmurro", "Machado de Assis")
        create_book(client, "Memórias Póstumas", "Machado de Assis")
        items = client.get("/books/?title=Dom Casmurro").json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["title"] == "Dom Casmurro"

    def test_search_by_title_partial_case_insensitive(self, client):
        create_book(client, "Dom Casmurro", "Machado de Assis")
        create_book(client, "Memórias Póstumas", "Machado de Assis")
        assert len(client.get("/books/?title=dom").json()["data"]["items"]) == 1

    def test_search_by_author(self, client):
        create_book(client, "Dom Casmurro", "Machado de Assis")
        create_book(client, "Duna", "Frank Herbert")
        items = client.get("/books/?author=Machado").json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["author"] == "Machado de Assis"

    def test_search_by_title_and_author_returns_union(self, client):
        create_book(client, "Dom Casmurro", "Machado de Assis")
        create_book(client, "Duna", "Frank Herbert")
        create_book(client, "Fundação", "Isaac Asimov")
        assert len(client.get("/books/?title=Dom&author=Herbert").json()["data"]["items"]) == 2

    def test_search_no_results(self, client):
        create_book(client, "Dom Casmurro", "Machado de Assis")
        assert client.get("/books/?title=Inexistente").json()["data"]["items"] == []

    def test_filter_by_publication_date(self, client):
        create_book(client, "Dom Casmurro", "Machado de Assis", date="1899-01-01")
        create_book(client, "Duna", "Frank Herbert", date="1965-08-01")
        items = client.get("/books/?publication_date=1899-01-01").json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["title"] == "Dom Casmurro"

    def test_filter_by_publication_date_no_match(self, client):
        create_book(client, "Dom Casmurro", "Machado de Assis", date="1899-01-01")
        assert client.get("/books/?publication_date=2000-01-01").json()["data"]["items"] == []

    def test_filter_by_publication_date_invalid_format(self, client):
        assert client.get("/books/?publication_date=01-01-1899").status_code == 422


@pytest.mark.integration
class TestListBooksPagination:
    def test_pagination_response_shape(self, client):
        create_book(client, "Livro A", "Autor A")
        data = client.get("/books/").json()["data"]
        for key in ("items", "total", "page", "page_size", "pages"):
            assert key in data

    def test_pagination_defaults(self, client):
        for i in range(5):
            create_book(client, f"Livro {i}", "Autor")
        data = client.get("/books/").json()["data"]
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total"] == 5
        assert data["pages"] == 1
        assert len(data["items"]) == 5

    def test_pagination_first_page(self, client):
        for i in range(15):
            create_book(client, f"Livro {i:02d}", "Autor")
        data = client.get("/books/?page=1&page_size=10").json()["data"]
        assert data["total"] == 15
        assert data["pages"] == 2
        assert len(data["items"]) == 10

    def test_pagination_second_page(self, client):
        for i in range(15):
            create_book(client, f"Livro {i:02d}", "Autor")
        data = client.get("/books/?page=2&page_size=10").json()["data"]
        assert len(data["items"]) == 5
        assert data["page"] == 2

    def test_pagination_page_beyond_total_returns_empty(self, client):
        create_book(client, "Único Livro", "Autor")
        data = client.get("/books/?page=99&page_size=10").json()["data"]
        assert data["items"] == []
        assert data["total"] == 1

    def test_pagination_invalid_page_returns_422(self, client):
        assert client.get("/books/?page=0").status_code == 422

    def test_pagination_page_size_exceeds_max_returns_422(self, client):
        assert client.get("/books/?page_size=101").status_code == 422

    def test_pagination_empty_db_pages_is_zero(self, client):
        assert client.get("/books/").json()["data"]["pages"] == 0


@pytest.mark.integration
class TestGetBook:
    def test_get_book_success(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        body = client.get(f"/books/{created['id']}").json()
        assert body["status_code"] == 200
        assert body["data"]["id"] == created["id"]
        assert body["data"]["title"] == sample_book["title"]

    def test_get_book_not_found_returns_404(self, client):
        response = client.get("/books/9999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Livro não encontrado"

    def test_get_book_invalid_id_returns_422(self, client):
        assert client.get("/books/abc").status_code == 422


@pytest.mark.integration
class TestUpdateBook:
    def test_update_title(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        body = client.put(f"/books/{created['id']}", json={"title": "Novo Título"}).json()
        assert body["status_code"] == 200
        assert body["data"]["title"] == "Novo Título"
        assert body["data"]["author"] == sample_book["author"]

    def test_update_author(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        body = client.put(f"/books/{created['id']}", json={"author": "Novo Autor"}).json()
        assert body["data"]["author"] == "Novo Autor"

    def test_update_publication_date(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        body = client.put(f"/books/{created['id']}", json={"publication_date": "2000-01-01"}).json()
        assert body["data"]["publication_date"] == "2000-01-01"

    def test_update_summary(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        body = client.put(f"/books/{created['id']}", json={"summary": "Novo resumo."}).json()
        assert body["data"]["summary"] == "Novo resumo."

    def test_update_multiple_fields(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        data = client.put(
            f"/books/{created['id']}",
            json={"title": "Título Atualizado", "author": "Autor Atualizado"},
        ).json()["data"]
        assert data["title"] == "Título Atualizado"
        assert data["author"] == "Autor Atualizado"

    def test_update_empty_body_returns_422(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        assert client.put(f"/books/{created['id']}", json={}).status_code == 422

    def test_update_nonexistent_book_returns_404(self, client):
        assert client.put("/books/9999", json={"title": "Qualquer"}).status_code == 404

    def test_update_empty_title_returns_422(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        assert client.put(f"/books/{created['id']}", json={"title": ""}).status_code == 422


@pytest.mark.integration
class TestDeleteBook:
    def test_delete_book_success(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        body = client.delete(f"/books/{created['id']}").json()
        assert body["status_code"] == 200
        assert body["data"] is None

    def test_deleted_book_not_found_by_id(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        client.delete(f"/books/{created['id']}")
        assert client.get(f"/books/{created['id']}").status_code == 404

    def test_deleted_book_excluded_from_list(self, client):
        create_book(client, "Livro Ativo", "Autor A")
        deleted = create_book(client, "Livro Deletado", "Autor B")
        client.delete(f"/books/{deleted['id']}")
        items = client.get("/books/").json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["title"] == "Livro Ativo"

    def test_deleted_book_total_excludes_inactive(self, client):
        create_book(client, "Livro Ativo", "Autor A")
        deleted = create_book(client, "Livro Deletado", "Autor B")
        client.delete(f"/books/{deleted['id']}")
        assert client.get("/books/").json()["data"]["total"] == 1

    def test_delete_nonexistent_book_returns_404(self, client):
        assert client.delete("/books/9999").status_code == 404

    def test_delete_already_deleted_book_returns_404(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        client.delete(f"/books/{created['id']}")
        assert client.delete(f"/books/{created['id']}").status_code == 404

    def test_update_deleted_book_returns_404(self, client, sample_book):
        created = client.post("/books/", json=sample_book).json()["data"]
        client.delete(f"/books/{created['id']}")
        assert client.put(f"/books/{created['id']}", json={"title": "Novo"}).status_code == 404


@pytest.mark.integration
class TestHealthCheck:
    def test_root_returns_ok(self, client):
        body = client.get("/").json()
        assert body["status_code"] == 200
        assert body["data"]["status"] == "ok"
