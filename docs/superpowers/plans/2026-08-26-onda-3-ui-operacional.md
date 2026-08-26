# Onda 3 UI Operacional Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refinar a Visão Geral do Projeto e o shell com hierarquia, semântica, responsividade e acessibilidade consistentes, sem alterar dados ou regras financeiras.

**Architecture:** Manter o fluxo de dados atual e criar primitivas visuais locais em `Dashboard.tsx`, promovendo apenas tokens compartilhados para `index.css`. Header e Sidebar recebem mudanças mínimas de apresentação, responsividade e foco.

**Tech Stack:** React 18, TypeScript, React Router, Tailwind CSS, Recharts, Vitest e Testing Library.

**Spec:** `docs/superpowers/specs/2026-08-26-onda-3-ui-operacional-design.md`

## Global Constraints

- Preservar `AGENTS.md`, o handoff da Onda 2 e todo trabalho preexistente.
- Não usar reset, checkout destrutivo, clean ou reformatação ampla.
- Não incluir `.claude/settings.local.json` em staging ou commits.
- Não alterar backend, migrations, autenticação, endpoints ou cálculos.
- Manter distintos “documentação completa”, “em análise” e “conciliada”.
- Validar tema claro/escuro e larguras aproximadas de 1440, 1024 e 390 px.

---

### Task 1: Travar a semântica dos gates financeiros

**Files:**
- Modify: `frontend/src/pages/Dashboard.test.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`

**Interfaces:**
- Consumes: `AuditoriaResumo` e `TransacaoAuditoria` atuais.
- Produces: distribuição exclusiva com ids `conciliadas`, `em-analise` e `pendencias`.

- [ ] **Step 1: Escrever o teste vermelho**

```tsx
it("separa documentação completa de conciliação bancária", async () => {
  api.get.mockImplementation((url: string) => {
    if (url === "/api/v1/projetos/p-1") return Promise.resolve({ ...p1, valor_captado: 1000 });
    if (url.includes("/auditoria")) return Promise.resolve({
      ...auditoria(10, 4, 750),
      resumo: { total: 10, orcado: 1000, debitado: 750, com_docs: 7, sem_docs: 3, total_ok: 4, total_pendente: 6 },
    });
    return Promise.reject(new Error(`URL inesperada: ${url}`));
  });
  render(<MemoryRouter><Dashboard /></MemoryRouter>);
  expect(await screen.findByTestId("status-conciliadas")).toHaveTextContent("4");
  expect(screen.getByTestId("status-em-analise")).toHaveTextContent("3");
  expect(screen.getByTestId("status-pendencias")).toHaveTextContent("3");
});
```

- [ ] **Step 2: Confirmar RED**

Run: `cd frontend && npm test -- --run src/pages/Dashboard.test.tsx`

Expected: FAIL porque os ids e “Em análise” ainda não existem.

- [ ] **Step 3: Implementar a distribuição exclusiva**

Preservar:

```ts
const emAnalise = Math.max(resumo.com_docs - resumo.total_ok, 0);
const pendentesExclusivos = Math.max(resumo.total - resumo.total_ok - emAnalise, 0);
```

Criar:

```ts
const statusResumo = [
  { id: "conciliadas", label: "Conciliadas", value: resumo.total_ok, description: "Documentos e banco validados" },
  { id: "em-analise", label: "Em análise", value: emAnalise, description: "Documentação completa; banco pendente" },
  { id: "pendencias", label: "Com pendências", value: pendentesExclusivos, description: "Falta documento ou pareamento" },
];
```

Renderizar com `data-testid={`status-${item.id}`}` e manter o total separado.

- [ ] **Step 4: Confirmar GREEN**

Run: `cd frontend && npm test -- --run src/pages/Dashboard.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit isolado**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.test.tsx
git commit -m "test: clarify dashboard reconciliation gates"
```

---

### Task 2: Consolidar cards, gráficos e tabelas

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/Dashboard.test.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Consumes: `statusResumo` da Task 1.
- Produces: `DashboardCard`, KPIs, resumos de status, regiões e tabelas acessíveis.

- [ ] **Step 1: Escrever testes vermelhos de estrutura**

```tsx
expect(await screen.findByRole("region", { name: "Indicadores financeiros" })).toBeInTheDocument();
expect(screen.getByRole("region", { name: "Evolução financeira" })).toBeInTheDocument();
expect(screen.getByRole("region", { name: "Situação das conciliações" })).toBeInTheDocument();
expect(screen.getByRole("table", { name: "Pagamentos com pendências" })).toBeInTheDocument();
expect(screen.getByRole("table", { name: "Últimos lançamentos" })).toBeInTheDocument();
```

- [ ] **Step 2: Confirmar RED**

Run: `cd frontend && npm test -- --run src/pages/Dashboard.test.tsx`

Expected: FAIL por falta dos nomes acessíveis.

