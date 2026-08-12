"""
Configuração Phidata para OrquestradorConcilia Rouanet
Agentes especializados para: Conciliação, Auditoria, Importação, Reconciliação

Seleção de modelo (mesmo padrão de fallback usado em backend/config.py
para OCR): usa Gemini se GOOGLE_API_KEY estiver definida (tier gratuito
da Google), senão cai para Ollama local (qwen2.5-coder, já rodando no
host em localhost:11434 — sem custo, sem chave).
"""

from phi.agent import Agent
from phi.model.google import Gemini
from phi.model.ollama import Ollama
import json
import os
import psycopg2
import psycopg2.extras


# Host do Ollama visto de DENTRO do container Docker. No Windows/Mac com
# Docker Desktop, host.docker.internal resolve pro host automaticamente.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
# Modelo pequeno de propósito: a GPU disponível (930M, VRAM mínima) leva
# minutos por chamada com o 7B. O 1.5b responde em segundos, com queda de
# qualidade aceitável pra orquestrar/testar o fluxo.
OLLAMA_MODEL_ID = os.getenv("OLLAMA_MODEL_ID", "qwen2.5-coder:1.5b")
GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash-exp")
# Sem isso, o qwen2.5-coder (modelo de código) não converge sozinho pra um
# "fim" em prompts abertos em português (ex.: "audite e liste validações")
# — ele gera token após token sem parar até bater o limite de contexto
# (8192), levando minutos. Confirmado via teste isolado: com num_predict=40
# a chamada terminou em 9.6s com done_reason="length" (bateu o teto, não
# parou natural). 400 tokens é um teto razoável pro tamanho de relatório
# que os agentes geram aqui, a ~8 tok/s nesse hardware (~50s no pior caso).
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))
# O padrão de OLLAMA_NUM_GPU agora é None (auto-detecção do Ollama). 
# Caso queira forçar CPU ou GPU específica, configure no ambiente (ex: OLLAMA_NUM_GPU=0 para CPU).
OLLAMA_NUM_GPU_ENV = os.getenv("OLLAMA_NUM_GPU")
if OLLAMA_NUM_GPU_ENV is not None:
    try:
        OLLAMA_NUM_GPU = int(OLLAMA_NUM_GPU_ENV)
    except ValueError:
        OLLAMA_NUM_GPU = None
else:
    OLLAMA_NUM_GPU = None


def _gemini_key_valida(chave: str) -> bool:
    """Chaves reais do Gemini (aistudio.google.com/apikey) começam com
    AIzaSy e têm 39 caracteres. Contas afetadas pelo bug atual do Google
    (ago/2026) só emitem chaves no formato "AQ." — essas são rejeitadas
    pela API REST, então tratamos como ausente e caímos pro Ollama."""
    return chave.startswith("AIzaSy") and len(chave) == 39


def criar_modelo():
    """Gemini se houver chave válida (tier gratuito), senão Ollama local."""
    google_api_key = os.getenv("GOOGLE_API_KEY", "")
    if _gemini_key_valida(google_api_key):
        return Gemini(id=GEMINI_MODEL_ID, api_key=google_api_key)
    # keep_alive alto: recarregar o modelo do zero custa dezenas de
    # segundos neste hardware — vale manter residente em memória por
    # mais tempo entre chamadas em vez do default (~5min).
    options = {"num_predict": OLLAMA_NUM_PREDICT}
    if OLLAMA_NUM_GPU is not None:
        options["num_gpu"] = OLLAMA_NUM_GPU

    return Ollama(
        id=OLLAMA_MODEL_ID,
        host=OLLAMA_HOST,
        keep_alive="30m",
        # O cliente `ollama` (httpx) NÃO tem timeout por padrão (None). Se o
        # servidor atolar (já aconteceu: 4 llama-server órfãos acumulados +
        # request de 3832 tokens preso no slot único -> requests filavam e
        # pareciam travar pra sempre), o Agent.run() bloquearia eternamente
        # e o endpoint FastAPI penduraria sem resposta. Com timeout, o
        # OllamaError estoura e o erro chega limpo ao cliente. 300s é
        # folgado pra este hardware (~72s por chamada em CPU), mas trava o
        # hang infinito.
        timeout=300,
        options=options,
    )


