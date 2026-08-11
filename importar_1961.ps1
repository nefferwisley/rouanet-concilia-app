<#
.SYNOPSIS
  Script de automação para importação do Projeto 1961 (Circunstância Cinematográfica).

.DESCRIPTION
  Executa em lote os 3 passos de carga no backend RouanetConcilia:
    1. Cria o projeto (PRONAC 20-7453 / Banco do Brasil)
    2. Importa os 265 lançamentos de despesas (modo commit) e aguarda a conclusão
    3. Importa o extrato bancário parseado (movimentos.json + cruzamento.json)

.PARAMETER ApiUrl
  URL base da API backend (padrão: http://localhost:8000)

.PARAMETER Token
  Bearer token JWT para autenticação (se o backend exigir)

.EXAMPLE
  .\importar_1961.ps1
  .\importar_1961.ps1 -ApiUrl "https://meu-backend.onrender.com" -Token "eyJhbG..."
#>

[CmdletBinding()]
param(
    [string]$ApiUrl = "http://localhost:8000",
    [string]$Token = ""
)

$ErrorActionPreference = "Stop"

# Ajusta barra no final da URL
$ApiUrl = $ApiUrl.TrimEnd("/")

# Headers
$Headers = @{}
if ($Token) {
    $Headers["Authorization"] = "Bearer $Token"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  RouanetConcilia — Automação de Carga do Projeto 1961" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "API Target: $ApiUrl`n"

# ------------------------------------------------------------
# Passo 1: Criar Projeto
# ------------------------------------------------------------
Write-Host "[1/3] Criando o Projeto 1961 (PRONAC 20-7453)..." -ForegroundColor Yellow

$BodyProjeto = @{
    pronac     = "20-7453"
    nome       = "Circunstância Cinematográfica"
    proponente = "Mônica Guimarães"
    controller = "Mog Produtora"
    banco_nome = "Banco do Brasil"
    agencia    = "3210-9"
    conta      = "14.209-1"
} | ConvertTo-Json

try {
    $RespProjeto = Invoke-RestMethod -Uri "$ApiUrl/api/v1/projetos" `
        -Method Post `
        -ContentType "application/json" `
        -Headers $Headers `
        -Body $BodyProjeto
    
    $ProjetoId = $RespProjeto.id
    Write-Host "  ✅ Projeto criado com sucesso!" -ForegroundColor Green
    Write-Host "  ID: $ProjetoId" -ForegroundColor Gray
    Write-Host "  Nome: $($RespProjeto.nome)" -ForegroundColor Gray
    Write-Host "  PRONAC: $($RespProjeto.pronac)`n" -ForegroundColor Gray
}
catch {
    Write-Host "  ❌ Erro ao criar projeto: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $Reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Host "  Detalhes: $($Reader.ReadToEnd())" -ForegroundColor Red
    }
    exit 1
}

# ------------------------------------------------------------
# Passo 2: Importar Lançamentos (JSON + YAML) via curl.exe
# ------------------------------------------------------------
Write-Host "[2/3] Importando os lançamentos de despesas (modo commit)..." -ForegroundColor Yellow

$JsonPath = Join-Path $PSScriptRoot "motor\tests\fixtures\projeto_1961\lancamentos_1961.json"
$YamlPath = Join-Path $PSScriptRoot "motor\tests\fixtures\projeto_1961\config_1961.yaml"

if (-not (Test-Path $JsonPath) -or -not (Test-Path $YamlPath)) {
    Write-Host "  ❌ Arquivos de fixture não encontrados em motor/tests/fixtures/projeto_1961/" -ForegroundColor Red
    exit 1
}

$AuthHeader = if ($Token) { "-H", "Authorization: Bearer $Token" } else { @() }

$CurlArgs = @(
    "-s", "-X", "POST", "$ApiUrl/api/v1/importacoes"
) + $AuthHeader + @(
    "-F", "projeto_id=$ProjetoId",
    "-F", "modo=commit",
    "-F", "arquivo=@$JsonPath",
    "-F", "config_yaml=@$YamlPath"
)

$RespImportRaw = & curl.exe @CurlArgs
try {
    $RespImport = $RespImportRaw | ConvertFrom-Json
    $ImportacaoId = $RespImport.importacao_id
    Write-Host "  ✅ Importação agendada!" -ForegroundColor Green
    Write-Host "  Importação ID: $ImportacaoId" -ForegroundColor Gray
}
catch {
    Write-Host "  ❌ Falha ao agendar importação: $RespImportRaw" -ForegroundColor Red
    exit 1
}

# Aguarda conclusão
Write-Host "  Aguardando processamento das linhas..." -NoNewline
$Status = "iniciando"
$Tentativas = 0

while ($Status -in @("iniciando", "em_progresso") -and $Tentativas -lt 60) {
    Start-Sleep -Seconds 2
    $Tentativas++
    Write-Host "." -NoNewline
    
    try {
        $StatusObj = Invoke-RestMethod -Uri "$ApiUrl/api/v1/importacoes/$ImportacaoId" `
            -Method Get `
            -Headers $Headers
        $Status = $StatusObj.status
    }
    catch {
        # ignora erro transitório
    }
}
Write-Host ""

if ($Status -eq "sucesso") {
    Write-Host "  ✅ Lançamentos importados com sucesso!" -ForegroundColor Green
    Write-Host "  Total de linhas: $($StatusObj.linhas_total) (OK: $($StatusObj.linhas_ok), Alertas: $($StatusObj.linhas_alerta), Erros: $($StatusObj.linhas_erro))`n" -ForegroundColor Gray
}
else {
    Write-Host "  ⚠️ Importação finalizou com status '$Status': $($StatusObj.mensagem)" -ForegroundColor Yellow
}

# ------------------------------------------------------------
# Passo 3: Importar Extrato Bancário
# ------------------------------------------------------------
Write-Host "[3/3] Importando extrato bancário (movimentos.json + cruzamento.json)..." -ForegroundColor Yellow

try {
    $RespExtrato = Invoke-RestMethod -Uri "$ApiUrl/api/v1/projetos/$ProjetoId/extrato/importar" `
        -Method Post `
        -Headers $Headers
    
    Write-Host "  ✅ Extrato importado com sucesso!" -ForegroundColor Green
    Write-Host "  Movimentos importados: $($RespExtrato.importados)" -ForegroundColor Gray
    Write-Host "  Conta ID: $($RespExtrato.conta_id)`n" -ForegroundColor Gray
}
catch {
    Write-Host "  ❌ Falha ao importar extrato: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $Reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Host "  Detalhes: $($Reader.ReadToEnd())" -ForegroundColor Red
    }
}

# ------------------------------------------------------------
# Resumo Final
# ------------------------------------------------------------
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  CARGA CONCLUÍDA!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Projeto ID: $ProjetoId" -ForegroundColor White
Write-Host "Abra no painel frontend:" -ForegroundColor White
Write-Host "  http://localhost:5173/projeto/$ProjetoId" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
