#!/usr/bin/env python3
"""
Exporta skills do .opencode/agents/ (formato opencode subagent)
para o formato Agent Skills do Google Antigravity (SKILL.md).

Padrao Antigravity (docs oficiais):
  - Uma skill = pasta com SKILL.md
  - Frontmatter YAML obrigatorio: description (gatilho semantico); name (slug, opcional)
  - Project-scope padrao (workspace): .agents/skills/<skill-name>/SKILL.md
  - Global: ~/.gemini/config/skills/

Uso:
  python scripts/export_antigravity_skills.py
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".opencode" / "agents"
OUT_EXPORT = ROOT / "antigravity-skills"
OUT_PROJECT = ROOT / ".agents" / "skills"

# Skills recomendadas por fase (plano de verificacao)
SELECTED = [
    # Fase 1 - Ingestao (pasta + Drive)
    "data-engineer",
    "privacy-engineer",
    "secrets-credential-hygiene-engineer",
    # Fase 2 - Base de dados
    "database-optimizer",
    "database-reliability-engineer",
    # Fase 3 - Consistencia e cruzamento (reconciliacao)
    "ai-data-remediation-engineer",
    "payments-billing-engineer",
    # Fase 4 - Espelho planilha <-> site
    "backend-architect",
    "realtime-collaboration-engineer",
    # Fase 5 - Tela de lancamentos
    "frontend-developer",
    "ui-designer",
    "data-visualization-engineer",
    "evidence-collector",
    # Fase 6 - Extracao / prestacao de contas MINC
    "compliance-auditor",
    # Fase 7 - Seguranca / LGPD / qualidade
    "senior-secops-engineer",
    "ai-generated-code-security-auditor",
    "reality-checker",
]

# Skills cujo corpo termina com bloco "Instructions Reference" exclusivo do opencode
TAIL_REF = "**Instructions Reference**:"


def parse_agent(path: Path) -> tuple[str, str, str]:
    """Extrai (name, description, body) do arquivo de agente."""
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, flags=re.S)
    if not m:
        raise ValueError(f"Frontmatter nao encontrado em {path.name}")
    fm, body = m.group(1), m.group(2)
    name = re.search(r"^name:\s*(.+)$", fm, flags=re.M)
    desc = re.search(r"^description:\s*(.+)$", fm, flags=re.M)
    if not name or not desc:
        raise ValueError(f"Frontmatter incompleto em {path.name}")
    return name.group(1).strip(), desc.group(1).strip(), body.strip()


def strip_opencode_tail(body: str) -> str:
    """Remove bloco final 'Instructions Reference' — artefato do opencode, irrelevante no Antigravity."""
    idx = body.find(TAIL_REF)
    if idx != -1:
        body = body[:idx].rstrip()
    return body


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return slug or "skill"


def write_skill(src_name: str, out_base: Path) -> None:
    src = SRC / f"{src_name}.md"
    if not src.exists():
        print(f"  [SKIP] fonte nao encontrada: {src.name}")
        return

    name, description, body = parse_agent(src)
    slug = slugify(name)
    body = strip_opencode_tail(body)

    frontmatter = f"---\nname: {slug}\ndescription: >-\n  {description}\n---\n"
    content = frontmatter + "\n" + body + "\n"

    out_dir = out_base / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    sk = out_dir / "SKILL.md"
    sk.write_text(content, encoding="utf-8")
    print(f"  [OK] {slug} -> {out_dir.relative_to(ROOT).as_posix()}/SKILL.md")


def main() -> int:
    print("== Exportando skills para o formato Agent Skills do Antigravity ==\n")

    for base in (OUT_EXPORT, OUT_PROJECT):
        if base.exists():
            shutil.rmtree(base)

    print(f"[1] Export portavel: {OUT_EXPORT.relative_to(ROOT)}/")
    for s in SELECTED:
        write_skill(s, OUT_EXPORT)

    print(f"\n[2] Project-scope do workspace: {OUT_PROJECT.relative_to(ROOT)}/")
    for s in SELECTED:
        write_skill(s, OUT_PROJECT)

    print(f"\nConcluido: {len(SELECTED)} skills no formato Agent Skills.")
    print("\nInstalacao:")
    print("  - AGY/AGY IDE neste workspace    : ja instalado (auto-discovery em .agents/skills/)")
    print("  - Global (todos os projetos)     : copie antigravity-skills/* -> ~/.gemini/config/skills/")
    print("  - AGY CLI project-scope          : copie para .agent/skills/")
    print("  - AGY CLI global                 : copie para ~/.gemini/antigravity-cli/skills/")
    return 0


if __name__ == "__main__":
    sys.exit(main())