# ============================================================================
# TOOLS — acesso real ao banco (schema em db/migrations/0001_schema.sql)
#
# Sem isso os agentes só "conversam" sobre o assunto — o Agent.run() não
# tem nenhuma forma de ver dados reais do projeto, então o LLM inventa uma
# resposta plausível a partir só do texto da instrução. Cada função vira
# uma tool que o phidata expõe ao modelo (docstring + type hints viram o
# schema da tool automaticamente); o modelo decide quando chamar.
#
# projeto_id é uuid (texto) na tabela `projetos`, não int — corrigido aqui
# e em toda a cadeia de chamada (routes/orquestrador.py incluído).
# ============================================================================

_LIMITE_LINHAS_TOOL = 20  # nº de linhas por consulta — prompt pequeno, hardware fraco


def _conectar_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def _query_json(sql: str, params: tuple) -> str:
    """Roda a query e devolve os resultados como JSON (texto) pro agente ler."""
    try:
        with _conectar_db() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            linhas = cur.fetchall()
    except Exception as e:  # noqa: BLE001 — erro de DB vira texto pro agente, não crash
        return json.dumps({"erro": str(e)}, ensure_ascii=False)

    resultado = [dict(r) for r in linhas]
    # Decimal/date/datetime não serializam direto em JSON — normaliza pra string.
    resultado = json.loads(json.dumps(resultado, default=str, ensure_ascii=False))
    if not resultado:
        return json.dumps({"aviso": "Nenhum registro encontrado para esse projeto_id."}, ensure_ascii=False)
    return json.dumps(resultado, ensure_ascii=False)


def buscar_projeto(projeto_id: str) -> str:
    """Busca os dados básicos do projeto Lei Rouanet: PRONAC, nome, proponente, banco."""
    return _query_json(
        "select pronac, nome, proponente, controller, banco, data_inicio, data_fim "
        "from projetos where id = %s",
        (projeto_id,),
    )


def buscar_transacoes(projeto_id: str) -> str:
    """Busca as transações (pagamentos) do projeto: fornecedor, CNPJ, valores, status de conciliação."""
    return _query_json(
        "select fornecedor, cnpj_fornecedor, data_pagamento, valor_bruto, valor_liquido, "
        "tem_nf, tem_comprovante, status, score_conciliacao "
        "from transacoes where projeto_id = %s order by data_pagamento desc limit %s",
        (projeto_id, _LIMITE_LINHAS_TOOL),
    )


def buscar_rubricas(projeto_id: str) -> str:
    """Busca as rubricas orçamentárias do projeto: código, descrição, valor orçado."""
    return _query_json(
        "select codigo, descricao, valor_orcado from rubricas where projeto_id = %s order by codigo limit %s",
        (projeto_id, _LIMITE_LINHAS_TOOL),
    )


def buscar_extrato_movimentos(projeto_id: str) -> str:
    """Busca os movimentos do extrato bancário do projeto (via conta captadora): data, histórico, valor, status."""
    return _query_json(
        "select m.data, m.historico, m.tipo, m.valor, m.status_conciliacao "
        "from extrato_movimentos m "
        "join contas_captadoras c on c.id = m.conta_id "
        "where c.projeto_id = %s order by m.data desc limit %s",
        (projeto_id, _LIMITE_LINHAS_TOOL),
    )


def buscar_campos_revisao(projeto_id: str) -> str:
    """Busca campos incertos pendentes de revisão manual (baixa confiança de matching) do projeto."""
    return _query_json(
        "select cr.campo, cr.valor_extraido, cr.confianca, cr.status_revisao "
        "from campos_revisao cr "
        "join transacoes t on t.id = cr.transacao_id "
        "where t.projeto_id = %s and cr.status_revisao = 'PENDENTE' limit %s",
        (projeto_id, _LIMITE_LINHAS_TOOL),
    )


# ============================================================================
# 1. CONHECIMENTO (Knowledge Bases)
# ============================================================================

def criar_conhecimento_lei_rouanet():
    """Retorna conhecimento sobre Lei Rouanet como string"""
    return """
    LEI ROUANET - Conhecimento Base

    RUBRICAS PRINCIPAIS:
    - 01: Recursos Humanos
    - 02: Serviços Pessoa Jurídica
    - 03: Serviços Pessoa Física
    - 04: Compras
    - 05: Despesas com Viagem

    VALIDAÇÕES:
    - CPF: 11 dígitos, checksum válido
    - CNPJ: 14 dígitos, checksum válido
    - Data: formato DD/MM/YYYY ou YYYY-MM-DD
    - Valor: numérico positivo

    CONFORMIDADE:
    - Todos os beneficiários devem estar documentados
    - Despesas devem estar vinculadas a rubricas válidas
    - Extratos devem ser conciliados com documentação
    """


