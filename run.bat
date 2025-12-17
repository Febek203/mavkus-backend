@echo off
echo 🚀 Avvio MAVKUS AI Server

echo 🔍 Controllo dipendenze...
pip install -r requirements.txt

echo 📁 Directory corrente: %CD%
echo 🔑 Controllo variabili ambiente...

python -c "
import os
from dotenv import load_dotenv
import sys

# Prova a caricare .env
env_paths = ['.env', '..\.env', '..\..\.env']
for path in env_paths:
    if os.path.exists(path):
        load_dotenv(dotenv_path=path)
        print(f'✅ .env trovato in: {path}')
        break
else:
    print('⚠️ Nessun file .env trovato')

groq = os.getenv('GROQ_API_KEY')
gemini = os.getenv('GEMINI_API_KEY')

print(f'GROQ_API_KEY: {'***CONFIGURATA***' if groq else 'NON TROVATA'}')
print(f'GEMINI_API_KEY: {'***CONFIGURATA***' if gemini else 'NON TROVATA'}')

if not groq:
    print('\n❌ ERRORE: GROQ_API_KEY mancante!')
    print('Crea un file .env nella root del progetto con:')
    print('GROQ_API_KEY=la_tua_chiave_qui')
    print('GEMINI_API_KEY=la_tua_chiave_qui')
    sys.exit(1)
"

if errorlevel 1 (
    echo.
    echo ❌ Impossibile avviare. Controlla le API keys.
    pause
    exit /b
)

echo.
echo ✅ Tutto pronto!
echo 🌐 Server in avvio...
echo 📚 Docs: http://localhost:8000/docs
echo 🔧 Health: http://localhost:8000/health
echo.

python server.py