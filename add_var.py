import re
with open('frontend/src/pages/ProjetoDetalhes.tsx', 'r', encoding='utf-8') as f:
    code = f.read()
code = code.replace('const [importandoAutonomo, setImportandoAutonomo] = useState(false);', 'const [importandoAutonomo, setImportandoAutonomo] = useState(false);\n  const [erroImportacaoAutonoma, setErroImportacaoAutonoma] = useState<string | null>(null);')
with open('frontend/src/pages/ProjetoDetalhes.tsx', 'w', encoding='utf-8') as f:
    f.write(code)
