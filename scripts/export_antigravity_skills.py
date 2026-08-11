#!/usr/bin/env python3
"""
scripts/export_antigravity_skills.py

Exports all 105 agency-agents into:
1. Workspace skills: .agents/skills/agency-<name>/SKILL.md
2. Global/CLI skills: antigravity-skills/agency-<name>/SKILL.md
3. User config skills: C:/Users/Dell/.gemini/config/skills/agency-<name>/SKILL.md
4. Workspace root AGENTS.md (full tool index)
5. Workspace root GEMINI.md (Antigravity system prompt + @./AGENTS.md)
6. planos/FASE-1..7.md execution roadmap
"""

import os
import re
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
AGENCY_DIR = ROOT_DIR / "agency-agents"
AGENTS_SKILLS_DIR = ROOT_DIR / ".agents" / "skills"
PORTABLE_SKILLS_DIR = ROOT_DIR / "antigravity-skills"
GLOBAL_CONFIG_SKILLS_DIR = Path("C:/Users/Dell/.gemini/config/skills")
PLANOS_DIR = ROOT_DIR / "planos"


def parse_agent_file(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)

    name = ""
    description = ""
    color = ""
    emoji = ""
    vibe = ""
    body = content

    if frontmatter_match:
        fm_text = frontmatter_match.group(1)
        body = frontmatter_match.group(2)

        for line in fm_text.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"\'')
                if key == "name":
                    name = val
                elif key == "description":
                    description = val
                elif key == "color":
                    color = val
                elif key == "emoji":
                    emoji = val
                elif key == "vibe":
                    vibe = val

    if not name:
        name = file_path.stem

    # Derive slug
    slug = file_path.stem
    # Remove category prefix if present (e.g. engineering-backend-architect -> backend-architect)
    parts = slug.split("-")
    if len(parts) > 1 and parts[0] in [
        "academic", "design", "engineering", "finance", "game", "gis", "healthcare",
        "integrations", "marketing", "paid", "product", "project", "sales", "security",
        "spatial", "specialized", "strategy", "support", "testing"
    ]:
        slug = "-".join(parts[1:])

    skill_slug = f"agency-{slug}"
    return {
        "slug": skill_slug,
        "name": name,
        "description": description or f"Agency agent: {name}",
        "color": color,
        "emoji": emoji,
        "vibe": vibe,
        "body": body,
        "file_path": file_path,
        "category": file_path.parent.name,
    }


def export():
    print(f"Scanning {AGENCY_DIR} for agents...")
    agent_files = []
    for root, _, files in os.walk(AGENCY_DIR):
        for f in files:
            if f.endswith(".md") and f not in ["README.md", "CONTRIBUTING.md", "CONTRIBUTING_zh-CN.md", "SECURITY.md"]:
                agent_files.append(Path(root) / f)

    agents = [parse_agent_file(f) for f in agent_files]
    print(f"Found {len(agents)} agents.")

    # Create target directories
    AGENTS_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    PORTABLE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    PLANOS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        GLOBAL_CONFIG_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create global config dir: {e}")

    for agent in agents:
        slug = agent["slug"]
        skill_content = f"""---
name: {slug}
description: {agent['description']}
---
{agent['body']}
"""

        # Write to .agents/skills/<slug>/SKILL.md
        ws_skill_dir = AGENTS_SKILLS_DIR / slug
        ws_skill_dir.mkdir(parents=True, exist_ok=True)
        (ws_skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        # Write to antigravity-skills/<slug>/SKILL.md
        port_skill_dir = PORTABLE_SKILLS_DIR / slug
        port_skill_dir.mkdir(parents=True, exist_ok=True)
        (port_skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        # Write to C:/Users/Dell/.gemini/config/skills/<slug>/SKILL.md
        try:
            glob_skill_dir = GLOBAL_CONFIG_SKILLS_DIR / slug
            glob_skill_dir.mkdir(parents=True, exist_ok=True)
            (glob_skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")
        except Exception:
            pass

    print(f"Exported {len(agents)} skills to .agents/skills/ and antigravity-skills/")

    # Generate AGENTS.md
    agents_md = f"""# Agency Agents Index ({len(agents)} Agents)

Este repositório contém a suíte completa de {len(agents)} agentes da agência especializada para auxílio em arquitetura, engenharia, design, segurança, finanças, GIS e auditoria cultural.

## Categorias de Agentes

"""
    categories = {}
    for a in agents:
        cat = a["category"].capitalize()
        categories.setdefault(cat, []).append(a)

    for cat, cat_agents in sorted(categories.items()):
        agents_md += f"### {cat} ({len(cat_agents)})\n\n"
        for a in sorted(cat_agents, key=lambda x: x['name']):
            agents_md += f"- **{a['name']}** (`{a['slug']}`): {a['description']}\n"
        agents_md += "\n"

    (ROOT_DIR / "AGENTS.md").write_text(agents_md, encoding="utf-8")
    print("Generated workspace AGENTS.md")

    # Generate GEMINI.md
    gemini_md = f"""# System Instructions for Antigravity AI

@./AGENTS.md

## Projeto: RouanetConcilia — Conciliação Financeira para Projetos Culturais (Lei Rouanet)

Você é o assistente Antigravity pareado com o usuário para desenvolver, auditar e operar o **RouanetConcilia**.

### Habilidades de Agente Ativas:
Todas as {len(agents)} habilidades especializadas estão disponíveis no diretório `.agents/skills/` e `C:/Users/Dell/.gemini/config/skills/`.

### Princípios do Projeto:
1. **Fidelidade à Planilha Oficial**: O site reflete 1:1 a estrutura e os dados da planilha oficial de revisão financeira do projeto.
2. **Interface Premium & Clean**: Visual escuro glassmorphic com alta legibilidade, filtragem rápida e sem rótulos redundantes.
3. **Autenticação & Token Transparente**: Auto-renovação de sessão JWT do Supabase via REST API sem deslogar o usuário.
4. **Resolução de Documentos**: PDFs de comprovantes e NFs são abertos inline diretamente do banco de dados/disco.

"""
    (ROOT_DIR / "GEMINI.md").write_text(gemini_md, encoding="utf-8")
    print("Generated workspace GEMINI.md")

    # Generate planos/FASE-1..7.md
    fases = [
        ("FASE-1.md", "Fase 1: Infraestrutura, Autenticação Supabase e Schema PostgreSQL"),
        ("FASE-2.md", "Fase 2: Motor Python de Importação e Parsing do Projeto 1961"),
        ("FASE-3.md", "Fase 3: Backend FastAPI (Rotas de Auditoria, Conciliação e Documentos)"),
        ("FASE-4.md", "Fase 4: Frontend React/Vite com Tabela Rica Alinhada à Planilha"),
        ("FASE-5.md", "Fase 5: Reimportação Oficial do Projeto 1961 e Associação de Rubricas"),
        ("FASE-6.md", "Fase 6: Suíte de Testes Automatizados (Vitest 13/13 & Pytest 152/152)"),
        ("FASE-7.md", "Fase 7: Deploy em Produção (Netlify App & Render API)"),
    ]

    for filename, title in fases:
        fase_content = f"""# {title}

## Visão Geral
Roteiro detalhado de execução para a {title.split(':')[0]}.

## Metas e Entregáveis
- Implementação rigorosa sem regressões.
- Verificação automatizada e validação manual com o usuário.
- Sincronização com o repositório principal do GitHub.
"""
        (PLANOS_DIR / filename).write_text(fase_content, encoding="utf-8")

    print("Generated planos/FASE-1..7.md")


if __name__ == "__main__":
    export()
