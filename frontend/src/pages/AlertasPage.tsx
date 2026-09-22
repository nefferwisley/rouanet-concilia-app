import { Link } from "react-router-dom";
import { useProjectSelection } from "../context/ProjectContext";
import { DivergenciasPanel } from "../components/DivergenciasPanel";

export function AlertasPage() {
  const { projetoSelecionadoId, carregando, erro } = useProjectSelection();

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Central de Alertas e Notificações</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">Divergências financeiras verificadas no projeto selecionado.</p>
      </div>

      {carregando && <p role="status" className="card text-sm">Carregando projetos...</p>}
      {erro && !carregando && <p role="alert" className="card text-sm text-red-600">{erro}</p>}
      {!carregando && !erro && !projetoSelecionadoId && (
        <p className="card text-sm">Selecione um projeto para consultar suas divergências. <Link className="underline" to="/projetos">Ver projetos</Link></p>
      )}
      {!carregando && !erro && projetoSelecionadoId && <DivergenciasPanel key={projetoSelecionadoId} projetoId={projetoSelecionadoId} />}
    </div>
  );
}
