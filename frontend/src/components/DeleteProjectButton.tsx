/**
 * RouanetConcilia — DeleteProjectButton Component
 * Gerado via Llama3.2:1b + refinamento manual
 *
 * Props:
 *   projectId: string — ID do projeto a deletar
 *   onDeleted: () => void — Callback após sucesso
 */

import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useAPI } from '../hooks/useAPI';
import { Trash2 } from 'lucide-react';

interface DeleteProjectButtonProps {
  projectId: string;
  onDeleted?: () => void;
}

export const DeleteProjectButton: React.FC<DeleteProjectButtonProps> = ({
  projectId,
  onDeleted,
}) => {
  const { token } = useAuth();
  const { delete: apiDelete } = useAPI(token);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    setIsLoading(true);
    setError(null);

    try {
      await apiDelete(`/api/v1/projetos/${projectId}`);

      // Success toast (usar seu toast provider)
      console.log('✅ Projeto deletado com sucesso');

      setIsOpen(false);
      onDeleted?.();
    } catch (err: any) {
      const message = err.message || 'Erro ao deletar projeto';
      setError(message);
      console.error('❌ Erro:', message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Botão Delete */}
      <button
        onClick={() => setIsOpen(true)}
        disabled={isLoading}
        className="flex items-center gap-2 px-3 py-2 text-red-600 hover:bg-red-50 rounded-md transition-colors disabled:opacity-50"
        title="Deletar este projeto"
      >
        <Trash2 size={18} />
        <span>Deletar</span>
      </button>

      {/* Dialog de Confirmação */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm shadow-lg">
            <h2 className="text-lg font-semibold mb-2">Deletar Projeto?</h2>
            <p className="text-gray-600 mb-4">
              Esta ação é permanente. Todos os dados associados serão perdidos.
            </p>

            {error && (
              <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
                {error}
              </div>
            )}

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setIsOpen(false)}
                disabled={isLoading}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleDelete}
                disabled={isLoading}
                className="px-4 py-2 bg-red-600 text-white hover:bg-red-700 rounded-md transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isLoading ? '⏳ Deletando...' : 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default DeleteProjectButton;
