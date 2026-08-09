import io
import os
import re
import sys
from datetime import datetime

import pandas as pd
import pdfplumber
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from fpdf import FPDF
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

try:
    import google.generativeai as genai
except ImportError:
    genai = None

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
try:
    if not GEMINI_API_KEY and "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass  # st.secrets pode não existir localmente, sem problema

# ============================================================
# CONFIGURAÇÃO
# ============================================================
CREDS_PATH = "creds.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# ID direto do arquivo "2. Conciliação 1961.xlsx" dentro da pasta
# 1dQA1GZSyWBewnoqaR-qJ5UiIbaR_2wxp -> 3. 1961 -> 2. Conciliação 1961.xlsx
TARGET_FILE_ID = "1q52xZirlzYCqpQJ7ldYNG9wQrVodPuJc"
TARGET_FILE_NAME = "2. Conciliação 1961.xlsx"

# Pasta "1. Pagamentos" com os comprovantes/recibos em PDF
PASTA_PAGAMENTOS_ID = "1ydDeUQQzcTRk6QhJY_QIow1SfaJyL0Mj"

# Tolerância (em R$) para considerar que o valor do PDF "bate" com a planilha
TOLERANCIA_VALOR = 0.01

# Senha de acesso ao painel. ATENÇÃO: isso fica visível em texto puro
# no código-fonte se você não usar Secrets — não é segurança real, só uma
# barreira simples contra acesso casual. Não use para proteger dados
# sensíveis de terceiros sem uma senha configurada via Secrets.
try:
    SENHA_ACESSO = st.secrets.get("SENHA_ACESSO", "1961")
except Exception:
    SENHA_ACESSO = "1961"

st.set_page_config(page_title="Conciliação Offline - Projeto 1961", layout="wide")
st.title("📁 Conciliação Offline - Projeto 1961")


# ============================================================
# LOGIN SIMPLES (barreira básica, não é segurança real)
# ============================================================
def verificar_login():
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.title("🔐 Acesso Restrito")
        senha_input = st.text_input("Digite a senha do projeto:", type="password")
        if st.button("Entrar"):
            if senha_input == SENHA_ACESSO:
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
        st.stop()

    st.sidebar.success("🔓 Logado como: Administrador")
    st.sidebar.markdown("---")
    if st.sidebar.button("Sair (Logout)"):
        st.session_state.logado = False
        st.rerun()


# ============================================================
# AUTENTICAÇÃO
# ============================================================
def autenticar_drive():
    try:
        # NA NUVEM (Streamlit Community Cloud): lê as credenciais do
        # cofre seguro "Secrets", configurado no painel do Streamlit Cloud.
        if "gcp_service_account" in st.secrets:
            info_credenciais = dict(st.secrets["gcp_service_account"])
            creds = service_account.Credentials.from_service_account_info(
                info_credenciais, scopes=SCOPES
            )
            service = build("drive", "v3", credentials=creds)
            return service
    except Exception:
        pass  # st.secrets pode não existir localmente — segue pro fallback abaixo

    # LOCAL: lê o arquivo creds.json do disco, como sempre funcionou
    if not os.path.exists(CREDS_PATH):
        st.error(
            f"❌ Credenciais não encontradas.\n\n"
            f"- Rodando localmente: crie o arquivo `{CREDS_PATH}` na pasta do projeto.\n"
            "- Rodando no Streamlit Cloud: configure o segredo "
            "`gcp_service_account` no painel do app (Settings → Secrets).\n\n"
            "Veja o README.md para instruções detalhadas."
        )
        st.stop()

    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDS_PATH, scopes=SCOPES
        )
        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        st.error(f"❌ Erro de autenticação com o Google Drive: {e}")
        st.stop()