- [ ] **Step 3: Criar e aplicar primitivas locais**

```tsx
function DashboardCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`dashboard-card min-w-0 ${className}`}>{children}</div>;
}
```

Atualizar `MetricCard` para valor sem truncar, helper alinhado e ícone tonal. Criar `StatusSummaryCard` com ícone, contagem, percentual e descrição. Usar `DashboardCard` nos gráficos, alertas e tabelas; adicionar `aria-label`, `scope="col"` e resumo textual adjacente à rosca.

- [ ] **Step 4: Refinar tokens CSS**

```css
:root {
  --surface-border: #e2e8f0;
  --surface-shadow: 0 12px 32px -24px rgba(15, 23, 42, 0.45);
  --focus-ring: rgba(20, 184, 166, 0.48);
}
.dashboard-card {
  @apply rounded-[18px] border border-slate-200/80 bg-white dark:border-navy-700 dark:bg-navy-800;
  box-shadow: var(--surface-shadow);
}
.interactive-focus {
  @apply focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/50 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-navy-900;
}
```

- [ ] **Step 5: Confirmar GREEN**

Run: `cd frontend && npm test -- --run src/pages/Dashboard.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit isolado**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.test.tsx frontend/src/index.css
git commit -m "feat: polish project overview dashboard"
```

---

### Task 3: Refinar shell e navegação móvel

**Files:**
- Modify: `frontend/src/components/Header.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/index.css`
- Create: `frontend/src/components/AppShell.test.tsx`

**Interfaces:**
- Consumes: contextos de projeto, autenticação e tema atuais.
- Produces: shell responsivo com página atual e controles nomeados.

- [ ] **Step 1: Escrever o teste vermelho**

Após mockar os contextos, renderizar Header e Sidebar:

```tsx
expect(screen.getByRole("link", { name: "Visão Geral" })).toHaveAttribute("aria-current", "page");
expect(screen.getByRole("button", { name: "Notificações, 3 não lidas" })).toBeInTheDocument();
expect(screen.getByRole("button", { name: "Abrir menu de navegação" })).toBeInTheDocument();
```

- [ ] **Step 2: Confirmar RED**

Run: `cd frontend && npm test -- --run src/components/AppShell.test.tsx`

Expected: FAIL por ausência de `aria-current` e do nome completo das notificações.

- [ ] **Step 3: Implementar o refinamento mínimo**

No Header, aplicar gaps responsivos, truncamento seguro, `interactive-focus`, `aria-label="Notificações, 3 não lidas"` e remover aparência clicável do perfil sem ação. Na Sidebar, adicionar `aria-current`, `min-h-11`, foco visível e preservar fechamento móvel ao navegar.

- [ ] **Step 4: Executar testes focados**

Run: `cd frontend && npm test -- --run src/components/AppShell.test.tsx src/context/ProjectContext.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit isolado**

```bash
git add frontend/src/components/Header.tsx frontend/src/components/Sidebar.tsx frontend/src/components/AppShell.test.tsx frontend/src/index.css
git commit -m "feat: refine responsive application shell"
```

---

### Task 4: Regressão e finish gate visual

**Files:**
- Modify only if a defect is verified: files owned by Tasks 1–3.
- Evidence: local screenshots outside the repository.

**Interfaces:**
- Consumes: UI final das Tasks 1–3.
- Produces: evidência de testes, build, responsividade, temas e console.

- [ ] **Step 1: Executar testes focados**

Run: `cd frontend && npm test -- --run src/pages/Dashboard.test.tsx src/components/AppShell.test.tsx`

Expected: PASS.

- [ ] **Step 2: Executar suíte completa**

Run: `cd frontend && npm test -- --run`

Expected: PASS.

- [ ] **Step 3: Executar build**

Run: `cd frontend && npm run build`

Expected: exit 0; registrar aviso de bundle sem confundi-lo com falha.

- [ ] **Step 4: Validar o diff**

Run: `git diff --check`

Expected: nenhuma saída.

- [ ] **Step 5: Smoke visual autenticado**

Na rota `/projetos/d6027085-7023-421d-a708-5e3d49b2148e/visao-geral`, validar 1440, 1024 e 390 px; temas claro/escuro; foco por Tab; ausência de overflow da página e de erros novos no console.

- [ ] **Step 6: Corrigir somente defeitos comprovados e repetir o gate afetado**

Não alterar componentes adjacentes. Reexecutar o teste, build ou viewport que comprovou o defeito.

- [ ] **Step 7: Registrar estado final**

Run: `git status --short` e `git diff --stat`

Expected: apenas arquivos declarados, além dos preexistentes do usuário intocados.

- [ ] **Step 8: Commit final de QA, se necessário**

```bash
git add <somente os arquivos da Onda 3 que precisaram de correção>
git commit -m "fix: finish onda 3 responsive polish"
```
