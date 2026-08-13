"""
dominio/ — regras de negócio puras da revisão financeira.

Nada aqui faz I/O (sem SQL, sem HTTP, sem filesystem) nem conhece um projeto
específico. É o que permite a mesma lógica servir o site, a exportação pra
planilha e um projeto novo sem duplicação.
"""