# ============================================================
# DOWNLOAD DO ARQUIVO
# ============================================================
def baixar_arquivo(service, file_id: str) -> io.BytesIO:
    try:
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        progress = st.progress(0, text="Baixando arquivo do Drive...")
        while not done:
            status, done = downloader.next_chunk()
            if status:
                progress.progress(
                    int(status.progress() * 100),
                    text=f"Baixando arquivo do Drive... {int(status.progress() * 100)}%",
                )
        progress.empty()

        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(
            f"❌ Erro ao baixar o arquivo (ID: {file_id}): {e}\n\n"
            "Verifique se a pasta/arquivo foi compartilhado com o e-mail "
            "da Service Account (veja o README.md)."
        )
        st.stop()


# ============================================================
# LEITURA DO ARQUIVO (CSV ou Excel)
# ============================================================
def ler_dados(buffer: io.BytesIO, nome_arquivo: str) -> pd.DataFrame:
    try:
        if nome_arquivo.lower().endswith((".xlsx", ".xls")):
            # Lê primeiro sem cabeçalho fixo, pra descobrir em qual linha
            # está o cabeçalho real (procura a linha que contém "CONTROLE")
            buffer.seek(0)
            df_bruto = pd.read_excel(buffer, engine="openpyxl", header=None)

            linha_cabecalho = 0
            for i in range(min(5, len(df_bruto))):
                valores_linha = df_bruto.iloc[i].astype(str).str.strip().str.upper()
                if (valores_linha == "CONTROLE").any():
                    linha_cabecalho = i
                    break

            buffer.seek(0)
            df = pd.read_excel(buffer, engine="openpyxl", header=linha_cabecalho)
            # Remove colunas totalmente vazias (sem nome e sem dados)
            df = df.dropna(axis=1, how="all")
            # Remove colunas com nome duplicado tipo "RUBRICA.1"
            df = df.loc[:, ~df.columns.astype(str).str.match(r"^Unnamed")]

            # A coluna CONTROLE mistura números (1, 2, 3...) e texto
            # (ex: "Total Rendimento" em linhas de resumo). Isso quebra a
            # exibição da tabela no Streamlit, que exige tipo único por
            # coluna. Convertemos para texto de forma segura.
            for col in df.columns:
                if str(col).strip().upper() == "CONTROLE":
                    df[col] = df[col].apply(
                        lambda v: "" if pd.isna(v)
                        else (str(int(v)) if isinstance(v, float) and v.is_integer() else str(v))
                    )
        else:
            try:
                df = pd.read_csv(buffer)
            except Exception:
                buffer.seek(0)
                df = pd.read_excel(buffer, engine="openpyxl")
        return df
    except Exception as e:
        st.error(f"❌ Erro ao processar os dados do arquivo: {e}")
        st.stop()


# ============================================================
# OCR/PDF - LISTAR COMPROVANTES NA PASTA "1. Pagamentos"
# ============================================================
def listar_pdfs_pagamentos(service, folder_id: str):
    try:
        query = (
            f"'{folder_id}' in parents "
            "and mimeType = 'application/pdf' "
            "and trashed = false"
        )
        resultado = (
            service.files()
            .list(q=query, fields="files(id, name)", pageSize=200)
            .execute()
        )
        return resultado.get("files", [])
    except Exception as e:
        st.error(f"❌ Erro ao listar PDFs na pasta de pagamentos: {e}")
        return []


# ============================================================
# OCR/PDF - EXTRAIR VALOR DO COMPROVANTE
# ============================================================
def extrair_valor_do_pdf(buffer: io.BytesIO):
    try:
        with pdfplumber.open(buffer) as pdf:
            texto_completo = ""
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina + "\n"

        # Procura padrões tipo "R$ 1.234,56" ou "1.234,56"
        padrao = r"R?\$?\s?([\d]{1,3}(?:\.\d{3})*,\d{2})"
        matches = re.findall(padrao, texto_completo)

        if not matches:
            return None, texto_completo

        # Pega o maior valor encontrado (geralmente é o valor total do comprovante)
        valores = []
        for m in matches:
            try:
                valor = float(m.replace(".", "").replace(",", "."))
                valores.append(valor)
            except ValueError:
                continue

        if not valores:
            return None, texto_completo

        return max(valores), texto_completo
    except Exception as e:
        st.error(f"❌ Erro ao processar o PDF: {e}")
        return None, ""


