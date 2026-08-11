@echo off
REM Script de inicialização do Orquestrador Automático

cd /d %~dp0..

echo.
echo =====================================================
echo   Meta-Orquestrador RouanetConcilia v2.0
echo   Modo: AUTO (Orquestração Paralela Automática)
echo =====================================================
echo.

REM Opção 1: Executar Phases 1-7 (completo)
REM python scripts\meta_orquestrador_integrado.py --phase 1-7 --mode auto

REM Opção 2: Executar Phases 5-7 (UI + Security)
REM python scripts\meta_orquestrador_integrado.py --phase 5-7 --mode auto

REM Opção 3: Ver plano antes (dry-run)
python scripts\meta_orquestrador_integrado.py --phase 1-7 --mode dry-run

echo.
echo Plano salvo em: saida\plano_execução.json
echo.
pause
