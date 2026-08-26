import re

with open('frontend/src/pages/ProjetoDetalhes.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

old_tabs = r'<div className="bg-white dark:bg-navy-800 rounded-t-2xl border-b border-slate-100 dark:border-navy-700 overflow-x-auto shadow-sm">.*?</div>\s*</div>'
new_tabs = """<div className="bg-white dark:bg-navy-800 rounded-t-2xl border-b border-slate-100 dark:border-navy-700 overflow-x-auto shadow-sm">
        <div className="flex items-center gap-8 px-6">
          {ABAS.map((a) => (
            <button
              key={a.chave}
              onClick={() => setAba(a.chave)}
              className={`py-4 text-sm font-semibold transition-colors border-b-2 whitespace-nowrap ${
                aba === a.chave
                  ? "text-blue-700 dark:text-blue-400 border-blue-600 dark:border-blue-400"
                  : "text-slate-400 dark:text-slate-500 border-transparent hover:text-slate-600 dark:hover:text-slate-300"
              }`}
            >
              {a.rotulo}
            </button>
          ))}
        </div>
      </div>"""
code = re.sub(old_tabs, new_tabs, code, flags=re.DOTALL)

with open('frontend/src/pages/ProjetoDetalhes.tsx', 'w', encoding='utf-8') as f:
    f.write(code)
