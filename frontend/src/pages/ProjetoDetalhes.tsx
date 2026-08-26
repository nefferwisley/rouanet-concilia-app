import { useEffect, useState } from "react";
import { Link, useParams, useNavigate, useLocation } from "react-router-dom";

import { ImportarModal } from "./ImportarModal";
import { AuditoriaProjeto } from "../components/AuditoriaProjeto";
import { ConfrontoSalic } from "../components/ConfrontoSalic";
import { DemonstrativoSaldos } from "../components/DemonstrativoSaldos";
import { EditProjectModal } from "../components/EditProjectModal";
import { DeleteProjectButton } from "../components/DeleteProjectButton";
import { RevisaoDocumental } from "../components/RevisaoDocumental";
import { RevisaoManual } from "../components/RevisaoManual";
import { RevisaoPendentes } from "../components/RevisaoPendentes";
import { RevisaoDocumentosAmbiguos } from "../components/RevisaoDocumentosAmbiguos";
import { ConciliacaoManual } from "../components/ConciliacaoManual";
import { OrganizacaoDocumental } from "../components/OrganizacaoDocumental";
import { Regularizacao } from "../components/Regularizacao";
import { ChecklistFinal } from "../components/ChecklistFinal";
import { Dashboard } from "./Dashboard";
import { useAPI } from "../hooks/useAPI";
import { Projeto } from "../types";

const ABAS = [
  { chave: "visao-geral", rotulo: "Painel", emoji: "📊" },
  { chave: "lancamentos", rotulo: "Lançamentos e Auditoria", emoji: "📋" },
  { chave: "documentos", rotulo: "Documentos", emoji: "📑" },
  { chave: "entrega", rotulo: "Entrega Final", emoji: "📦" },
] as const;

type Aba = (typeof ABAS)[number]["chave"];

