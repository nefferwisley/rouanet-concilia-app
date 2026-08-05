# Conciliação Offline - Projeto 1961

App em Streamlit que lê a planilha **"2. Conciliação 1961.xlsx"** direto do
Google Drive (via Service Account) e exibe os dados em uma tabela.

## 1. Criar a Service Account no Google Cloud

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Vá em **IAM & Admin → Service Accounts**
3. Clique em **Criar Service Account**
4. Após criada, entre nela → aba **Chaves (Keys)** → **Adicionar chave → Criar nova chave → JSON**
5. O download do arquivo `.json` vai começar automaticamente

## 2. Configurar as credenciais no projeto

1. Renomeie o arquivo baixado para `creds.json`
2. Coloque esse arquivo na **raiz do projeto** (mesma pasta do `app.py`)

⚠️ **Nunca suba esse arquivo pro GitHub** — adicione `creds.json` no `.gitignore`.

## 3. Compartilhar a pasta/arquivo do Drive com a Service Account

O e-mail da Service Account tem o formato:
```
nome-da-conta@projeto.iam.gserviceaccount.com
```

Você encontra esse e-mail dentro do `creds.json` (campo `client_email`).

No Google Drive, abra a pasta ou o arquivo `2. Conciliação 1961.xlsx` →
**Compartilhar** → cole o e-mail da Service Account → permissão de
**Visualizador**.

⚠️ **Isso é obrigatório.** Sem compartilhar, a API retorna erro ou lista
vazia mesmo com credenciais válidas.

## 4. Instalar dependências e rodar

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt

streamlit run app.py
```

## Sobre o arquivo lido

O app já está configurado para baixar diretamente pelo ID do arquivo:

- **Arquivo:** `2. Conciliação 1961.xlsx`
- **ID:** `1q52xZirlzYCqpQJ7ldYNG9wQrVodPuJc`
- **Caminho no Drive:** Pasta raiz → `3. 1961` → `2. Conciliação 1961.xlsx`

Se o arquivo for movido ou substituído, atualize a constante
`TARGET_FILE_ID` em `app.py`.

## Justificativa automática por IA (opcional)

O app pode gerar justificativas automáticas para itens de conciliação
usando a IA do Google (Gemini). Isso é **opcional** — sem configurar,
o app funciona normalmente, só sem essa seção.

Para ativar:

1. Gere uma chave em [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Cria um arquivo chamado `.env` (sem nome antes do ponto) na raiz do
   projeto, com o conteúdo:
   ```
   GEMINI_API_KEY=sua_chave_aqui
   ```
3. **Nunca cole essa chave em nenhum chat ou lugar público.** O `.env`
   já está protegido no `.gitignore`, então não vai pro GitHub.
4. Instala as dependências (já estão no `requirements.txt`):
   ```
   pip install -r requirements.txt
   ```

## Publicando na nuvem (Streamlit Community Cloud) — para o app rodar 24/7 sem depender do seu PC

Hoje, ao rodar `streamlit run app.py`, o app só existe enquanto seu
computador estiver ligado e o terminal aberto. Pra virar um serviço
acessível de qualquer lugar, a qualquer hora, publique no Streamlit
Community Cloud (grátis).

### Passo 1 — Subir o código pro GitHub

⚠️ **Confirme antes de continuar:** `creds.json` e `.env` **não** devem
ir pro GitHub (o `.gitignore` já bloqueia isso, mas vale checar com
`git status` antes de dar `git push`).

```bash
cd meu_sistema_rouanet
git add .
git commit -m "Versão inicial do app de conciliação"
```

Cria um repositório novo (privado, de preferência) em
[github.com/new](https://github.com/new), depois:

```bash
git remote add origin https://github.com/SEU_USUARIO/NOME_DO_REPO.git
git branch -M main
git push -u origin main
```

### Passo 2 — Criar o app no Streamlit Cloud

1. Acessa [share.streamlit.io](https://share.streamlit.io) e loga com sua conta GitHub
2. Clica em **"New app"**
3. Seleciona o repositório que você acabou de criar
4. Em "Main file path", coloca `app.py`
5. Clica em **"Deploy"** (vai dar erro na primeira vez — falta configurar os Secrets, próximo passo)

### Passo 3 — Configurar os Secrets (credenciais seguras)

1. No painel do seu app no Streamlit Cloud, vai em **Settings → Secrets**
2. Abre o arquivo `.streamlit/secrets.toml.example` (incluído neste projeto) como referência
3. Cola no campo de Secrets do Streamlit Cloud, substituindo pelos valores reais:
   - `SENHA_ACESSO`: a senha de acesso ao painel
   - `GEMINI_API_KEY`: sua chave do Gemini (se for usar a IA — opcional)
   - `[gcp_service_account]`: **todo o conteúdo do seu `creds.json`**, campo por campo, no formato TOML (copia cada valor do JSON pro formato mostrado no exemplo)
4. Salva

O app reinicia sozinho e passa a ler as credenciais dali, com segurança
(o Secrets do Streamlit Cloud é criptografado e não aparece pra ninguém
além de você).

### Passo 4 — Compartilhar a pasta do Drive com a Service Account (de novo)

Mesmo passo de sempre — a Service Account (o e-mail que está em
`client_email` no seu `creds.json`) precisa ter acesso de leitura às
pastas do Drive (`3. 1961` e `1. Pagamentos`), independente de rodar
local ou na nuvem.

### Pronto

A partir daí, o link do seu app (algo como
`https://seu-app.streamlit.app`) funciona sempre, mesmo com seu PC
desligado. Toda vez que você der `git push` com mudanças no código, o
Streamlit Cloud atualiza o app automaticamente.
