/**
 * RouanetConcilia — EditProjectModal Component
 * Edita um projeto existente via PATCH /api/v1/projetos/{id}
 */

import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useAPI } from '../hooks/useAPI';

interface EditProjectModalProps {
  projeto: {
    id: string;
    pronac: string;
    nome: string;
    proponente?: string;
    banco?: string;
  };
  onClose: () => void;
  onSaved: () => void;
}

export const EditProjectModal: React.FC<EditProjectModalProps> = ({
  projeto,
  onClose,
  onSaved,
}) => {
  const { token } = useAuth();
  const { patch: apiPatch } = useAPI(token);

  const [nome, setNome] = useState(projeto.nome);
  const [proponente, setProponente] = useState(projeto.proponente || '');
  const [banco, setBanco] = useState(projeto.banco || '');
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
      });

      console.log('✅ Projeto atualizado com sucesso');
      onClose();
      onSaved();
    } catch (err: any) {
      const message = err.message || 'Erro ao atualizar projeto';
      setError(message);
      console.error('❌ Erro:', message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md shadow-lg">
        <h2 className="text-lg font-semibold mb-4">Editar Projeto</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* PRONAC - Readonly */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              PRONAC (somente leitura)
            </label>
            <input
              type="text"
              value={projeto.pronac}
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-500"
            />
          </div>

          {/* Nome */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome *
            </label>
            <input
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Nome do projeto"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          {/* Proponente */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Proponente
            </label>
            <input
              type="text"
              value={proponente}
              onChange={(e) => setProponente(e.target.value)}
              placeholder="Nome do proponente"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Banco */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Banco
            </label>
            <input
              type="text"
              value={banco}
              onChange={(e) => setBanco(e.target.value)}
              placeholder="Nome do banco"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Erro */}
          {error && (
            <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">
              {error}
            </div>
          )}

          {/* Botões */}
          <div className="flex gap-2 justify-end pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-md transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading ? '⏳ Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditProjectModal;