# ============================================================
# OCR/PDF - COMPARAR VALOR EXTRAÍDO COM A PLANILHA
# ============================================================
def encontrar_linhas_correspondentes(df: pd.DataFrame, valor: float):
    coluna_valor = None
    for col in df.columns:
        if str(col).strip().upper() == "VALOR":
            coluna_valor = col
            break

    if coluna_valor is None:
        return pd.DataFrame(), None

    valores_numericos = pd.to_numeric(df[coluna_valor], errors="coerce")
    mascara = (valores_numericos - valor).abs() < TOLERANCIA_VALOR
    return df[mascara], coluna_valor


# ============================================================
# OCR/PDF - VALIDAÇÃO EM LOTE (todos os PDFs de uma vez)
# ============================================================
def validar_pdfs_em_lote(service, df: pd.DataFrame, pdfs: list) -> pd.DataFrame:
    df = df.copy()
    df["Status"] = "⏳ Sem comprovante"
    df["Valor_PDF"] = None

    # Descobre as colunas reais CONTROLE e VALOR (tolerante a maiúsc/minúsc/espaços)
    coluna_controle = None
    coluna_valor = None
    for col in df.columns:
        nome = str(col).strip().upper()
        if nome == "CONTROLE":
            coluna_controle = col
        elif nome == "VALOR":
            coluna_valor = col

    if coluna_controle is None or coluna_valor is None:
        st.warning(
            "⚠️ Não encontrei as colunas 'CONTROLE' e/ou 'VALOR' na planilha "
            "para fazer o cruzamento automático."
        )
        return df

    controle_numerico = pd.to_numeric(df[coluna_controle], errors="coerce")
    valor_numerico = pd.to_numeric(df[coluna_valor], errors="coerce")

    progresso = st.progress(0, text="Processando comprovantes...")

    for i, pdf_arq in enumerate(pdfs):
        progresso.progress(
            (i + 1) / len(pdfs),
            text=f"Lendo {pdf_arq['name']} ({i + 1}/{len(pdfs)})...",
        )

        # Extrai o número do CONTROLE a partir do nome do arquivo (ex: "NF_12.pdf" -> 12)
        match_id = re.search(r"(\d+)", pdf_arq["name"])
        if not match_id:
            continue
        controle_id = int(match_id.group(1))

        mascara_linha = controle_numerico == controle_id
        if not mascara_linha.any():
            continue

        buffer_pdf = baixar_arquivo(service, pdf_arq["id"])
        valor_pdf, _ = extrair_valor_do_pdf(buffer_pdf)

        if valor_pdf is None:
            df.loc[mascara_linha, "Status"] = (
                f"⚠️ PDF sem valor legível ({pdf_arq['name']})"
            )
            continue

        df.loc[mascara_linha, "Valor_PDF"] = valor_pdf
        valor_planilha = valor_numerico[mascara_linha].values[0]

        if pd.isna(valor_planilha):
            df.loc[mascara_linha, "Status"] = "⚠️ Planilha sem valor nessa linha"
        elif abs(valor_planilha - valor_pdf) < TOLERANCIA_VALOR:
            df.loc[mascara_linha, "Status"] = f"✅ OK (R$ {valor_pdf:,.2f})"
        else:
            df.loc[mascara_linha, "Status"] = (
                f"❌ Diverge — Planilha: R$ {valor_planilha:,.2f} / "
                f"PDF: R$ {valor_pdf:,.2f}"
            )

    progresso.empty()
    return df


def colorir_linhas_status(row):
    status = str(row.get("Status", ""))
    if "✅" in status:
        return ["background-color: #d4edda"] * len(row)
    elif "❌" in status:
        return ["background-color: #f8d7da"] * len(row)
    elif "⚠️" in status:
        return ["background-color: #fff3cd"] * len(row)
    return [""] * len(row)


