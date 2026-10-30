from fastapi import FastAPI

from .database import Base, engine
from .routers import books
from .schemas import ApiResponse, HealthResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Biblioteca Virtual",
    description="API para cadastro e consulta de livros em uma biblioteca virtual.",
    version="1.0.0",
)

app.include_router(books.router)


@app.get("/", tags=["health"], response_model=ApiResponse[HealthResponse])
def root():
    """Verifica se a API está no ar."""
    return ApiResponse(
        status_code=200,
        data=HealthResponse(status="ok", message="Biblioteca Virtual API"),
    )
