@echo off
chcp 65001 > nul
if not defined DATABASE_URL (
    echo ERRO: defina DATABASE_URL no ambiente antes de executar. 1>&2
    exit /b 1
)
if not defined GOOGLE_API_KEY (
    echo ERRO: defina GOOGLE_API_KEY no ambiente antes de executar. 1>&2
    exit /b 1
)

python -m motor.importar --config "C:\Users\Dell\Downloads\config_1961.yaml" --json "C:\Users\Dell\Downloads\lançamentos_1961.json" --db-url "%DATABASE_URL%" --verbose
if errorlevel 1 exit /b %errorlevel%
pause
