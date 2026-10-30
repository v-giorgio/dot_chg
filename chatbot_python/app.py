import logging
import uuid
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from langsmith import traceable

from inference.guardrails import GuardrailsService
from inference.llm import get_response

load_dotenv()

app = Flask(__name__)
logger = logging.getLogger(__name__)
_guardrails = GuardrailsService()

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)


@traceable(name="chatbot-inference", tags=["python-chatbot"])
def _traced_inference(message: str) -> str:
    return get_response(message)


@app.route("/api/inference/", methods=["POST"])
def inference():
    data = request.get_json(silent=True)

    if not data or "message" not in data:
        return jsonify({"error": {"message": ["Este campo é obrigatório."]}}), 400

    message = data["message"]

    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": {"message": ["Este campo não pode estar vazio."]}}), 400

    if len(message) > 2000:
        return jsonify({"error": {"message": ["Mensagem muito longa (máximo 2000 caracteres)."]}}), 400

    input_check = _guardrails.validate_input(message)
    if not input_check.passed:
        return jsonify({"error": input_check.reason}), 422

    try:
        response_text = _traced_inference(message)
    except Exception as exc:
        logger.error("LLM inference error: %s", exc, exc_info=True)
        return jsonify({"error": "Erro ao processar a requisição."}), 503

    output_check = _guardrails.validate_output(response_text)
    if not output_check.passed:
        logger.warning("Output blocked for input (first 80 chars): %.80s", message)
        return jsonify({"error": output_check.reason}), 422

    return jsonify({"response": response_text}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
