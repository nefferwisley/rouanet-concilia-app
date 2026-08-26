import React, { useEffect, useState } from 'react';
import { useAPI } from '../../hooks/useAPI';
import { useAuth } from '../../context/AuthContext';

interface Candidato {
  id: string;
  documento_id: string;
  transacao_id: string;
  score_total: number;
  decisao: string;
  nome_exibicao: string;
}

function Thumbnail({ documentoId }: { documentoId: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const { token } = useAuth();
  
  useEffect(() => {
    let active = true;
    
    // We cannot use useAPI for raw binary responses cleanly if it assumes JSON,
    // so we fetch directly with the token
    const fetchThumb = async () => {
      try {
        const res = await fetch("/api/v1/documentos-sincronizacao/" + documentoId + "/thumbnail", {
          headers: {
            'Authorization': 'Bearer ' + token
          }
        });
        if (res.status === 200 && active) {
          const blob = await res.blob();
          setUrl(URL.createObjectURL(blob));
        }
      } catch (e) {}
    };
    fetchThumb();
    
    return () => { active = false; };
  }, [documentoId, token]);

  if (!url) return <div className="w-32 h-32 bg-gray-100 flex items-center justify-center text-xs text-gray-400">Sem preview</div>;
  return <img src={url} alt="Thumbnail" className="w-32 h-32 object-cover border" />;
}

export function RevisaoCandidatos({ sincronizacaoId }: { sincronizacaoId: string }) {
  const [candidatos, setCandidatos] = useState<Candidato[]>([]);
  const api = useAPI();
  
  useEffect(() => {
    api.get<Candidato[]>("/api/v1/sincronizacoes-documentos/" + sincronizacaoId + "/candidatos")
      .then(data => setCandidatos(data));
  }, [sincronizacaoId, api]);

  const acao = async (id: string, tipo: 'confirmar' | 'rejeitar' | 'desfazer') => {
    await api.post("/api/v1/candidatos-documento/" + id + "/" + tipo, {});
    setCandidatos(prev => prev.map(c => 
      c.id === id ? { ...c, decisao: tipo === 'desfazer' ? 'automatico' : (tipo === 'confirmar' ? 'confirmado' : 'rejeitado') } : c
    ));
  };

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4">Revisão de Candidatos</h2>
      <div className="flex flex-col gap-4">
        {candidatos.map(c => (
          <div key={c.id} className="border p-4 flex gap-4 bg-white shadow-sm rounded-lg">
            <Thumbnail documentoId={c.documento_id} />
            <div className="flex-1">
              <p className="font-semibold">{c.nome_exibicao}</p>
              <p className="text-sm text-gray-600">Score: {c.score_total}</p>
              <p className="text-sm">Status: <span className="font-medium">{c.decisao}</span></p>
              
              <div className="mt-4 flex gap-2">
                {c.decisao !== 'confirmado' && (
                  <button onClick={() => acao(c.id, 'confirmar')} className="px-3 py-1 bg-green-600 text-white rounded text-sm">Confirmar</button>
                )}
                {c.decisao !== 'rejeitado' && (
                  <button onClick={() => acao(c.id, 'rejeitar')} className="px-3 py-1 bg-red-600 text-white rounded text-sm">Rejeitar</button>
                )}
                {(c.decisao === 'confirmado' || c.decisao === 'rejeitado') && (
                  <button onClick={() => acao(c.id, 'desfazer')} className="px-3 py-1 bg-gray-500 text-white rounded text-sm">Desfazer</button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
