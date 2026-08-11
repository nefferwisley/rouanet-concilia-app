import { Navigate, Route, Routes } from "react-router-dom";

import { Header } from "./components/Header";
import { useAuth } from "./context/AuthContext";
import { ConciliacaoPage } from "./pages/ConciliacaoPage";
import { Dashboard } from "./pages/Dashboard";
import { ImportacaoDetalhes } from "./pages/ImportacaoDetalhes";
import { LoginPage } from "./pages/LoginPage";
import { ProjetoDetalhes } from "./pages/ProjetoDetalhes";
import { RelatorioPage } from "./pages/RelatorioPage";

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { token } = useAuth();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export function App() {
  return (
    <div className="min-h-screen">
      <Header />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/conciliacao"
          element={
            <ProtectedRoute>
              <ConciliacaoPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projeto/:id"
          element={
            <ProtectedRoute>
              <ProjetoDetalhes />
            </ProtectedRoute>
          }
        />
        <Route
          path="/importacao/:id"
          element={
            <ProtectedRoute>
              <ImportacaoDetalhes />
            </ProtectedRoute>
          }
        />
        <Route
          path="/relatorio/:id"
          element={
            <ProtectedRoute>
              <RelatorioPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  );
}
