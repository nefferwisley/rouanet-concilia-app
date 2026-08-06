@echo off
chcp 65001 > nul
python -m motor.importar --config "C:\Users\Dell\Downloads\config_1961.yaml" --json "C:\Users\Dell\Downloads\lançamentos_1961.json" --db-url "postgresql://postgres.okszeaecgyrymoxwwhdm:123%%40456b78c@aws-0-sa-east-1.pooler.supabase.com:6543/postgres" --verbose
pause



uv run python -m motor.importar --config config_1961.yaml --json lancamentos_1961.json --db-url="postgresql://postgres:SUA_SENHA_BANCO@db.xxxx.supabase.co:6543/postgres" --api-key-gemini="AQ.Ab8RN6LbXF5qeTiVmnb3cr-WuoEnX3_WiWZdH5BG9QaBGaS8Cg" --verbose