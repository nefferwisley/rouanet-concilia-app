import re

def fix_file(path, replacements):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    for old, new in replacements:
        text = text.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

fix_file('backend/main.py', [
    (
        '''# Login de demonstração SEM autenticação (rota /api/v1/dev/demo-login).
app.include_router(dev_demo.router)''',
        '''# Login de demonstração SEM autenticação (rota /api/v1/dev/demo-login).
if settings.dev_routes_enabled:
    app.include_router(dev_demo.router)'''
    )
])

fix_file('backend/routes/dev_demo.py', [
    (
        '''@router.post("/api/v1/dev/demo-login")
async def gerar_token_demo():''',
        '''@router.post("/api/v1/dev/demo-login")
async def gerar_token_demo():
    if not settings.dev_routes_enabled:
        raise HTTPException(status_code=403, detail="Rota indisponível em produção")'''
    )
])