# ============================================================
# SEÇÃO DE VALIDAÇÃO POR PDF (OCR) - EM LOTE
# ============================================================
def secao_validacao_pdf(service, df: pd.DataFrame):
    st.divider()
    st.subheader("🧾 Validação Automática de Comprovantes (OCR em lote)")
    st.caption(
        "Os PDFs devem estar na pasta '1. Pagamentos' e ter um número no nome "
        "(ex: NF_12.pdf) correspondente ao CONTROLE da planilha."
    )

    with st.spinner("Buscando comprovantes na pasta '1. Pagamentos'..."):
        pdfs = listar_pdfs_pagamentos(service, PASTA_PAGAMENTOS_ID)

    if not pdfs:
        st.info(
            "Nenhum PDF encontrado na pasta '1. Pagamentos'. "
            "Verifique se a pasta foi compartilhada com a Service Account "
            "e se há arquivos .pdf nela."
        )
        return

    st.write(f"📎 {len(pdfs)} PDF(s) encontrado(s) na pasta.")

    if st.button("🚀 Validar todos os comprovantes"):
        df_resultado = validar_pdfs_em_lote(service, df, pdfs)
        df_resultado["Minha_Decisao"] = "Não analisado"
        df_resultado["Justificativa"] = ""
        # Guarda em session_state para sobreviver aos reruns do Streamlit
        # (o data_editor e o botão de download abaixo disparam reruns)
        st.session_state["df_conciliacao"] = df_resultado

    if "df_conciliacao" in st.session_state:
        secao_decisao_e_exportacao(st.session_state["df_conciliacao"])


