import React, { createContext, useContext, useState, ReactNode } from 'react';
import { useAPI } from '../../hooks/useAPI';

interface SincronizacaoState {
  sincronizacaoId: string | null;
  status: 'idle' | 'uploading' | 'processing' | 'done' | 'error';
  progress: number;
  error?: string;
}

interface SincronizacaoContextData {
  state: SincronizacaoState;
  iniciar: (projetoId: string, files: FileList) => Promise<void>;
  reset: () => void;
}

const Context = createContext<SincronizacaoContextData | undefined>(undefined);

export function SincronizacaoProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SincronizacaoState>({ status: 'idle', sincronizacaoId: null, progress: 0 });
  const api = useAPI();

  const iniciar = async (projetoId: string, files: FileList) => {
    try {
      setState(s => ({ ...s, status: 'uploading', progress: 0 }));
      const formData = new FormData();
      Array.from(files).forEach(f => formData.append('arquivos', f));
      
      const res = await api.postForm<any>("/api/v1/projetos/" + projetoId + "/sincronizacoes-documentos", formData);
      
      const sincronizacao_id = res.sincronizacao_id;
      setState(s => ({ ...s, status: 'processing', sincronizacaoId: sincronizacao_id }));
      
      const poll = setInterval(async () => {
        try {
          const stRes = await api.get<any>("/api/v1/sincronizacoes-documentos/" + sincronizacao_id);
          if (stRes.status === 'concluida') {
            clearInterval(poll);
            setState(s => ({ ...s, status: 'done', progress: 100 }));
          } else if (stRes.status === 'erro') {
            clearInterval(poll);
            setState(s => ({ ...s, status: 'error', error: stRes.erro_operacional }));
          }
        } catch (e) {
          clearInterval(poll);
          setState(s => ({ ...s, status: 'error', error: 'Falha ao buscar status' }));
        }
      }, 2000);
    } catch (error: any) {
      setState(s => ({ ...s, status: 'error', error: error.message }));
    }
  };

  const reset = () => setState({ status: 'idle', sincronizacaoId: null, progress: 0 });

  return (
    <Context.Provider value={{ state, iniciar, reset }}>
      {children}
    </Context.Provider>
  );
}

export const useSincronizacao = () => {
  const ctx = useContext(Context);
  if (!ctx) throw new Error('useSincronizacao must be inside SincronizacaoProvider');
  return ctx;
};
