import re

with open('frontend/src/components/ConfrontoSalic.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'get<ConfrontoResponse>(/api/v1/salic/confronto/ + projetoId)',
    'get<ConfrontoResponse>("/api/v1/salic/confronto/" + projetoId)'
)

with open('frontend/src/components/ConfrontoSalic.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
