#!/usr/bin/env bash
# deploy_frontend.sh — publica o frontend no Cloudflare Pages.
#
# Por que este script existe: o projeto "rouanet-concilia" no Cloudflare Pages
# NÃO tem integração Git (`wrangler pages project list` mostra
# "Git Provider: No") — nenhum `git push` aciona rebuild sozinho. Todo deploy
# tem que ser manual via `wrangler pages deploy`. Duas armadilhas já
# aconteceram fazendo isso à mão e este script existe pra não repetí-las:
#
# 1. Buildar sem VITE_API_URL faz o bundle cair no fallback
#    "http://localhost:8000" (ver frontend/src/lib/api.ts) — o site sobe,
#    mas nenhuma chamada de API funciona (bloqueada como mixed content).
# 2. Buildar com o working tree "sujo" publica no ar qualquer WIP não
#    commitado de outra sessão/branch — por isso o script stasha antes de
#    buildar e restaura depois, SEMPRE (mesmo se o build falhar).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"
BACKEND_URL="${VITE_API_URL:-https://rouanetconcilia-backend-y19v.onrender.com}"
PROJECT_NAME="${CF_PAGES_PROJECT:-rouanet-concilia}"

cd "$REPO_ROOT"

STASHED=0
cleanup() {
  if [ "$STASHED" = "1" ]; then
    echo "↩ Restaurando mudanças locais que estavam pendentes (stash)…"
    git stash pop
  fi
}
trap cleanup EXIT

if [ -n "$(git status --porcelain)" ]; then
  echo "📦 Working tree tem mudanças não commitadas — guardando antes do build limpo…"
  git stash push -u -m "deploy_frontend.sh: preservado antes do build de deploy"
  STASHED=1
fi

echo "🔨 Buildando com VITE_API_URL=$BACKEND_URL"
cd "$FRONTEND_DIR"
VITE_API_URL="$BACKEND_URL" npm run build

# Trava de segurança: nunca publicar um bundle que caiu no fallback local.
JS_BUNDLE=$(ls dist/assets/index-*.js | head -1)
if grep -q "localhost:8000" "$JS_BUNDLE"; then
  echo "❌ ERRO: o bundle contém 'localhost:8000' — VITE_API_URL não foi aplicada corretamente. Abortando deploy."
  exit 1
fi
if ! grep -q "$(echo "$BACKEND_URL" | sed 's#https\?://##')" "$JS_BUNDLE"; then
  echo "❌ ERRO: o bundle não contém a URL do backend esperada ($BACKEND_URL). Abortando deploy."
  exit 1
fi
echo "✓ Bundle confirmado apontando para $BACKEND_URL"

echo "🚀 Publicando no Cloudflare Pages (projeto: $PROJECT_NAME)…"
npx wrangler pages deploy dist --project-name="$PROJECT_NAME" --branch=main --commit-dirty=true

echo "✅ Deploy concluído."
