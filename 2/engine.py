"""
engine.py — Motor de leitura e validação de dados do Projeto Rouanet.

Esta é a mesma lógica confiável já testada no app Streamlit
(rouanet-concilia-app), extraída aqui sem dependências de UI, para ser
consumida via API REST por qualquer front-end (incluindo o painel HTML
legado).
"""

import io
import os
import re

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

TARGET_FILE_ID = "1q52xZirlzYCqpQJ7ldYNG9wQrVodPuJc"
TARGET_FILE_NAME = "2. Conciliação 1961.xlsx"
PASTA_PAGAMENTOS_ID = "1ydDeUQQzcTRk6QhJY_QIow1SfaJyL0Mj"
TOLERANCIA_VALOR = 0.01


class EngineError(Exception):
    """Erro previsível do motor (credenciais, download, parsing) —
    sempre traz uma mensagem segura para expor ao cliente da API."""


def autenticar_drive():
    """
    Autentica com o Google Drive via Service Account.

    Credenciais lidas de UMA das duas formas, nesta ordem:
    1. Variável de ambiente GOOGLE_CREDS_JSON (conteúdo completo do
       creds.json como string) — usado em produção (Render/Railway/etc).
    2. Arquivo local creds.json — usado em desenvolvimento local.
    """
    import json

    creds_json_env = os.getenv("GOOGLE_CREDS_JSON")
    if creds_json_env:
        try:
            info = json.loads(creds_json_env)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
            return build("drive", "v3", credentials=creds)
        except Exception as e:
            raise EngineError(f"Erro ao ler GOOGLE_CREDS_JSON: {e}")

    if os.path.exists("creds.json"):
        try:
            creds = service_account.Credentials.from_service_account_file(
                "creds.json", scopes=SCOPES
            )
            return build("drive", "v3", credentials=creds)
        except Exception as e:
            raise EngineError(f"Erro ao autenticar com creds.json local: {e}")

    raise EngineError(
        "Credenciais não encontradas. Configure GOOGLE_CREDS_JSON (produção) "
        "ou coloque um creds.json na pasta (desenvolvimento local)."
    )


def baixar_arquivo(service, file_id: str) -> io.BytesIO:
    try:
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        return buffer
    except Exception as e:
        raise EngineError(f"Erro ao baixar arquivo (ID: {file_id}): {e}")


def ler_planilha(service) -> pd.DataFrame:
    """Baixa e lê a planilha de conciliação, com detecção automática
    de cabeçalho e limpeza de colunas — mesma lógica do app Streamlit."""
    buffer = baixar_arquivo(service, TARGET_FILE_ID)

    try:
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
        df = df.dropna(axis=1, how="all")
        df = df.loc[:, ~df.columns.astype(str).str.match(r"^Unnamed")]

        for col in df.columns:
            if str(col).strip().upper() == "CONTROLE":
                df[col] = df[col].apply(
                    lambda v: "" if pd.isna(v)
                    else (str(int(v)) if isinstance(v, float) and v.is_integer() else str(v))
                )
        return df
    except Exception as e:
        raise EngineError(f"Erro ao processar a planilha: {e}")


def listar_pdfs_pagamentos(service) -> list:
    try:
        query = (
            f"'{PASTA_PAGAMENTOS_ID}' in parents "
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
        raise EngineError(f"Erro ao listar PDFs: {e}")


def extrair_valor_do_pdf(buffer: io.BytesIO):
    import pdfplumber

    try:
        with pdfplumber.open(buffer) as pdf:
            texto_completo = ""
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina + "\n"

        padrao = r"R?\$?\s?([\d]{1,3}(?:\.\d{3})*,\d{2})"
        matches = re.findall(padrao, texto_completo)
        if not matches:
            return None

        valores = []
        for m in matches:
            try:
                valores.append(float(m.replace(".", "").replace(",", ".")))
            except ValueError:
                continue

        return max(valores) if valores else None
    except Exception:
        return None


def validar_pdfs_em_lote(service, df: pd.DataFrame, pdfs: list) -> pd.DataFrame:
    """Casa cada PDF com uma linha da planilha pelo número de CONTROLE
    no nome do arquivo, extrai o valor do comprovante e compara."""
    df = df.copy()
    df["Status"] = "Sem comprovante"
    df["Valor_PDF"] = None

    coluna_controle = None
    coluna_valor = None
    for col in df.columns:
        nome = str(col).strip().upper()
        if nome == "CONTROLE":
            coluna_controle = col
        elif nome == "VALOR":
            coluna_valor = col

    if coluna_controle is None or coluna_valor is None:
        raise EngineError("Colunas CONTROLE e/ou VALOR não encontradas na planilha.")

    controle_numerico = pd.to_numeric(df[coluna_controle], errors="coerce")
    valor_numerico = pd.to_numeric(df[coluna_valor], errors="coerce")

    for pdf_arq in pdfs:
        match_id = re.search(r"(\d+)", pdf_arq["name"])
        if not match_id:
            continue
        controle_id = int(match_id.group(1))

        mascara_linha = controle_numerico == controle_id
        if not mascara_linha.any():
            continue

        buffer_pdf = baixar_arquivo(service, pdf_arq["id"])
        valor_pdf = extrair_valor_do_pdf(buffer_pdf)

        if valor_pdf is None:
            df.loc[mascara_linha, "Status"] = f"PDF sem valor legível ({pdf_arq['name']})"
            continue

        df.loc[mascara_linha, "Valor_PDF"] = valor_pdf
        valor_planilha = valor_numerico[mascara_linha].values[0]

        if pd.isna(valor_planilha):
            df.loc[mascara_linha, "Status"] = "Planilha sem valor nessa linha"
        elif abs(valor_planilha - valor_pdf) < TOLERANCIA_VALOR:
            df.loc[mascara_linha, "Status"] = "OK"
        else:
            df.loc[mascara_linha, "Status"] = "Diverge"

    return df
