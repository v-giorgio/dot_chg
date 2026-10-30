# Chatbot Python — Especificações

## Objetivo
API REST Flask com um único endpoint de inferência, especializado em Python, com guardrails de segurança e sem contexto entre requisições.

## Stack
| Componente | Tecnologia |
|------------|-----------|
| Framework web | Flask 3.x |
| LLM | OpenAI GPT-4o via LangChain |
| Token counting | tiktoken (cl100k_base) |
| Config | python-dotenv |

## Estrutura de Arquivos
```
chatbot_python/
├── app.py              — Flask app + rota POST /api/inference/
├── requirements.txt
├── .env.example
├── install.bat
└── inference/
    ├── guardrails.py   — GuardrailsService (input + output)
    └── llm.py          — chain LangChain stateless
```

## Endpoint
| Campo | Valor |
|-------|-------|
| Método | `POST` |
| URL | `/api/inference/` |
| Content-Type | `application/json` |
| Request body | `{"message": "Como criar uma lista em Python?"}` |
| Response 200 | `{"response": "..."}` |
| Response 400 | `{"error": {...}}` — campo ausente, vazio ou longo demais |
| Response 422 | `{"error": "..."}` — guardrail bloqueou |
| Response 503 | `{"error": "..."}` — falha no LLM |

## Guardrails

### Entrada (`validate_input`)
1. **Limite de caracteres**: máximo 2000 chars (validação em `app.py`)
2. **Limite de tokens**: máximo 500 tokens (tiktoken cl100k_base)
3. **Prompt injection**: regex contra 15+ padrões (DAN, jailbreak, "ignore instructions", "reveal system prompt", "bypass safety" etc.)

### Saída (`validate_output`)
1. **Dados sensíveis**: bloqueia API keys (sk-..., AKIA...), tokens Bearer, cartão de crédito, SSN
2. **Vazamento de system prompt**: bloqueia se a resposta reproduzir trechos das instruções internas

## Limites de Tokens
| Direção | Limite | Mecanismo |
|---------|--------|-----------|
| Entrada | 500 tokens | tiktoken no guardrail de input |
| Saída | 800 tokens | `max_tokens=800` na chamada OpenAI |

## Sem Contexto
Cada requisição é independente — sem histórico entre chamadas. A chain LangChain recebe apenas `{message}` + system prompt fixo.

## Dependências (sem extensões C problemáticas)
`langchain-core==0.3.0` + `langchain-openai==0.2.0` resolvem para `langsmith==0.1.147`, que não depende de `zstandard` — compatível com Python 3.15.

## Como executar
```bash
cd chatbot_python
cp .env.example .env       # preencha OPENAI_API_KEY
install.bat
python app.py              # http://127.0.0.1:5000
```

## Exemplo de uso
```bash
curl -X POST http://127.0.0.1:5000/api/inference/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Como criar uma lista em Python?"}'
```
