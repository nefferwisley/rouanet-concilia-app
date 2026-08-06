import { useState } from "react";

import { useAPI } from "../hooks/useAPI";

export function NovoProjetoModal({ onClose, onCriado }: { onClose: () => void; onCriado: () => void }) {
  const api = useAPI();
  const [form, setForm] = useState({
    pronac: "", nome: "", proponente: "", banco_nome: "", agencia: "", conta: "",
  });
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const set = (campo: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [campo]: e.target.value }));

  async function salvar() {
    if (!form.pronac || !form.nome) {
      setErro("PRONAC e Nome são obrigatórios.");
      return;
    }
    setSalvando(true);
    setErro(null);
    try {
      await api.post("/api/v1/projetos", form);
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
      <div className="card w-full max-w-md space-y-3">
        <h2 className="text-lg font-bold">Novo Projeto</h2>
        <input className="input" placeholder="PRONAC *" value={form.pronac} onChange={set("pronac")} />
        <input className="input" placeholder="Nome do Projeto *" value={form.nome} onChange={set("nome")} />
        <input className="input" placeholder="Proponente" value={form.proponente} onChange={set("proponente")} />
        <input className="input" placeholder="Banco Captador" value={form.banco_nome} onChange={set("banco_nome")} />
        <div className="grid grid-cols-2 gap-2">
          <input className="input" placeholder="Agência" value={form.agencia} onChange={set("agencia")} />
          <input className="input" placeholder="Conta" value={form.conta} onChange={set("conta")} />
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