# ============================================================
# GERAÇÃO DO RELATÓRIO FINAL EM PDF
# ============================================================
def gerar_relatorio_pdf(df: pd.DataFrame, data_geracao: str) -> bytes:
    coluna_controle = next(
        (c for c in df.columns if str(c).strip().upper() == "CONTROLE"), None
    )
    coluna_valor = next(
        (c for c in df.columns if str(c).strip().upper() == "VALOR"), None
    )

    pdf = FPDF()
    pdf.add_page()

    # Cabeçalho
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Relatorio de Conciliacao - Projeto 1961", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 10, f"Gerado em: {data_geracao}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # Estatísticas
    aprovados = (df.get("Minha_Decisao") == "Aprovado").sum()
    rejeitados = (df.get("Minha_Decisao") == "Rejeitado").sum()
    pendentes = (df.get("Minha_Decisao") == "Não analisado").sum()

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Resumo Final:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 7, f"Aprovados: {aprovados}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Rejeitados: {rejeitados}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Pendentes: {pendentes}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Tabela
    pdf.set_font("Helvetica", "B", 9)
    cols = ["CONTROLE", "Valor Planilha", "Valor PDF", "Status", "Decisão", "Justificativa"]
    col_widths = [18, 30, 30, 45, 25, 42]

    for i, col in enumerate(cols):
        pdf.cell(col_widths[i], 8, col, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", size=8)
    for _, row in df.iterrows():
        controle = row[coluna_controle] if coluna_controle else ""
        if pd.isna(controle) or str(controle).strip() == "":
            continue  # pula linhas sem número de controle (linhas de rendimento/saldo)

        valor_planilha = row[coluna_valor] if coluna_valor else None
        texto_valor_planilha = (
            f"R$ {valor_planilha:,.2f}" if pd.notna(valor_planilha) else "N/A"
        )

        valor_pdf = row.get("Valor_PDF")
        texto_valor_pdf = f"R$ {valor_pdf:,.2f}" if pd.notna(valor_pdf) else "N/A"

        status_text = str(row.get("Status", ""))
        # Remove emojis (o FPDF padrão não suporta Unicode/emoji com Helvetica)
        status_limpo = re.sub(r"[^\x00-\x7F]+", "", status_text).strip()
        if len(status_limpo) > 25:
            status_limpo = status_limpo[:25] + "..."

        decisao = str(row.get("Minha_Decisao", ""))

        justificativa = str(row.get("Justificativa", ""))
        if len(justificativa) > 25:
            justificativa = justificativa[:25] + "..."

        pdf.cell(col_widths[0], 7, str(controle), border=1, align="C")
        pdf.cell(col_widths[1], 7, texto_valor_planilha, border=1, align="R")
        pdf.cell(col_widths[2], 7, texto_valor_pdf, border=1, align="R")
        pdf.cell(col_widths[3], 7, status_limpo, border=1, align="C")
        pdf.cell(col_widths[4], 7, decisao, border=1, align="C")
        pdf.cell(col_widths[5], 7, justificativa, border=1, align="L")
        pdf.ln()

    # Rodapé
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(
        0, 5,
        "Documento gerado automaticamente pelo Sistema RouanetConcilia.",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )

    return bytes(pdf.output())


# ============================================================
# JUSTIFICATIVA AUTOMÁTICA VIA IA (Gemini) - SOB DEMANDA
# ============================================================
def gemini_disponivel() -> bool:
    return genai is not None and bool(GEMINI_API_KEY)


def gerar_justificativa_ia(
    controle, fornecedor, valor_planilha, valor_pdf, status
) -> str:
    if not gemini_disponivel():
        return (
            "⚠️ IA não configurada. Crie um arquivo `.env` na pasta do projeto "
            "com a linha GEMINI_API_KEY=sua_chave_aqui (e confirme que `.env` "
            "está no .gitignore)."
        )

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        texto_valor_pdf = (
            f"R$ {valor_pdf:,.2f}" if pd.notna(valor_pdf) else "não encontrado/sem comprovante"
        )
        texto_valor_planilha = (
            f"R$ {valor_planilha:,.2f}" if pd.notna(valor_planilha) else "não informado"
        )

        prompt = (
            "Você é um assistente de prestação de contas da Lei Rouanet. "
            f"Item CONTROLE {controle}, fornecedor: {fornecedor}. "
            f"Valor na planilha de conciliação: {texto_valor_planilha}. "
            f"Valor extraído do comprovante: {texto_valor_pdf}. "
            f"Status da validação automática: {status}. "
            "Escreva uma justificativa curta (2-3 frases), profissional e objetiva, "
            "adequada para constar num relatório de prestação de contas cultural."
        )

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Erro ao consultar a IA: {e}"


# ============================================================
# SEÇÃO DE DECISÃO (APROVAR/REJEITAR) E EXPORTAÇÃO
# ============================================================
def secao_decisao_e_exportacao(df_resultado: pd.DataFrame):
    st.divider()
    st.subheader("📊 Painel de Controle")

    total_itens = len(df_resultado)
    aprovados = (df_resultado["Minha_Decisao"] == "Aprovado").sum()
    rejeitados = (df_resultado["Minha_Decisao"] == "Rejeitado").sum()
    pendentes = (df_resultado["Minha_Decisao"] == "Não analisado").sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📄 Total de Itens", total_itens)
    col2.metric("✅ Aprovados", aprovados)
    col3.metric("❌ Rejeitados", rejeitados)
    col4.metric("⏳ Pendentes", pendentes)

    if total_itens > 0:
        fig = px.pie(
            names=["Aprovados", "Rejeitados", "Pendentes"],
            values=[aprovados, rejeitados, pendentes],
            color_discrete_map={
                "Aprovados": "#00CC96",
                "Rejeitados": "#EF553B",
                "Pendentes": "#FFC107",
            },
            title="Distribuição das Decisões",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("🤖 Justificativa Automática por IA (opcional)")

    if not gemini_disponivel():
        st.caption(
            "⚠️ IA não configurada. Para ativar, crie um `.env` na pasta do "
            "projeto com `GEMINI_API_KEY=sua_chave_aqui` e instale `google-generativeai` "
            "e `python-dotenv`."
        )
    else:
        coluna_controle = next(
            (c for c in df_resultado.columns if str(c).strip().upper() == "CONTROLE"),
            None,
        )
        coluna_fornecedor = next(
            (c for c in df_resultado.columns if "FORNECEDOR" in str(c).strip().upper()),
            None,
        )
        coluna_valor = next(
            (c for c in df_resultado.columns if str(c).strip().upper() == "VALOR"),
            None,
        )

        if coluna_controle is None:
            st.info("Não encontrei a coluna CONTROLE para selecionar a linha.")
        else:
            opcoes_controle = sorted(
                {
                    v for v in df_resultado[coluna_controle].astype(str).str.strip()
                    if v != "" and v.replace(".", "", 1).isdigit()
                },
                key=int,
            )
            controle_escolhido = st.selectbox(
                "Selecione o CONTROLE para gerar justificativa:", opcoes_controle
            )

            if st.button("✨ Gerar justificativa com IA para essa linha"):
                mascara = df_resultado[coluna_controle].astype(str) == controle_escolhido
                linha = df_resultado[mascara].iloc[0]

                with st.spinner("Consultando a IA..."):
                    justificativa_gerada = gerar_justificativa_ia(
                        controle=controle_escolhido,
                        fornecedor=linha[coluna_fornecedor] if coluna_fornecedor else "N/A",
                        valor_planilha=linha[coluna_valor] if coluna_valor else None,
                        valor_pdf=linha.get("Valor_PDF"),
                        status=linha.get("Status", ""),
                    )

                df_resultado.loc[mascara, "Justificativa"] = justificativa_gerada
                st.session_state["df_conciliacao"] = df_resultado
                st.success("Justificativa gerada e preenchida na tabela abaixo.")
                st.rerun()

    st.divider()
    st.subheader("📋 Tabela Interativa (Aprove ou Rejeite)")

    colunas_bloqueadas = [
        col for col in df_resultado.columns
        if col not in ("Minha_Decisao", "Justificativa")
    ]

    df_editado = st.data_editor(
        df_resultado,
        column_config={
            "Minha_Decisao": st.column_config.SelectboxColumn(
                "Minha Decisão Final",
                help="O que você decide sobre esse lançamento?",
                width="medium",
                options=["Não analisado", "Aprovado", "Rejeitado"],
                required=True,
            ),
            "Justificativa": st.column_config.TextColumn(
                "Justificativa (Opcional)", width="large"
            ),
        },
        disabled=colunas_bloqueadas,
        hide_index=True,
        use_container_width=True,
    )

    # Guarda a versão editada de volta no session_state
    st.session_state["df_conciliacao"] = df_editado

    st.divider()
    st.subheader("📤 Gerar Relatório Final")

    nome_arquivo_export = (
        f"Relatorio_Conciliacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    csv_final = df_editado.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="📥 Baixar Relatório de Conciliação (.csv)",
        data=csv_final,
        file_name=nome_arquivo_export,
        mime="text/csv",
    )

    st.divider()
    st.subheader("📄 Relatório Final em PDF")

    if st.button("📥 Gerar e Baixar Relatório (.pdf)"):
        with st.spinner("Gerando PDF..."):
            data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")
            pdf_bytes = gerar_relatorio_pdf(df_editado, data_atual)

        st.download_button(
            label="Clique aqui para baixar o PDF",
            data=pdf_bytes,
            file_name=f"Relatorio_Conciliacao_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
        )
        st.success("✅ PDF gerado com sucesso!")


# ============================================================
# FLUXO PRINCIPAL
# ============================================================
def main():
    verificar_login()

    with st.spinner("Autenticando com o Google Drive..."):
        service = autenticar_drive()

    st.success(f"✅ Autenticado. Buscando arquivo: **{TARGET_FILE_NAME}**")

    buffer = baixar_arquivo(service, TARGET_FILE_ID)
    df = ler_dados(buffer, TARGET_FILE_NAME)

    st.metric("Total de linhas", len(df))
    st.dataframe(df, use_container_width=True)

    secao_validacao_pdf(service, df)


if __name__ == "__main__":
    main()