@echo off
echo [1/2] Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERRO: Falha ao instalar dependencias.
    exit /b 1
)

echo [2/2] Pronto! Proximos passos:
echo   cp .env.example .env
echo   ollama pull nomic-embed-text
echo   python index_blog.py --max-posts 5
echo   flask --app app.main run --debug
