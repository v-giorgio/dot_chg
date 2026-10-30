@echo off
echo Atualizando pip...
python -m pip install --upgrade pip

echo.
echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo Instalacao concluida!
echo Para iniciar: python app.py
pause
