import re

with open('frontend/src/pages/ProjetoDetalhes.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace the top card with the mockup's Profile Card style
old_top_card = r'<div className="card">\s*<div className="flex flex-wrap justify-between items-start gap-4">.*?</div>\s*</div>'
new_top_card = """<div className="bg-white dark:bg-navy-800 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-navy-700 flex flex-wrap items-center justify-between mb-6 gap-4">
        <div className="flex items-center gap-6">
          <div className="w-20 h-20 rounded-full bg-slate-100 dark:bg-navy-900 border-4 border-white dark:border-navy-800 shadow-md flex items-center justify-center text-2xl font-bold text-slate-400 shrink-0">
            {projeto.pronac.substring(0,2)}
          </div>
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-2xl font-bold text-slate-900 dark:text-white">{projeto.nome}</h3>
              <span className="px-2.5 py-1 text-xs font-semibold text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-500/10 rounded-full border border-blue-100 dark:border-blue-500/20">{projeto.pronac}</span>
            </div>
            <div className="flex flex-wrap gap-8 text-sm">
              <div>
                <p className="text-slate-400 dark:text-slate-500 mb-1">Proponente:</p>
                <p className="font-medium dark:text-slate-200">{projeto.proponente || "Não informado"}</p>
              </div>
              <div>
                <p className="text-slate-400 dark:text-slate-500 mb-1">Banco Captador:</p>
                <p className="font-medium dark:text-slate-200">{projeto.banco || "Não informado"}</p>
              </div>
              <div>
                <p className="text-slate-400 dark:text-slate-500 mb-1">Controller:</p>
                <p className="font-medium dark:text-slate-200">{projeto.controller || "Não atribuído"}</p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="flex flex-col gap-2 shrink-0">
          <div className="flex gap-2 justify-end">
            <button
              className="px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-navy-600 hover:bg-slate-50 dark:hover:bg-navy-700 rounded-lg transition-colors"
              onClick={() => setMostrarEditar(true)}
            >
              Editar Projeto
            </button>
            <DeleteProjectButton projectId={projeto.id} onDeleted={() => {}} />
          </div>
          <div className="flex gap-2 justify-end mt-2">
             <button className="btn-primary" onClick={() => setMostrarImportar(true)}>+ Nova Importação</button>
             <button
               className="btn-primary bg-emerald-600 hover:bg-emerald-500 text-white font-bold transition-all shadow-sm"
               onClick={executarImportacaoAutonoma}
               disabled={importandoAutonomo}
             >
               {importandoAutonomo ? "Conciliando..." : "Importação Autônoma"}
             </button>
          </div>
          {erroImportacaoAutonoma && (
            <p className="text-xs text-red-600 dark:text-red-400 text-right mt-1">{erroImportacaoAutonoma}</p>
          )}
        </div>
      </div>"""
code = re.sub(old_top_card, new_top_card, code, flags=re.DOTALL)


# Replace tabs
old_tabs = r'<div className="flex gap-1 p-1 rounded-xl bg-slate-100 dark:bg-navy-900/70 overflow-x-auto">.*?</div>'
new_tabs = """<div className="bg-white dark:bg-navy-800 rounded-t-2xl border-b border-slate-100 dark:border-navy-700 overflow-x-auto shadow-sm">
        <div className="flex items-center gap-8 px-6">
          {ABAS.map((a) => (
            <button
              key={a.chave}
              onClick={() => setAba(a.chave)}
              className={py-4 text-sm font-semibold transition-colors border-b-2 whitespace-nowrap }
            >
              {a.rotulo}
            </button>
          ))}
        </div>
      </div>"""
code = re.sub(old_tabs, new_tabs, code, flags=re.DOTALL)

with open('frontend/src/pages/ProjetoDetalhes.tsx', 'w', encoding='utf-8') as f:
    f.write(code)
