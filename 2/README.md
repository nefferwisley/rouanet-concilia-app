# RouanetConcilia API

Motor de leitura e validação de dados do Projeto 1961, exposto como
API REST. Esta API existe para que o painel HTML legado
(`nefferwisley/rouanet-concilia`, GitHub Pages) possa consumir dados
reais e validados do Google Drive, sem precisar de login OAuth do
usuário nem de dados mockados no código.

## Por que isso existe

O painel HTML antigo lia dados de duas formas problemáticas:
1. Login OAuth do próprio usuário no navegador (token expira, exige
   login toda sessão, e expõe o token no `localStorage`)
2. Dados mockados/hardcoded direto no código (`realRows1961`)

Esta API resolve os dois problemas: autentica via Service Account no
servidor (nunca exposta ao navegador) e lê os dados reais do Drive sob
demanda.

## Rodando localmente

```bash
pip install -r requirements.txt
```

Cria um arquivo `.env` ou exporta as variáveis direto no terminal:

```bash
export API_KEY="escolha-uma-chave-forte-aqui"
export GOOGLE_CREDS_JSON='{"type": "service_account", ...}'  # conteúdo do creds.json numa linha só
```

Ou, mais simples para teste local: coloca o `creds.json` na raiz do
projeto (a API detecta automaticamente) e só define `API_KEY`.

```bash
uvicorn main:app --reload
```

Testa em `http://localhost:8000/health` (não precisa de chave) e
`http://localhost:8000/planilha` (precisa do header `X-API-Key`).

## Endpoints

| Método | Rota | O que faz |
|---|---|---|
| GET | `/health` | Verifica se a API está no ar (sem autenticação) |
| GET | `/planilha` | Retorna a planilha de conciliação em JSON |
| GET | `/pdfs` | Lista os comprovantes PDF disponíveis |
| POST | `/validar-comprovantes` | Roda a validação em lote (PDF × planilha) |

Todos exceto `/health` exigem o header:
```
X-API-Key: sua-chave-configurada
```

## Publicando (Render.com — grátis)

1. Sobe este código pra um repositório GitHub novo (ex: `rouanet-concilia-api`)
2. Cria conta em [render.com](https://render.com), loga com GitHub
3. **New → Web Service** → seleciona o repositório
4. Configuração:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Em **Environment Variables**, adiciona:
   - `API_KEY` = uma chave forte que só você conhece (gere uma em [1password.com/password-generator](https://1password.com/password-generator) ou similar)
   - `GOOGLE_CREDS_JSON` = todo o conteúdo do seu `creds.json`, colado como uma linha só (copia o JSON inteiro e cola no campo)
   - `CORS_ALLOWED_ORIGIN` = a URL do seu painel HTML (ex: `https://nefferwisley.github.io`)
6. Deploy

O Render te dá uma URL tipo `https://rouanet-concilia-api.onrender.com`.

⚠️ **Plano gratuito do Render "dorme" após 15 min de inatividade** — a
primeira requisição depois disso demora ~30-50s para "acordar" o
serviço. Para uso real frequente, considere o plano pago ($7/mês) ou
outro provedor (Railway tem lógica parecida).

## Integrando com o painel HTML legado

No `index.html` do painel antigo, localize os trechos que fazem
`fetch` direto para `googleapis.com` (as chamadas com
`Authorization: Bearer ${gDriveAccessToken}`) e substitua por
chamadas para esta API, por exemplo:

```javascript
const API_URL = "https://rouanet-concilia-api.onrender.com";
const API_KEY = "sua-chave-aqui"; // idealmente não hardcoded, ver nota abaixo

async function buscarPlanilha() {
  const res = await fetch(`${API_URL}/planilha`, {
    headers: { "X-API-Key": API_KEY }
  });
  const data = await res.json();
  return data.dados; // array de linhas, pronto pra popular a tabela
}
```

⚠️ **Nota importante sobre a API_KEY no front-end:** como o painel é
um site estático (GitHub Pages), não existe como esconder totalmente
a API_KEY do navegador — qualquer chave colocada no JavaScript do
painel é visível a quem inspecionar o código-fonte da página. Isso é
uma limitação arquitetural de sites estáticos, não um bug. Se isso for
uma preocupação real (dados sensíveis, uso por terceiros não
confiáveis), a solução correta é adicionar uma camada de login próprio
no painel (usuário/senha reais, não só uma chave fixa), o que é um
passo futuro a se planejar separadamente.