# ============================================================================
# 2. AGENTES ESPECIALIZADOS
# ============================================================================

class AgenteConciliacao:
    """Agente especializado em reconciliação de extratos com planilhas"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conhecimento = criar_conhecimento_lei_rouanet()

        # NOTA: sem tools=[...] aqui de propósito. Testado e confirmado que
        # qwen2.5-coder:1.5b não invoca function calling de verdade via
        # Ollama (message.tool_calls vem None, o modelo só escreve texto
        # parecido com JSON de chamada de função). Em vez de depender do
        # modelo "decidir" chamar uma tool, os dados reais são buscados em
        # Python e injetados direto no prompt — determinístico, não depende
        # da confiabilidade de tool-calling de um modelo pequeno.
        self.agent = Agent(
            name="Agente Conciliação",
            role="Especialista em reconciliação de Lei Rouanet",
            model=criar_modelo(),
            description="""
            Responsável por:
            - Analisar divergências entre planilhas e extratos
            - Propor estratégias de reconciliação
            - Identificar rubricas corretas (via matching determinístico e RAG)
            - Revisar campos incertos
            - Gerar relatórios de conciliação
            """,
            instructions=[
                "Sempre usar conhecimento Lei Rouanet",
                "Os dados reais do projeto (transações, extrato, rubricas) já vêm no prompt — nunca invente valores além deles",
                "Propor soluções específicas para cada divergência",
                "Usar terminologia oficial Lei Rouanet",
                "Validar CPF/CNPJ quando necessário",
                "Seja extremamente objetivo e conciso. Responda apenas com tabelas ou pontos de ação diretos, limitando o relatório a no máximo 150 palavras. Não inclua introduções, explicações longas ou conclusões.",
                f"Conhecimento base: {self.conhecimento}"
            ],
        )

    def reconciliar_projeto(self, projeto_id: str, estrategia="hibrida"):
        """Executa reconciliação inteligente"""
        transacoes = buscar_transacoes(projeto_id)
        extrato = buscar_extrato_movimentos(projeto_id)
        rubricas = buscar_rubricas(projeto_id)
        prompt = f"""
        Reconcilie o projeto {projeto_id} usando estratégia '{estrategia}':

        TRANSAÇÕES DO PROJETO:
        {transacoes}

        MOVIMENTOS DO EXTRATO BANCÁRIO:
        {extrato}

        RUBRICAS ORÇAMENTÁRIAS:
        {rubricas}

        Com base SOMENTE nos dados acima, gere um relatório ultra-curto (máximo 150 palavras) e focado:
        1. Identifique divergências críticas entre transações e extrato (com valores/datas)
        2. Liste rubricas problemáticas
        3. Ações recomendadas de revisão manual
        Seja conciso, direto ao ponto e não adicione introduções ou resumos.
        """
        return self.agent.run(prompt)

    def analisar_campo_incerto(self, campo_id: str, contexto: dict):
        """Análise inteligente de campos incertos"""
        prompt = f"""
        Analise este campo incerto de forma direta e curta (máximo 60 palavras):
        - Campo ID: {campo_id}
        - Contexto: {contexto}

        Responda apenas com:
        1. Valor proposto
        2. Confiança (%)
        3. Breve justificativa
        """
        return self.agent.run(prompt)


class AgenteAuditoria:
    """Agente especializado em auditoria de dados"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conhecimento = criar_conhecimento_lei_rouanet()

        # Ver nota em AgenteConciliacao sobre não usar tools=[...]: dados
        # reais entram via prompt, não via function-calling do modelo.
        self.agent = Agent(
            name="Agente Auditoria",
            role="Auditor especializado em Lei Rouanet",
            model=criar_modelo(),
            description="""
            Responsável por:
            - Validar integridade dos dados
            - Checar conformidade com Lei Rouanet
            - Identificar anomalias e inconsistências
            - Revisar documentações
            - Gerar relatórios de auditoria
            """,
            instructions=[
                "Aplicar regras de validação determinísticas",
                "As transações reais do projeto já vêm no prompt — nunca invente valores, CPFs ou fornecedores além delas",
                "Usar análise estatística para outliers",
                "Documentar todas as anomalias encontradas",
                "Recomendar ações corretivas",
                "Seja extremamente objetivo e conciso. Apresente as irregularidades encontradas e as recomendações de forma direta em listas simples. Limite a resposta a no máximo 150 palavras, sem introduções ou conclusões.",
                f"Conhecimento base: {self.conhecimento}"
            ],
        )

    def auditar_projeto(self, projeto_id: str):
        """Executa auditoria completa"""
        transacoes = buscar_transacoes(projeto_id)
        campos_revisao = buscar_campos_revisao(projeto_id)
        prompt = f"""
        Audite o projeto {projeto_id} com base SOMENTE nos dados abaixo.
        Apresente um relatório de auditoria resumido (máximo 150 palavras) focando estritamente em:

        TRANSAÇÕES DO PROJETO:
        {transacoes}

        CAMPOS PENDENTES DE REVISÃO MANUAL:
        {campos_revisao}

        Pontos obrigatórios da resposta curta:
        1. Inconsistências críticas encontradas (CPF/CNPJ, datas, valores)
        2. Irregularidades contra regras da Lei Rouanet
        3. Recomendações diretas de correção
        Não escreva preâmbulos ou considerações finais.
        """
        return self.agent.run(prompt)

    def revisar_documento(self, documento_id: str):
        """Análise de documentação anexada"""
        prompt = f"""
        Revise o documento {documento_id} de forma ultra-concisa (máximo 60 palavras):
        1. Status de Validade
        2. Status de Conformidade Lei Rouanet
        3. Recomendação principal
        """
        return self.agent.run(prompt)


