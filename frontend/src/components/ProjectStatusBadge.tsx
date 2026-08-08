/**
 * RouanetConcilia — ProjectStatusBadge Component
 * Exibe status com cores e emojis
 */

import React from 'react';

interface ProjectStatusBadgeProps {
  status: 'iniciando' | 'em_progresso' | 'sucesso' | 'concluido' | 'erro';
}

const statusConfig: Record<string, { emoji: string; label: string; color: string }> = {
  iniciando: {
    emoji: '⏳',
    label: 'Iniciando',
    color: 'bg-gray-100 text-gray-700',
  },
  em_progresso: {
    emoji: '⚙️',
    label: 'Em Progresso',
    color: 'bg-blue-100 text-blue-700',
  },
  sucesso: {
    emoji: '✅',
    label: 'Sucesso',
    color: 'bg-green-100 text-green-700',
  },
  concluido: {
    emoji: '🎉',
    label: 'Concluído',
    color: 'bg-green-100 text-green-700',
  },
  erro: {
    emoji: '❌',
    label: 'Erro',
    color: 'bg-red-100 text-red-700',
  },
};

export const ProjectStatusBadge: React.FC<ProjectStatusBadgeProps> = ({ status }) => {
  const config = statusConfig[status] || statusConfig.erro;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded ${config.color}`}>
      <span>{config.emoji}</span>
      <span>{config.label}</span>
    </span>
  );
};

export default ProjectStatusBadge;
