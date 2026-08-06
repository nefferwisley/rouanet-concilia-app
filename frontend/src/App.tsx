import { Route, Routes } from "react-router-dom";

import { Header } from "./components/Header";
import { Dashboard } from "./pages/Dashboard";
import { ImportacaoDetalhes } from "./pages/ImportacaoDetalhes";
import { ProjetoDetalhes } from "./pages/ProjetoDetalhes";
import { RelatorioPage } from "./pages/RelatorioPage";

export function App() {
  return (
    <div className="min-h-screen">
      <Header />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projeto/:id" element={<ProjetoDetalhes />} />
        <Route path="/importacao/:id" element={<ImportacaoDetalhes />} />
        <Route path="/relatorio/:id" element={<RelatorioPage />} />
      </Routes>
    </div>
  );
}
