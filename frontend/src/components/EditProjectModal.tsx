/**
 * RouanetConcilia — EditProjectModal Component
 * Edita um projeto existente via PATCH /api/v1/projetos/{id}
 */

import React, { useState } from 'react';
import { useAPI } from '../hooks/useAPI';

interface EditProjectModalProps {
  projeto: {
    id: string;
    pronac: string;
    nome: string;
    proponente?: string;
    banco?: string;
    valor_captado?: number | null;
  };
  onClose: () => void;
  onSaved: () => void;
}

export const EditProjectModal: React.FC<EditProjectModalProps> = ({
  projeto,
  onClose,
  onSaved,
}) => {
  const { patch: apiPatch } = useAPI();

  const [nome, setNome] = useState(projeto.nome);
  const [proponente, setProponente] = useState(projeto.proponente || '');
  const [banco, setBanco] = useState(projeto.banco || '');
  const [valorCaptado, setValorCaptado] = useState(
    projeto.valor_captado != null ? String(projeto.valor_captado) : ''
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!nome.trim()) {
      setError('Nome não pode estar vazio');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await apiPatch(`/api/v1/projetos/${projeto.id}`, {
        nome: nome.trim(),
        proponente: proponente.trim() || undefined,
        banco: banco.trim() || undefined,
        valor_captado: valorCaptado.trim() ? Number(valorCaptado.trim()) : undefined,
      });

      onClose();
      onSaved();
    } catch (err: any) {
      const message = err.message || 'Erro ao atualizar projeto';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md">
        <h2 className="text-lg font-bold tracking-tight mb-4">Editar Projeto</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium block mb-1">PRONAC (somente leitura)</label>
            <input type="text" value={projeto.pronac} disabled className="input opacity-60 cursor-not-allowed" />
          </div>

          <div>
            <label className="text-sm font-medium block mb-1">Nome *</label>
            <input
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Nome do projeto"
              className="input"
              required
            />
          </div>

          <div>
            <label className="text-sm font-medium block mb-1">Proponente</label>
            <input
              type="text"
              value={proponente}
              onChange={(e) => setProponente(e.target.value)}
              placeholder="Nome do proponente"
              className="input"
            />
          </div>

          <div>
            <label className="text-sm font-medium block mb-1">Banco</label>
            <input
              type="text"
              value={banco}
              onChange={(e) => setBanco(e.target.value)}
              placeholder="Nome do banco"
              className="input"
            />
          </div>

          <div>
            <label className="text-sm font-medium block mb-1">Valor total captado (R$)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={valorCaptado}
              onChange={(e) => setValorCaptado(e.target.value)}
              placeholder="Ex: 835000.00"
              className="input"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Valor efetivamente recebido (depósito do patrocinador) — confira contra o extrato/planilha oficial antes de preencher.
            </p>
          </div>

          {error && (
            <div className="p-3 rounded-lg text-sm bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400">
              {error}
            </div>
          )}

          <div className="flex gap-2 justify-end pt-2">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoading}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? '⏳ Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditProjectModal;