class AgenteImportacao:
    """Agente especializado em importação e parsing"""

    def __init__(self, db_url: str):
        self.db_url = db_url

        self.agent = Agent(
            name="Agente Importação",
            role="Especialista em parsing e importação de dados",
            model=criar_modelo(),
            description="""
            Responsável por:
            - Analisar arquivos de entrada (JSON, Excel, CSV, PDF)
            - Normalizar e limpar dados
            - Validar formatos
            - Executar importação com tratamento de erros
            - Gerar relatórios de importação
            """,
            instructions=[
                "Detectar automaticamente o formato do arquivo",
                "Normalizar strings (maiúscula, espaços, acentuação)",
                "Validar campos obrigatórios",
                "Reportar erros de forma estruturada",
                "Seja extremamente conciso. Responda em formato de lista simples ou JSON indicando o status e principais avisos. Limite a resposta a no máximo 80 palavras.",
            ],
        )

    def importar_arquivo(self, caminho_arquivo: str, tipo_projeto: str = "rouanet"):
        """Importa e processa arquivo"""
        prompt = f"""
        Importe e processe o arquivo: {caminho_arquivo}
        Tipo de projeto: {tipo_projeto}

        Apresente um resumo curto (máximo 80 palavras) indicando:
        1. Formato detectado
        2. Status da validação e normalização
        3. Lista de problemas ou avisos principais
        """
        return self.agent.run(prompt)


