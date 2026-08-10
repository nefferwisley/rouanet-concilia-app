/**
 * RouanetConcilia — ProjectStatusBadge Component
 * Exibe status com cores e emojis
 */

import React from 'react';

interface ProjectStatusBadgeProps {
  status: 'iniciando' | 'em_progresso' | 'sucesso' | 'concluido' | 'erro';
}

const statusConfig: Record<string, { emoji: string; label: string; pill: string }> = {
  iniciando: {
    emoji: '⏳',
    label: 'Iniciando',
    pill: 'pill-neutro',
  },
  em_progresso: {
    emoji: '⚙️',
    label: 'Em Progresso',
    pill: 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300',
  },
  sucesso: {
    emoji: '✅',
    label: 'Sucesso',
    pill: 'pill-sucesso',
  },
  concluido: {
    emoji: '🎉',
    label: 'Concluído',
    pill: 'pill-sucesso',
  },
  erro: {
    emoji: '❌',
    label: 'Erro',
    pill: 'pill-erro',
  },
};

export const ProjectStatusBadge: React.FC<ProjectStatusBadgeProps> = ({ status }) => {
  const config = statusConfig[status] || statusConfig.erro;

  return (
    <span className={`pill ${config.pill}`}>
      <span>{config.emoji}</span>
      <span>{config.label}</span>
    </span>
  );
};

export default ProjectStatusBadge;