export function ProjetoDetalhes() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Extract active tab from URL path
  const pathParts = location.pathname.split('/');
  let aba: Aba = "visao-geral";
  const lastPart = pathParts[pathParts.length - 1];
  if (lastPart === "auditoria" || lastPart === "lancamentos") aba = "lancamentos";
  else if (lastPart === "documentos") aba = "documentos";
  else if (lastPart === "entrega") aba = "entrega";
  else if (lastPart === "visao-geral") aba = "visao-geral";

  const setAba = (novaAba: string) => {
    navigate(`/projetos/${id}/${novaAba}`);
  };  const api = useAPI();
  const [projeto, setProjeto] = useState<Projeto | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [mostrarImportar, setMostrarImportar] = useState(false);
  const [mostrarEditar, setMostrarEditar] = useState(false);
  const [importandoAutonomo, setImportandoAutonomo] = useState(false);
  const [erroImportacaoAutonoma, setErroImportacaoAutonoma] = useState<string | null>(null);
  
  const recarregarProjeto = () => {
    if (!id) return;
    setCarregando(true);
    setErro(null);
    api
      .get<Projeto>(`/api/v1/projetos/${id}`)
      .then((p) => {
        setProjeto(p);
        setCarregando(false);
      })
      .catch((e) => {
        // Antes, um erro aqui (token expirado, backend fora, 404) deixava a
        // tela presa em "Carregando..." pra sempre -- igual ao estado inicial,
        // sem diferença visível nenhuma. Agora mostra o motivo de verdade.
        setErro(e instanceof Error ? e.message : "Erro ao carregar projeto.");
        setCarregando(false);
      });
  };

  useEffect(() => {
    recarregarProjeto();
  }, [api, id]);

  const executarImportacaoAutonoma = async () => {
    if (!id) return;
    setErroImportacaoAutonoma(null);
    setImportandoAutonomo(true);
    try {
      const res = await api.post<{ conciliacao_id: string }>(`/api/v1/projetos/${id}/importar-autonomo`, {});
      const pollId = setInterval(async () => {
        try {
            const st = await api.get<{ status: string; erro?: string; erro_fatal?: string; mensagem?: string }>(`/api/v1/conciliacao/${res.conciliacao_id}`);
            if (st.status === "sucesso" || st.status === "concluido") {
              clearInterval(pollId);
              setImportandoAutonomo(false);
              setErroImportacaoAutonoma(null);
              recarregarProjeto();
            } else if (st.status === "erro") {
              clearInterval(pollId);
              setImportandoAutonomo(false);
              setErroImportacaoAutonoma(st.erro_fatal || st.erro || st.mensagem || "Erro no processamento autônomo.");
            }
        } catch (error) {
          clearInterval(pollId);
          setImportandoAutonomo(false);
          setErroImportacaoAutonoma(error instanceof Error ? error.message : "Falha ao consultar o processamento autônomo.");
        }
      }, 2000);
    } catch (err: unknown) {
      setImportandoAutonomo(false);
      setErroImportacaoAutonoma(err instanceof Error ? err.message : "Falha ao iniciar processamento autônomo.");
    }
  };

  if (erro) {
    return (
      <div className="max-w-3xl mx-auto p-6 space-y-3">
        <p className="text-sm text-red-600">{erro}</p>
        <button className="btn-secondary" onClick={recarregarProjeto}>
          🔄 Tentar novamente
        </button>
      </div>
    );
  }

  if (carregando || !projeto) {
    return (
      <div className="max-w-6xl mx-auto p-6 space-y-4 animate-pulse">
        <div className="h-20 card" />
        <div className="h-32 card" />
        <div className="h-48 card" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-4">
      <Link
        to="/"
        className="text-sm text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors inline-flex items-center gap-1"
      >
        ← Projetos
      </Link>

      <div className="bg-white dark:bg-navy-800 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-navy-700 flex flex-wrap items-center justify-between mb-6 gap-4">
        <div className="flex items-center gap-6">
          <div className="w-20 h-20 rounded-full bg-slate-100 dark:bg-navy-900 border-4 border-white dark:border-navy-800 shadow-md flex items-center justify-center text-2xl font-bold text-slate-400 shrink-0">
            {projeto.pronac.substring(0,2)}
          </div>
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-2xl font-bold text-slate-900 dark:text-white">{projeto.nome}</h3>
              <span className="px-2.5 py-1 text-xs font-semibold text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-500/10 rounded-full border border-blue-100 dark:border-blue-500/20">{projeto.pronac}</span>
            </div>
            <div className="flex flex-wrap gap-8 text-sm">
              <div>
                <p className="text-slate-400 dark:text-slate-500 mb-1">Proponente:</p>
                <p className="font-medium dark:text-slate-200">{projeto.proponente || "Não informado"}</p>
              </div>
              <div>
                <p className="text-slate-400 dark:text-slate-500 mb-1">Banco Captador:</p>
                <p className="font-medium dark:text-slate-200">{projeto.banco || "Não informado"}</p>
              </div>
              <div>
                <p className="text-slate-400 dark:text-slate-500 mb-1">Controller:</p>
                <p className="font-medium dark:text-slate-200">{projeto.controller || "Não atribuído"}</p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="flex flex-col gap-2 shrink-0">
          <div className="flex gap-2 justify-end">
            <button
              className="px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-navy-600 hover:bg-slate-50 dark:hover:bg-navy-700 rounded-lg transition-colors"
              onClick={() => setMostrarEditar(true)}
            >
              Editar Projeto
            </button>
            <DeleteProjectButton projectId={projeto.id} onDeleted={() => {}} />
          </div>
          <div className="flex gap-2 justify-end mt-2">
             <button className="btn-primary" onClick={() => setMostrarImportar(true)}>+ Nova Importação</button>
             <button
               className="btn-primary bg-emerald-600 hover:bg-emerald-500 text-white font-bold transition-all shadow-sm"
               onClick={executarImportacaoAutonoma}
               disabled={importandoAutonomo}
             >
               {importandoAutonomo ? "Conciliando..." : "Importação Autônoma"}
             </button>
          </div>
          {erroImportacaoAutonoma && (
            <p role="alert" className="text-xs text-red-600 dark:text-red-400 text-right mt-1">{erroImportacaoAutonoma}</p>
          )}
        </div>
      </div>

      <DemonstrativoSaldos projetoId={projeto.id} />

      <ConfrontoSalic projetoId={projeto.id} />

      <div className="bg-white dark:bg-navy-800 rounded-t-2xl border-b border-slate-100 dark:border-navy-700 overflow-x-auto shadow-sm">
        <div className="flex items-center gap-8 px-6">
          {ABAS.map((a) => (
            <button
              key={a.chave}
              onClick={() => setAba(a.chave)}
              className={`py-4 text-sm font-semibold transition-colors border-b-2 whitespace-nowrap ${
                aba === a.chave
                  ? "text-blue-700 dark:text-blue-400 border-blue-600 dark:border-blue-400"
                  : "text-slate-400 dark:text-slate-500 border-transparent hover:text-slate-600 dark:hover:text-slate-300"
              }`}
            >
              {a.rotulo}
            </button>
          ))}
        </div>
      </div>

      <div className={aba === "visao-geral" ? "space-y-4" : "hidden"}>
        <Dashboard />
      </div>

      <div className={aba === "lancamentos" ? "space-y-4" : "hidden"}>
        <AuditoriaProjeto projetoId={projeto.id} />
      </div>


      <div className={aba === "documentos" ? "space-y-4" : "hidden"}>
        <RevisaoPendentes projetoId={projeto.id} />
        <RevisaoDocumentosAmbiguos projetoId={projeto.id} />
        <RevisaoDocumental projetoId={projeto.id} />
        <RevisaoManual projetoId={projeto.id} />
      </div>

      <div className={aba === "entrega" ? "space-y-4" : "hidden"}>
        <OrganizacaoDocumental projetoId={projeto.id} />
        <Regularizacao projetoId={projeto.id} />
        <ChecklistFinal projetoId={projeto.id} />
      </div>

      {mostrarImportar && (
        <ImportarModal
          projetos={[projeto]}
          onClose={() => setMostrarImportar(false)}
          onImported={() => {
            setMostrarImportar(false);
            recarregarProjeto();
          }}
        />
      )}

      {mostrarEditar && projeto && (
        <EditProjectModal
          projeto={projeto}
          onClose={() => setMostrarEditar(false)}
          onSaved={() => {
            setMostrarEditar(false);
            recarregarProjeto();
          }}
        />
      )}
    </div>
  );
}
