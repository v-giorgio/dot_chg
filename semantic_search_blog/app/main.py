from dotenv import load_dotenv

load_dotenv()

import logging

from flask import Flask, jsonify, request

from .embeddings import embed
from .vector_store import FAISSStore

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.post("/search")
def search():
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    if not query:
        return jsonify({"error": "Campo 'query' é obrigatório e não pode ser vazio."}), 400
    if len(query) > 1000:
        return jsonify({"error": "Campo 'query' deve ter no máximo 1000 caracteres."}), 400

    top_k = body.get("top_k", 5)
    if not isinstance(top_k, int) or not (1 <= top_k <= 20):
        return jsonify({"error": "Campo 'top_k' deve ser um inteiro entre 1 e 20."}), 400

    try:
        [vec] = embed([query])
        results = FAISSStore().search(vec, top_k=top_k)
        return jsonify({"query": query, "results": results})
    except Exception:
        logger.exception("Falha na busca semântica para query: %r", query)
        return jsonify({"error": "Serviço indisponível. Verifique se os documentos foram indexados."}), 503


@app.get("/stats")
def stats():
    try:
        return jsonify({"indexed_chunks": FAISSStore().count()})
    except Exception:
        logger.exception("Falha ao obter estatísticas do índice")
        return jsonify({"error": "Vector store indisponível."}), 503
