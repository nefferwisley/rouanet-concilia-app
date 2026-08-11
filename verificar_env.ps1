# verificar_env.ps1 — checagem pré-trabalho (disco, Docker, health, schema).
# Rode SEMPRE antes de começar a trabalhar no projeto:
#   powershell -ExecutionPolicy Bypass -File verificar_env.ps1
# Sai com código 1 e lista os problemas se algo estiver ruim.

$ErrorActionPreference = "SilentlyContinue"
$problemas = 0

function Falha([string]$msg) {
    Write-Host ("  [FALHA] " + $msg) -ForegroundColor Red
    $script:problemas++
}
function Ok([string]$msg) {
    Write-Host ("  [ok]    " + $msg) -ForegroundColor Green
}
function Aviso([string]$msg) {
    Write-Host ("  [!]     " + $msg) -ForegroundColor Yellow
}

Write-Host "=== RouanetConcilia - verificacao de ambiente ===" -ForegroundColor Cyan

# 1) Disco livre (causa raiz de 'read-only file system' no Docker)
Write-Host "`n[1/5] Disco C:" -ForegroundColor Cyan
$disco = Get-Volume -DriveLetter C
$livre = [math]::Round($disco.SizeRemaining / 1GB, 1)
$total = [math]::Round($disco.Size / 1GB, 1)
$pctLivre = [math]::Round(($disco.SizeRemaining / $disco.Size) * 100, 1)
Write-Host "  Livre: $livre GB de $total GB ($pctLivre%)" -ForegroundColor White
if ($pctLivre -lt 20) {
    Falha "menos de 20% livres. Limpe caches (Adobe Media Cache, Red Giant, .ollama) antes de continuar."
} else {
    Ok "espaco suficiente."
}

# 2) Docker Desktop + engine
Write-Host "`n[2/5] Docker" -ForegroundColor Cyan
if (Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue) {
    $engine = docker version --format "{{.Server.Version}}" 2>$null
    if ($engine) { Ok "engine no ar (server $engine)." }
    else {
        Falha "Docker Desktop aberto mas engine fora. Reinicie: Stop-Process 'Docker Desktop'; wsl --shutdown; inicie de novo."
    }
} else {
    Falha "Docker Desktop nao esta aberto. Inicie: C:\Users\Dell\AppData\Local\Programs\DockerDesktop\frontend\Docker Desktop.exe"
}

# 3) Containers da stack
Write-Host "`n[3/5] Containers" -ForegroundColor Cyan
$stack = docker ps -a --filter "name=rouanet_" --format "{{.Names}} {{.Status}}" 2>$null
if ($stack) { $stack | ForEach-Object { Write-Host "  $_" -ForegroundColor White } }
else { Aviso "nenhum container rouanet_ encontrado (so sobe se precisar)." }

# 4) Health do backend (local + producao)
Write-Host "`n[4/5] Health" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing
    Ok "local  : HTTP $($r.StatusCode)"
} catch { Aviso "local  : backend fora (sobe com docker compose up -d)." }
try {
    $r2 = Invoke-WebRequest -Uri "https://rouanetconcilia-backend-y19v.onrender.com/health" -TimeoutSec 15 -UseBasicParsing
    Ok "producao: HTTP $($r2.StatusCode)"
} catch { Falha "producao: Render fora ou dormindo (free tier)." }

# 5) Schema migrations (local, via docker)
Write-Host "`n[5/5] Schema" -ForegroundColor Cyan
$mig = docker exec rouanet_db psql -U rouanet -d rouanet_concilia -t -c "select count(*) from schema_migrations" 2>$null
if ($mig) {
    Ok "schema_migrations local: $($mig.Trim()) migration(s) registrada(s)."
} else {
    Aviso "schema_migrations nao respondeu (container fora ou tabela nao criada ainda). O runner aplica no startup do backend."
}

Write-Host ""
if ($problemas -gt 0) {
    Write-Host ("RESULTADO: $problemas problema(s). Corrija antes de trabalhar.") -ForegroundColor Red
    exit 1
}
Write-Host "RESULTADO: ambiente OK. Pode trabalhar." -ForegroundColor Green
exit 0
