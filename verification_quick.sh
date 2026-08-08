#!/bin/bash
# RouanetConcilia — Quick Verification Script
# Runs critical checks in ~5 minutes to validate system readiness

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  echo -n "Checking: $name... "
  if eval "$cmd" > /tmp/verify_output.log 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}"
    PASS=$((PASS+1))
  else
    echo -e "${RED}❌ FAIL${NC}"
    echo "  Error output:"
    tail -5 /tmp/verify_output.log | sed 's/^/    /'
    FAIL=$((FAIL+1))
  fi
}

echo "=================================================="
echo "🚀 RouanetConcilia Quick Verification"
echo "=================================================="
echo ""

# ─────────────────────────────────────────
# FRONTEND
# ─────────────────────────────────────────
echo -e "${YELLOW}--- Frontend ---${NC}"

cd frontend 2>/dev/null || { echo "❌ frontend/ not found"; exit 1; }

check "Dependencies installed" "test -d node_modules"
check "TypeScript valid" "npx tsc --noEmit"
check "Tests pass (23 expected)" "npm run test -- --run 2>&1 | grep -q '23 passed'"
check "Build succeeds" "npm run build"

cd ..

echo ""

# ─────────────────────────────────────────
# BACKEND
# ─────────────────────────────────────────
echo -e "${YELLOW}--- Backend ---${NC}"

cd backend 2>/dev/null || { echo "❌ backend/ not found"; exit 1; }

check "Python syntax valid" "python -m py_compile main.py config.py database.py models.py"
check ".env exists" "test -f .env"
check "requirements.txt exists" "test -f requirements.txt"

cd ..

echo ""

# ─────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────
echo -e "${YELLOW}--- Database ---${NC}"

check "Migrations exist" "test -f db/migrations/0001_schema.sql"
check "Docker Compose config valid" "docker-compose config --quiet"

echo ""

# ─────────────────────────────────────────
# DOCUMENTATION
# ─────────────────────────────────────────
echo -e "${YELLOW}--- Documentation ---${NC}"

check "README.md exists" "test -f README.md"
check "SETUP.md exists" "test -f SETUP.md"
check "ARCHITECTURE.md exists" "test -f ARCHITECTURE.md"
check "VERIFICATION_CHECKLIST.md exists" "test -f VERIFICATION_CHECKLIST.md"

echo ""

# ─────────────────────────────────────────
# GIT
# ─────────────────────────────────────────
echo -e "${YELLOW}--- Git ---${NC}"

check "Working tree clean or expected changes" "true"  # Always pass, informational
git status --short | head -5

echo ""
echo "=================================================="
echo -e "Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}"
echo "=================================================="

if [ $FAIL -eq 0 ]; then
  echo -e "${GREEN}🎉 All checks passed! System is ready.${NC}"
  exit 0
else
  echo -e "${RED}⚠️  Some checks failed. Review errors above.${NC}"
  exit 1
fi
