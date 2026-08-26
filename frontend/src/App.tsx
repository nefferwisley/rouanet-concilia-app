import { lazy, Suspense, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { useAuth } from "./context/AuthContext";
import { ProjectProvider } from "./context/ProjectContext";

const Dashboard = lazy(() => import("./pages/Dashboard").then(m => ({ default: m.Dashboard })));
const ProjetosPage = lazy(() => import("./pages/ProjetosPage").then(m => ({ default: m.ProjetosPage })));
const ProponentesPage = lazy(() => import("./pages/ProponentesPage").then(m => ({ default: m.ProponentesPage })));
const CaptacoesPage = lazy(() => import("./pages/CaptacoesPage").then(m => ({ default: m.CaptacoesPage })));
const DespesasPage = lazy(() => import("./pages/DespesasPage").then(m => ({ default: m.DespesasPage })));
const ConciliacaoPage = lazy(() => import("./pages/ConciliacaoPage").then(m => ({ default: m.ConciliacaoPage })));
const RelatoriosPage = lazy(() => import("./pages/RelatoriosPage").then(m => ({ default: m.RelatoriosPage })));
const AlertasPage = lazy(() => import("./pages/AlertasPage").then(m => ({ default: m.AlertasPage })));
const AgendaPage = lazy(() => import("./pages/AgendaPage").then(m => ({ default: m.AgendaPage })));
const DocumentosPage = lazy(() => import("./pages/DocumentosPage").then(m => ({ default: m.DocumentosPage })));
const UsuariosPage = lazy(() => import("./pages/UsuariosPage").then(m => ({ default: m.UsuariosPage })));

const ImportacaoDetalhes = lazy(() => import("./pages/ImportacaoDetalhes").then(m => ({ default: m.ImportacaoDetalhes })));
const LoginPage = lazy(() => import("./pages/LoginPage").then(m => ({ default: m.LoginPage })));
const ProjetoDetalhes = lazy(() => import("./pages/ProjetoDetalhes").then(m => ({ default: m.ProjetoDetalhes })));
const RelatorioPage = lazy(() => import("./pages/RelatorioPage").then(m => ({ default: m.RelatorioPage })));
const DesignMockup = lazy(() => import("./pages/DesignMockup"));

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { token } = useAuth();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function MainLayout() {
  const location = useLocation();
  const { token } = useAuth();
  const [menuAberto, setMenuAberto] = useState(false);
  const isLoginPage = location.pathname === '/login';
  const isDesignPage = location.pathname.startsWith('/design');
  
  if (isLoginPage) {
    return (
      <Suspense fallback={<div className="p-8 text-center text-slate-500">Carregando...</div>}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </Suspense>
    );
  }

  if (isDesignPage) {
    return (
      <Suspense fallback={<div className="p-8 text-center text-slate-500">Carregando...</div>}>
        <Routes>
          <Route path="/design/*" element={<DesignMockup />} />
        </Routes>
      </Suspense>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <ProjectProvider>
      <div className="flex h-screen bg-[#f7f9fb] dark:bg-navy-950 font-sans text-slate-800 overflow-hidden transition-colors">
        <Sidebar mobileOpen={menuAberto} onClose={() => setMenuAberto(false)} />
        <main className="flex-1 flex flex-col h-full overflow-hidden">
          <Header onOpenMenu={() => setMenuAberto(true)} />
          <div className="flex-1 overflow-y-auto px-4 py-5 sm:px-6 xl:px-8 xl:py-7">
            <Suspense fallback={<div className="p-8 text-center text-slate-500">Carregando...</div>}>
              <Routes>
                <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                <Route path="/projetos/:id/visao-geral" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/projetos" element={<ProtectedRoute><ProjetosPage /></ProtectedRoute>} />
              <Route path="/proponentes" element={<ProtectedRoute><ProponentesPage /></ProtectedRoute>} />
              <Route path="/captacoes" element={<ProtectedRoute><CaptacoesPage /></ProtectedRoute>} />
              <Route path="/despesas" element={<ProtectedRoute><DespesasPage /></ProtectedRoute>} />
              <Route path="/conciliacao" element={<ProtectedRoute><ConciliacaoPage /></ProtectedRoute>} />
              <Route path="/relatorios" element={<ProtectedRoute><RelatoriosPage /></ProtectedRoute>} />
              <Route path="/alertas" element={<ProtectedRoute><AlertasPage /></ProtectedRoute>} />
              <Route path="/agenda" element={<ProtectedRoute><AgendaPage /></ProtectedRoute>} />
              <Route path="/documentos" element={<ProtectedRoute><DocumentosPage /></ProtectedRoute>} />
              <Route path="/usuarios" element={<ProtectedRoute><UsuariosPage /></ProtectedRoute>} />

              <Route path="/projeto/:id" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/importacao/:id" element={<ProtectedRoute><ImportacaoDetalhes /></ProtectedRoute>} />
              <Route path="/relatorio/:id" element={<ProtectedRoute><RelatorioPage /></ProtectedRoute>} />
              </Routes>
            </Suspense>
          </div>
        </main>
      </div>
    </ProjectProvider>
  );
}

export function App() {
  return <MainLayout />;
}
