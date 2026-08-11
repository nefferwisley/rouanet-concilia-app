@echo off
REM ============================================================
REM RouanetConcilia - sobe a stack local completa (Windows)
REM   1) Postgres 16 em Docker (porta 5433 - a 5432 e do Postgres nativo)
REM   2) Backend FastAPI (porta 8000)
REM   3) Frontend Vite (porta 5173)
REM ============================================================
setlocal
cd /d "%~dp0"

echo [1/3] Subindo Postgres (Docker, porta 5433)...
docker ps --filter "name=^rouanet_db$" --format "{{.Names}}" | findstr /C:"rouanet_db" >nul 2>&1
if errorlevel 1 (
    docker run -d --name rouanet_db --restart always ^
        -e POSTGRES_USER=rouanet ^
        -e POSTGRES_PASSWORD=rouanet_dev_password ^
        -e POSTGRES_DB=rouanet_concilia ^
        -p 5433:5432 ^
        -v rouanet_pg_data:/var/lib/postgresql/data ^
        postgres:16-alpine
    if errorlevel 1 goto :docker_fail
    echo    Container rouanet_db criado.
) else (
    echo    Container rouanet_db ja existe - iniciando se parado...
    docker start rouanet_db >nul 2>&1
)

echo [2/3] Aguardando Postgres aceitar conexoes...
set PGPASSWORD=rouanet_dev_password
for /L %%i in (1,1,30) do (
    "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U rouanet -h 127.0.0.1 -p 5433 -d rouanet_concilia -c "select 1" >nul 2>&1
    if not errorlevel 1 goto :db_ok
    timeout /t 2 /nobreak >nul
)
echo    ERRO: Postgres nao respondeu na 5433 em 60s.
goto :end

:db_ok
echo    Postgres OK na porta 5433.

echo [3/3] Subindo backend (uvicorn :8000) e frontend (vite :5173)...
start "rouanet-backend" cmd /c "set PYTHONPATH=%CD%&& python -m uvicorn main:app --host 127.0.0.1 --port 8000"
start "rouanet-frontend" cmd /c "cd frontend && npm run dev"

echo.
echo Stack no ar:
echo   Postgres : postgresql://rouanet:rouanet_dev_password@127.0.0.1:5433/rouanet_concilia
echo   Backend  : http://127.0.0.1:8000  (docs: /docs)
echo   Frontend : http://127.0.0.1:5173
goto :end

:docker_fail
echo ERRO: docker run falhou. Docker Desktop esta rodando? (disco cheio tambem derruba o daemon)

:end
endlocal