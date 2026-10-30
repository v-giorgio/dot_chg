import re
import logging
from dataclasses import dataclass
from typing import Optional

import tiktoken

logger = logging.getLogger(__name__)

MAX_INPUT_TOKENS = 500
MAX_OUTPUT_TOKENS = 800

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+your\s+(previous\s+)?instructions?",
    r"pretend\s+(you\s+are|to\s+be)\s+(?!a\s+python)",
    r"act\s+as\s+(?!a\s+python)",
    r"new\s+persona",
    r"\bDAN\b(?:\s+mode)?",
    r"jailbreak",
    r"developer\s+mode",
    r"bypass\s+(safety|filter|guardrail|restriction)",
    r"override\s+(your\s+)?(system\s+)?(prompt|instructions?|rules?|settings?)",
    r"reveal\s+(your\s+)?(system\s+)?(prompt|instructions?|rules?)",
    r"(print|show|display|repeat|tell\s+me)\s+(your\s+)?(full\s+)?(system\s+)?(prompt|instructions?)",
    r"what('s|\s+is|\s+are)\s+your\s+(system\s+)?(prompt|instructions?|rules?)",
    r"(início|inicio|começo|start)\s+(do\s+)?(seu\s+)?(prompt|sistema|system)",
    r"você\s+(não\s+é|nao\s+e)\s+(mais\s+)?(um\s+)?assistente",
]

_SENSITIVE_OUTPUT_PATTERNS = [
    (r"sk-[A-Za-z0-9\-_]{20,}", "api-key"),
    (r"AKIA[A-Z0-9]{16}", "aws-key"),
    (r"(?i)(api[_\-\s]?key|secret[_\-\s]?key|access[_\-\s]?token)\s*[:=]\s*['\"]?[A-Za-z0-9\-_]{20,}", "credential"),
    (r"\b(?:\d[ -]?){15,16}\b", "credit-card"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
    (r"Bearer\s+[A-Za-z0-9\-_\.]{20,}", "bearer-token"),
]

_SYSTEM_PROMPT_LEAKAGE = [
    r"você\s+é\s+um\s+assistente\s+especialista\s+em\s+programação\s+python",
    r"diretrizes:",
    r"\[system prompt\]",
    r"<system>",
    r"system\s+prompt\s*[:=]",
]


@dataclass
class GuardrailResult:
    passed: bool
    reason: Optional[str] = None


def _count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


class GuardrailsService:
    def validate_input(self, text: str) -> GuardrailResult:
        token_count = _count_tokens(text)
        if token_count > MAX_INPUT_TOKENS:
            return GuardrailResult(
                passed=False,
                reason=f"Entrada excede o limite de {MAX_INPUT_TOKENS} tokens ({token_count} recebidos).",
            )

        for pattern in _INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning("Prompt injection attempt blocked. Pattern: %s", pattern)
                return GuardrailResult(
                    passed=False,
                    reason="Entrada contém padrão não permitido.",
                )

        return GuardrailResult(passed=True)

    def validate_output(self, text: str) -> GuardrailResult:
        for pattern, label in _SENSITIVE_OUTPUT_PATTERNS:
            if re.search(pattern, text):
                logger.warning("Sensitive data blocked in output. Label: %s", label)
                return GuardrailResult(
                    passed=False,
                    reason="Resposta bloqueada por política de segurança.",
                )

        for pattern in _SYSTEM_PROMPT_LEAKAGE:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning("System prompt leakage blocked.")
                return GuardrailResult(
                    passed=False,
                    reason="Resposta bloqueada por política de segurança.",
                )

        return GuardrailResult(passed=True)
