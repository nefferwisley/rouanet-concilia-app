import { useRef, useState } from "react";

import { useAPI } from "../hooks/useAPI";
import { SalicConsulta } from "../components/SalicConsulta";
import { obterRegrasPlataforma } from "../lib/regrasPlataforma";

type FonteDados = "pasta" | "drive";

export function NovoProjetoModal({ onClose, onCriado }: { onClose: () => void; onCriado: () => void }) {
  const api = useAPI();
  const regras = obterRegrasPlataforma();
  const [form, setForm] = useState({
    pronac: "", nome: "", proponente: "", banco_nome: "", agencia: "", conta: "",
  });
  const [fonte, setFonte] = useState<FonteDados>("pasta");
  const [arquivos, setArquivos] = useState<File[]>([]);
  const [driveLink, setDriveLink] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const inputPastaRef = useRef<HTMLInputElement>(null);

  const set = (campo: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [campo]: e.target.value }));

  async function salvar() {
    if ((!form.pronac && regras.identificadorObrigatorio) || !form.nome) {
      setErro(`${regras.rotuloIdentificador} e Nome são obrigatórios.`);
      return;
    }
    if (form.pronac && !new RegExp(regras.formatoIdentificador).test(form.pronac)) {
      setErro(`${regras.rotuloIdentificador} não segue o formato configurado.`);
      return;
    }
    if (fonte === "pasta" && arquivos.length === 0) {
      setErro("Selecione a pasta com os arquivos-fonte do projeto (extrato, notas, comprovantes).");
      return;
    }
    if (fonte === "drive" && !driveLink.trim()) {
      setErro("Cole o link da pasta do Google Drive.");
      return;
    }

    setSalvando(true);
    setErro(null);
    try {
      const projeto = await api.post<{ id: string }>("/api/v1/projetos", form);

      // Fonte de dados é registrada logo na criação — ainda não processada
      // automaticamente (isso depende da Etapa 1/3 do processo de
      // conciliação, ver dashboard de status), mas já fica associada ao
      // projeto pra quando essa etapa existir.
      const docsForm = new FormData();
      if (fonte === "pasta") {
        arquivos.forEach((arq) => docsForm.append("arquivos", arq));
      } else {
        docsForm.append("drive_link", driveLink.trim());
      }
      await api.postForm(`/api/v1/documentos/projeto/${projeto.id}`, docsForm);

      onCriado();
      onClose();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao criar projeto.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="card w-full max-w-md space-y-3 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold">Novo Projeto</h2>
        <input className="input" placeholder={`${regras.rotuloIdentificador}${regras.identificadorObrigatorio ? " *" : ""}`} value={form.pronac} onChange={set("pronac")} />

        {regras.consultaSalicAtiva && <SalicConsulta
          pronacInicial={form.pronac}
          onProjetoEncontrado={(p) =>
            setForm((f) => ({
              ...f,
              pronac: p.pronac || f.pronac,
              nome: p.nome || f.nome,
              proponente: p.proponente || f.proponente,
            }))
          }
        />}

        <input className="input" placeholder="Nome do Projeto *" value={form.nome} onChange={set("nome")} />
        <input className="input" placeholder="Proponente" value={form.proponente} onChange={set("proponente")} />
        <input className="input" placeholder="Banco Captador" value={form.banco_nome} onChange={set("banco_nome")} />
        <div className="grid grid-cols-2 gap-2">
          <input className="input" placeholder="Agência" value={form.agencia} onChange={set("agencia")} />
          <input className="input" placeholder="Conta" value={form.conta} onChange={set("conta")} />
        </div>

        <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
          <label className="text-sm font-medium block mb-2">Fonte de dados do projeto *</label>
          <p className="text-xs text-slate-500 mb-2">
            Todos os arquivos aqui (extrato, notas fiscais, comprovantes) são a base pra conciliação deste projeto.
          </p>
          <div className="flex gap-4 text-sm mb-2">
            <label className="flex items-center gap-1">
              <input type="radio" checked={fonte === "pasta"} onChange={() => setFonte("pasta")} />
              Upar pasta de arquivos
            </label>
            <label className="flex items-center gap-1">
              <input type="radio" checked={fonte === "drive"} onChange={() => setFonte("drive")} />
              Link do Google Drive
            </label>
          </div>

          {fonte === "pasta" ? (
            <div>
              <input
                ref={inputPastaRef}
                type="file"
                // @ts-expect-error atributo não tipado, mas suportado pelos browsers
                webkitdirectory=""
                directory=""
                multiple
                onChange={(e) => setArquivos(Array.from(e.target.files ?? []))}
              />
              {arquivos.length > 0 && (
                <p className="text-xs text-slate-500 mt-1">{arquivos.length} arquivo(s) selecionado(s)</p>
              )}
            </div>
          ) : (
            <input
              className="input"
              placeholder="https://drive.google.com/drive/folders/..."
              value={driveLink}
              onChange={(e) => setDriveLink(e.target.value)}
            />
          )}
        </div>

        {erro && <p className="text-sm text-red-600">{erro}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button className="btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn-primary" onClick={salvar} disabled={salvando}>
            {salvando ? "Criando..." : "Criar"}
          </button>
        </div>
      </div>
    </div>
  );
}
