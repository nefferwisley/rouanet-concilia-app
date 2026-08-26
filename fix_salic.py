import re

with open('frontend/src/components/ConfrontoSalic.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    '<div className={card border-l-4  + (temDivergencia ? "border-l-amber-500" : "border-l-emerald-500")}>',
    '<div className={"card border-l-4 " + (temDivergencia ? "border-l-amber-500" : "border-l-emerald-500")}>'
)

# It seems there are other issues. Let's see if there are other syntax errors.
with open('frontend/src/components/ConfrontoSalic.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