class AgenteReconciliacao:
    """Agente para reconciliação automática"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conhecimento = criar_conhecimento_lei_rouanet()

        # Ver nota em AgenteConciliacao sobre não usar tools=[...]: dados
        # reais entram via prompt, não via function-calling do modelo.
        self.agent = Agent(
            name="Agente Reconciliação",
            role="Especialista em reconciliação automática",
            model=criar_modelo(),
            description="""
            Responsável por:
            - Matching determinístico (CPF, valores, datas)
            - Matching semântico (RAG - rubricas)
            - Sugerir reconciliações manuais
            - Aprender com feedback do usuário
            - Otimizar regras de matching
            """,
            instructions=[
                f"Conhecimento base: {self.conhecimento}",
                "As transações e movimentos reais do projeto já vêm no prompt — nunca invente dados além deles",
                "Priorizar matches determinísticos (100% confiança)",
                "Usar matching semântico como fallback",
                "Sempre validar com regras Lei Rouanet",
                "Seja extremamente objetivo. Liste apenas os matches propostos e a respectiva confiança de forma resumida, sem textos introdutórios ou conclusivos. Limite a resposta a no máximo 150 palavras.",
            ],
        )

    def reconciliar_automatico(self, projeto_id: str, confianca_minima: float = 0.85):
        """Executa reconciliação automática"""
        transacoes = buscar_transacoes(projeto_id)
        extrato = buscar_extrato_movimentos(projeto_id)
        rubricas = buscar_rubricas(projeto_id)
        prompt = f"""
        Reconcilie o projeto {projeto_id} com base nos dados fornecidos abaixo (confiança mínima: {confianca_minima}).
        Gere um relatório de matching curto (máximo 150 palavras):

        TRANSAÇÕES DO PROJETO:
        {transacoes}

        MOVIMENTOS DO EXTRATO BANCÁRIO:
        {extrato}

        RUBRICAS ORÇAMENTÁRIAS:
        {rubricas}

        Responda objetivamente com:
        1. Lista de matches confirmados (valores e confiança)
        2. Transações pendentes de revisão manual
        3. Estatísticas rápidas de reconciliação
        Sem preâmbulos.
        """
        return self.agent.run(prompt)


# ============================================================================
# 3. ORQUESTRADOR PRINCIPAL
# ============================================================================

class OrquestradorConcilia:
    """Orquestrador principal do sistema"""

    def __init__(self, db_url: str):
        self.db_url = db_url

        # Inicializa agentes
        self.agente_conciliacao = AgenteConciliacao(db_url)
        self.agente_auditoria = AgenteAuditoria(db_url)
        self.agente_importacao = AgenteImportacao(db_url)
        self.agente_reconciliacao = AgenteReconciliacao(db_url)

        # Agente orquestrador central
        self.orquestrador = Agent(
            name="Orquestrador Concilia",
            role="Coordenador de fluxos de negócio",
            model=criar_modelo(),
            description="""
            Coordena todos os agentes especializados para executar fluxos completos:
            - Importação → Validação → Reconciliação → Auditoria
            - Gestão de estado e dependências
            - Tratamento de erros e escalações
            """,
        )

    def fluxo_completo_projeto(self, projeto_id: str, arquivo: str = None):
        """Executa fluxo completo: importação → validação → reconciliação → auditoria"""
        print(f"\n🎯 Iniciando fluxo completo para projeto {projeto_id}")
        print(f"{'='*60}")

        resultado = {}

        # FASE 1: Importação
        if arquivo:
            print("\n📥 FASE 1: Importação")
            resultado["importacao"] = self.agente_importacao.importar_arquivo(arquivo)

        # FASE 2: Reconciliação Automática
        print("\n🔄 FASE 2: Reconciliação Automática")
        resultado["reconciliacao"] = self.agente_reconciliacao.reconciliar_automatico(projeto_id)

        # FASE 3: Auditoria
        print("\n🔍 FASE 3: Auditoria")
        resultado["auditoria"] = self.agente_auditoria.auditar_projeto(projeto_id)

        # FASE 4: Análise de Conciliação
        print("\n📊 FASE 4: Análise de Conciliação")
        resultado["conciliacao"] = self.agente_conciliacao.reconciliar_projeto(projeto_id)

        print(f"\n{'='*60}")
        print("✅ Fluxo completo finalizado\n")

        return resultado

    def revisar_campo_incerto(self, campo_id: str, contexto: dict):
        """Revisão colaborativa de campos incertos"""
        print(f"\n🔬 Revisando campo incerto {campo_id}")
        return self.agente_conciliacao.analisar_campo_incerto(campo_id, contexto)

    def executar_auditoria_rapida(self, projeto_id: str):
        """Auditoria rápida focada"""
        print(f"\n⚡ Auditoria rápida para projeto {projeto_id}")
        return self.agente_auditoria.auditar_projeto(projeto_id)


# ============================================================================
# 4. INICIALIZAÇÃO
# ============================================================================

def criar_orquestrador(db_url: str = None) -> OrquestradorConcilia:
    """Factory para criar o orquestrador"""
    if not db_url:
        db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError("DATABASE_URL deve ser definida via env var")

    print("🚀 Inicializando Orquestrador Concilia com Phidata")
    print(f"   Banco de dados: {db_url[:50]}...")

    return OrquestradorConcilia(db_url)


if __name__ == "__main__":
    # Teste básico
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        orq = criar_orquestrador(db_url)
        print("\n✅ Orquestrador inicializado com sucesso!")
    else:
        print("❌ DATABASE_URL não configurada")
