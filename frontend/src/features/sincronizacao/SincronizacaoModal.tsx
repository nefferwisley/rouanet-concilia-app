import React, { useRef, useState } from 'react';
import { useSincronizacao } from './SincronizacaoContext';

export function SincronizacaoModal({ projetoId, onClose }: { projetoId: string, onClose: () => void }) {
  const { state, iniciar, reset } = useSincronizacao();
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDrag(false);
    if (e.dataTransfer.files?.length) {
      iniciar(projetoId, e.dataTransfer.files);
    }
  };
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      iniciar(projetoId, e.target.files);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white p-6 rounded-lg shadow-xl w-96 relative">
        <button onClick={() => { reset(); onClose(); }} className="absolute top-2 right-2">X</button>
        <h2 className="text-xl font-bold mb-4">Sincronizar Documentos</h2>
        
        {state.status === 'idle' && (
          <div 
            onDragOver={e => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={"border-2 border-dashed p-8 text-center cursor-pointer " + (drag ? "border-blue-500 bg-blue-50" : "border-gray-300")}
          >
            <p>Arraste arquivos ou ZIP aqui</p>
            <input type="file" ref={inputRef} multiple onChange={handleFileChange} className="hidden" />
          </div>
        )}
        
        {state.status === 'uploading' && <p>Enviando...</p>}
        {state.status === 'processing' && <p>Processando extração e matching...</p>}
        {state.status === 'error' && <p className="text-red-600">Erro: {state.error}</p>}
        {state.status === 'done' && (
          <div>
            <p className="text-green-600 mb-4">Sincronização concluída!</p>
            <button onClick={onClose} className="bg-blue-600 text-white px-4 py-2 rounded">Ver Candidatos</button>
          </div>
        )}
      </div>
    </div>
  );
}
