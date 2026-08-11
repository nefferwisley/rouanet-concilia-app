#!/usr/bin/env python3
"""
Orquestrador Distribuído: Auditoria 1961 com 2 PCs
PC Local (localhost:11434): Hermes - análise, execução
PC Remoto (192.168.1.102:11434): qwen2.5-coder - geração de código
"""

import requests
import json
import time
import subprocess
import sys
from pathlib import Path

# Configuração
PC_LOCAL = "http://localhost:11434"
PC_REMOTO = "http://192.168.1.102:11434"

class OrquestradorDistribuido:
    def __init__(self):
        print("🚀 Inicializando Orquestrador com 2 PCs\n")
        self.local_models = self.get_modelos(PC_LOCAL)
        self.remoto_models = self.get_modelos(PC_REMOTO)

        print(f"✓ PC Local ({PC_LOCAL}):")
        for m in self.local_models:
            print(f"  - {m}")

        print(f"\n✓ PC Remoto ({PC_REMOTO}):")
        for m in self.remoto_models:
            print(f"  - {m}")

        if not self.local_models or not self.remoto_models:
            print("\n❌ ERRO: Um dos PCs não tem modelos!")
            sys.exit(1)

    def get_modelos(self, url):
        """Lista modelos disponíveis em um PC"""
        try:
            r = requests.get(f"{url}/api/tags", timeout=5)
            return [m['name'] for m in r.json()['models']]
        except Exception as e:
            print(f"  ⚠️  Erro ao conectar {url}: {e}")
            return []

    def step1_analise_local(self):
        """STEP 1: PC Local (Hermes) analisa estrutura da planilha"""
        print("\n" + "="*60)
        print("📊 STEP 1: Análise da Planilha (PC Local - Hermes)")
        print("="*60)

        try:
            with open('_parsed/planilha.json', 'r', encoding='utf-8') as f:
                planilha = json.load(f)
        except FileNotFoundError:
            print("❌ Arquivo _parsed/planilha.json não encontrado!")
            return None

        try:
            with open('_parsed/extrato.json', 'r', encoding='utf-8') as f:
                extrato = json.load(f)
        except FileNotFoundError:
            print("⚠️  Arquivo _parsed/extrato.json não encontrado (OK, pode ser criado)")
            extrato = []

        prompt = f"""Analise rapidamente esses dados e responda em JSON:

PLANILHA (amostra):
- Total de linhas: {len(planilha)}
- Campos: {list(planilha[0].keys()) if planilha else 'vazio'}
- Primeira linha: {planilha[0] if planilha else 'N/A'}

EXTRATO (amostra):
- Total de movimentos: {len(extrato)}
- Campos: {list(extrato[0].keys()) if extrato else 'vazio'}

Perguntas:
1. Estrutura está OK?
2. Campos críticos presentes (valor, data, favorecido)?
3. Quais campos podem ter divergências?
4. Estratégia de matching recomendada?

Responda APENAS em JSON válido:
{{
  "planilha_ok": true/false,
  "extrato_ok": true/false,
  "campos_criticos": [...],
  "campos_divergencia": [...],
  "estrategia": "..."
}}"""

        print("→ Enviando análise para Hermes...")

        try:
            response = requests.post(
                f"{PC_LOCAL}/api/generate",
                json={"model": "hermes", "prompt": prompt, "stream": False},
                timeout=30
            )

            resultado_texto = response.json()['response']

            # Tenta extrair JSON
            try:
                resultado = json.loads(resultado_texto)
                print("✓ Análise concluída:")
                print(f"  - Planilha OK: {resultado.get('planilha_ok', '?')}")
                print(f"  - Extrato OK: {resultado.get('extrato_ok', '?')}")
                print(f"  - Campos críticos: {resultado.get('campos_criticos', [])}")
                print(f"  - Estratégia: {resultado.get('estrategia', '?')}")
            except:
                print("✓ Análise concluída (texto):")
                print(resultado_texto[:300] + "..." if len(resultado_texto) > 300 else resultado_texto)
                resultado = {"raw": resultado_texto}

            return resultado

        except Exception as e:
            print(f"❌ Erro ao chamar Hermes: {e}")
            return None

    def step2_gerar_codigo_remoto(self):
        """STEP 2: PC Remoto (qwen2.5-coder) gera código de reconciliação"""
        print("\n" + "="*60)
        print("💻 STEP 2: Gerar Código de Reconciliação (PC Remoto - qwen2.5-coder)")
        print("="*60)

        prompt = """Gere uma função Python COMPLETA e FUNCIONAL que reconcilia planilha com extrato.

Requisitos:
1. Entrada: dois JSONs (planilha e extrato)
2. Saída: dicionário com resultado da reconciliação
3. Lógica:
   - Matching exato (valor + data + favorecido)
   - Fuzzy matching se não achar exato (usar difflib, score > 0.85)
   - Tolerância: R$ 0,02 (centavos)
   - Zero data loss: registrar quarentena
4. Retornar JSON:
   {
     "conciliadas": 485,
     "divergencias": [...],
     "quarentena": [...],
     "taxa_reconciliacao": 97%
   }

IMPORTANTE:
- Código deve ser executável direto
- Usar apenas libs padrão (json, difflib, decimal)
- Sem comentários longos, código limpo
- Função main() que lê _parsed/planilha.json e _parsed/extrato.json

Gere APENAS código Python, sem explicações:"""

        print("→ Enviando para qwen2.5-coder:14b...")

        try:
            response = requests.post(
                f"{PC_REMOTO}/api/generate",
                json={
                    "model": "qwen2.5-coder:14b",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )

            codigo = response.json()['response']

            # Salva código gerado
            output_path = Path('motor/reconciliar_auto.py')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(codigo)

            print(f"✓ Código gerado e salvo em {output_path}")
            print(f"  Tamanho: {len(codigo)} caracteres")

            return codigo

        except Exception as e:
            print(f"❌ Erro ao chamar qwen2.5-coder: {e}")
            return None

    def step3_executar_local(self):
        """STEP 3: PC Local executa código gerado"""
        print("\n" + "="*60)
        print("⚡ STEP 3: Executar Código (PC Local)")
        print("="*60)

        script_path = Path('motor/reconciliar_auto.py')

        if not script_path.exists():
            print(f"❌ Script não encontrado: {script_path}")
            return None

        print(f"→ Executando {script_path}...")

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(Path.cwd())
            )

            if result.returncode == 0:
                print("✓ Execução bem-sucedida!")
                print(f"\nSaída:")
                print(result.stdout)
                return result.stdout
            else:
                print(f"❌ Erro na execução:")
                print(result.stderr)
                return None

        except subprocess.TimeoutExpired:
            print("❌ Script demorou > 5 minutos (timeout)")
            return None
        except Exception as e:
            print(f"❌ Erro ao executar: {e}")
            return None

    def step4_validar_resultado(self):
        """STEP 4: PC Local valida resultado"""
        print("\n" + "="*60)
        print("✅ STEP 4: Validar Resultado (PC Local)")
        print("="*60)

        relatorio_path = Path('saida/relatorios/auditoria_1961.md')

        if relatorio_path.exists():
            with open(relatorio_path, 'r', encoding='utf-8') as f:
                relatorio = f.read()

            print(f"✓ Relatório gerado: {relatorio_path}")
            print(f"  Tamanho: {len(relatorio)} bytes")
            print(f"\nPrimeiras 500 caracteres:")
            print(relatorio[:500])

            return {"ok": True, "path": str(relatorio_path)}
        else:
            print(f"⚠️  Relatório não encontrado: {relatorio_path}")
            return {"ok": False}

    def executar_pipeline(self):
        """Executa pipeline completo"""
        print("\n🎯 ORQUESTRAÇÃO COM 2 PCs - INICIADA\n")

        start_time = time.time()

        try:
            # Step 1: Análise
            resultado_1 = self.step1_analise_local()
            if not resultado_1:
                print("\n⚠️  Step 1 falhou, continuando mesmo assim...")

            # Step 2: Geração de código
            resultado_2 = self.step2_gerar_codigo_remoto()
            if not resultado_2:
                print("\n❌ Step 2 falhou - não há código para executar")
                return False

            # Step 3: Execução
            resultado_3 = self.step3_executar_local()
            if not resultado_3:
                print("\n❌ Step 3 falhou - código não executou")
                return False

            # Step 4: Validação
            resultado_4 = self.step4_validar_resultado()

            elapsed = time.time() - start_time

            print("\n" + "="*60)
            print("✅ PIPELINE CONCLUÍDO COM SUCESSO")
            print("="*60)
            print(f"Tempo total: {elapsed:.1f} segundos")
            print(f"\n📁 Arquivos gerados:")
            print(f"  - motor/reconciliar_auto.py (código gerado)")
            print(f"  - saida/relatorios/auditoria_1961.md (relatório)")
            print(f"\n🎯 Próximo passo: VALIDAR RESULTADO E CORRIGIR DIVERGÊNCIAS")

            return True

        except Exception as e:
            print(f"\n❌ Erro geral: {e}")
            return False

def main():
    try:
        orquestrador = OrquestradorDistribuido()
        sucesso = orquestrador.executar_pipeline()

        if sucesso:
            print("\n✅ Auditoria concluída!")
            print("   Abra saida/relatorios/auditoria_1961.md para ver divergências")
            sys.exit(0)
        else:
            print("\n❌ Auditoria falhou em algum ponto")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
