param(
    [string]$SourceDirectory = "C:\Users\Dell\Desktop\meu_sistema_rouanet\3. 1961",
    [string]$StatePath = (Join-Path $env:TEMP "rouanet-w2t4-current.json")
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$source = (Resolve-Path -LiteralPath $SourceDirectory).Path
$smokeRoot = Join-Path $env:TEMP ("rouanet-w2t4-" + [guid]::NewGuid().ToString("N"))
$uploadDir = Join-Path $smokeRoot "uploads"
$dbContainer = "rouanet_w2t4_smoke_" + [guid]::NewGuid().ToString("N").Substring(0, 10)
$backendProc = $null
$frontendProc = $null

function Remove-SmokeRootSafely([string]$Path) {
    if (-not $Path) { return }
    $resolved = [IO.Path]::GetFullPath($Path)
    $tempBase = [IO.Path]::GetFullPath($env:TEMP).TrimEnd("\") + "\"
    if (-not $resolved.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Diretório temporário fora do escopo esperado; limpeza cancelada."
    }
    if (Test-Path -LiteralPath $resolved) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}

try {
    New-Item -ItemType Directory -Path $uploadDir -Force | Out-Null

    # Não imprime nem persiste o nome original.
    $realPdf = Get-ChildItem -LiteralPath $source -File -Recurse |
        Where-Object {
            $_.Extension -ieq ".pdf" -and $_.Length -gt 1024 -and $_.Length -le 10MB
        } |
        Sort-Object Length |
        Select-Object -First 1
    if (-not $realPdf) { throw "Nenhum PDF elegível para o smoke." }

    $neutralPdf = Join-Path $smokeRoot "documento-teste-real.pdf"
    Copy-Item -LiteralPath $realPdf.FullName -Destination $neutralPdf

    $dbPassword = "w2t4db" + [guid]::NewGuid().ToString("N")
    docker run --name $dbContainer --rm -d `
        -p "127.0.0.1:55432:5432" `
        -e POSTGRES_USER=rouanet `
        -e POSTGRES_PASSWORD=$dbPassword `
        -e POSTGRES_DB=rouanet_concilia `
        postgres:16-alpine | Out-Null

    $dbReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        $PSNativeCommandUseErrorActionPreference = $false
        docker exec $dbContainer pg_isready -U rouanet -d rouanet_concilia 2>$null | Out-Null
        $readyExitCode = $LASTEXITCODE
        $PSNativeCommandUseErrorActionPreference = $true
        if ($readyExitCode -eq 0) { $dbReady = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $dbReady) { throw "Banco descartável não ficou pronto." }

    $jwtSecret = "w2t4jwt" + [guid]::NewGuid().ToString("N")
    $env:DATABASE_URL = "postgresql://rouanet:$dbPassword@127.0.0.1:55432/rouanet_concilia"
    $env:SUPABASE_JWT_SECRET = $jwtSecret
    $env:SUPABASE_URL = ""
    $env:SUPABASE_SERVICE_ROLE_KEY = ""
    $env:GOOGLE_API_KEY = ""
    $env:OCR_BACKEND = "disabled"
    $env:APP_ENV = "dev"
    $env:CORS_ORIGINS = "http://127.0.0.1:5174,http://localhost:5174"
    $env:UPLOAD_DIR = $uploadDir

    $python = (Resolve-Path -LiteralPath (Join-Path $repo ".venv\Scripts\python.exe")).Path
    $backendOut = Join-Path $smokeRoot "backend.out.log"
    $backendErr = Join-Path $smokeRoot "backend.err.log"
    $backendProc = Start-Process `
        -FilePath $python `
        -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "58000") `
        -WorkingDirectory $repo `
        -RedirectStandardOutput $backendOut `
        -RedirectStandardError $backendErr `
        -WindowStyle Hidden `
        -PassThru

    $api = "http://127.0.0.1:58000"
    $backendReady = $false
    for ($i = 0; $i -lt 60; $i++) {
        try {
            Invoke-RestMethod -Uri "$api/health/db" -TimeoutSec 2 | Out-Null
            $backendReady = $true
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $backendReady) {
        $tail = if (Test-Path -LiteralPath $backendErr) {
            (Get-Content -LiteralPath $backendErr -Tail 20) -join " | "
        } else { "sem log" }
        throw "Backend não iniciou: $tail"
    }

    $migrationCount = [int](
        docker exec $dbContainer psql -U rouanet -d rouanet_concilia -qAt `
            -c "select count(*) from schema_migrations;"
    )
    if ($migrationCount -ne 14) {
        throw "Migrations incompletas: $migrationCount de 14."
    }

    $userId = [guid]::NewGuid().ToString()
    $insertUser = "insert into auth.users(id,email) values ('$userId'::uuid,'smoke@rouanet.local');"
    docker exec $dbContainer psql -U rouanet -d rouanet_concilia -v ON_ERROR_STOP=1 -q -c $insertUser | Out-Null

    $tokenScript = "import jwt,sys,time; n=int(time.time()); print(jwt.encode({'sub':sys.argv[1],'email':sys.argv[3],'role':'authenticated','aud':'authenticated','iat':n,'exp':n+28800},sys.argv[2],algorithm='HS256'))"
    $token = & $python -c $tokenScript $userId $jwtSecret "smoke@rouanet.local"
    $auth = @{ Authorization = "Bearer $token" }

    $pronacSmoke = "SMOKE-" + [guid]::NewGuid().ToString("N").Substring(0, 12)
    $project = Invoke-RestMethod `
        -Method Post `
        -Uri "$api/api/v1/projetos" `
        -Headers $auth `
        -ContentType "application/json" `
        -Body (@{
            pronac = $pronacSmoke
            nome = "Smoke local de documento real"
            proponente = "Teste local"
            banco_nome = "Banco de teste"
        } | ConvertTo-Json)
    $projectId = $project.id

    $sqlTransacao = "insert into transacoes (projeto_id, fornecedor, data_pagamento, valor_bruto, valor_liquido, status) values ('$projectId'::uuid, 'Fornecedor de teste local', current_date, 1.00, 1.00, 'PENDENTE') returning id;"
    $transactionId = (
        docker exec $dbContainer psql -U rouanet -d rouanet_concilia -qAt -c $sqlTransacao
    ).Trim()
    if (-not $transactionId) { throw "Não foi possível criar a transação sintética." }

    $documento = Invoke-RestMethod `
        -Method Post `
        -Uri "$api/api/v1/projetos/$projectId/transacoes/$transactionId/documento" `
        -Headers $auth `
        -Form @{ arquivo = Get-Item -LiteralPath $neutralPdf }
    $documentId = $documento.documento_id
    if (-not $documentId) { throw "Upload não retornou documento_id." }

    $downloadedPdf = Join-Path $smokeRoot "documento-baixado.pdf"
    $response = Invoke-WebRequest `
        -Method Get `
        -Uri "$api/api/v1/documentos/$documentId/arquivo" `
        -Headers $auth `
        -OutFile $downloadedPdf `
        -PassThru

    if ($response.StatusCode -ne 200) { throw "Download autorizado falhou." }
    if ([string]$response.Headers["Content-Type"] -notlike "application/pdf*") {
        throw "Content-Type incorreto."
    }
    if ([string]$response.Headers["X-Content-Type-Options"] -ne "nosniff") {
        throw "Cabeçalho nosniff ausente."
    }
    if ([string]$response.Headers["Content-Disposition"] -notmatch "inline") {
        throw "Content-Disposition seguro ausente."
    }

    $hashOriginal = (Get-FileHash -LiteralPath $neutralPdf -Algorithm SHA256).Hash
    $hashBaixado = (Get-FileHash -LiteralPath $downloadedPdf -Algorithm SHA256).Hash
    if ($hashOriginal -ne $hashBaixado) { throw "PDF baixado difere do PDF enviado." }

    $outroUserId = [guid]::NewGuid().ToString()
    $insertOutro = "insert into auth.users(id,email) values ('$outroUserId'::uuid,'nao-membro@rouanet.local');"
    docker exec $dbContainer psql -U rouanet -d rouanet_concilia -v ON_ERROR_STOP=1 -q -c $insertOutro | Out-Null
    $outroToken = & $python -c $tokenScript $outroUserId $jwtSecret "nao-membro@rouanet.local"
    $negado = Invoke-WebRequest `
        -Method Get `
        -Uri "$api/api/v1/documentos/$documentId/arquivo" `
        -Headers @{ Authorization = "Bearer $outroToken" } `
        -SkipHttpErrorCheck
    if ($negado.StatusCode -ne 404) {
        throw "Controle de acesso negativo retornou HTTP $([int]$negado.StatusCode)."
    }

    $env:VITE_API_URL = $api
    $env:VITE_WS_URL = "ws://127.0.0.1:58000"
    $node = (Get-Command node.exe).Source
    $vite = Join-Path $repo "frontend\node_modules\vite\bin\vite.js"
    $frontendOut = Join-Path $smokeRoot "frontend.out.log"
    $frontendErr = Join-Path $smokeRoot "frontend.err.log"
    $frontendProc = Start-Process `
        -FilePath $node `
        -ArgumentList @($vite, "--host", "127.0.0.1", "--port", "5174") `
        -WorkingDirectory (Join-Path $repo "frontend") `
        -RedirectStandardOutput $frontendOut `
        -RedirectStandardError $frontendErr `
        -WindowStyle Hidden `
        -PassThru

    $frontendReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $frontResponse = Invoke-WebRequest -Uri "http://127.0.0.1:5174" -TimeoutSec 2
            if ($frontResponse.StatusCode -eq 200) { $frontendReady = $true; break }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $frontendReady) { throw "Frontend não iniciou." }

    [ordered]@{
        smoke_root = $smokeRoot
        db_container = $dbContainer
        backend_pid = $backendProc.Id
        frontend_pid = $frontendProc.Id
        project_id = $projectId
        document_id = $documentId
        api = $api
        ui = "http://127.0.0.1:5174"
    } | ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding utf8

    [ordered]@{
        status = "PASS"
        migrations = $migrationCount
        upload_download_hash = "MATCH"
        authorized_status = 200
        unauthorized_status = [int]$negado.StatusCode
        content_type = [string]$response.Headers["Content-Type"]
        nosniff = [string]$response.Headers["X-Content-Type-Options"]
        disposition_inline = ([string]$response.Headers["Content-Disposition"] -match "inline")
        ui = "http://127.0.0.1:5174"
        project_ready = $true
        state_path = $StatePath
    } | ConvertTo-Json -Compress
} catch {
    $failureMessage = $_.Exception.Message
    $backendTail = if ($backendErr -and (Test-Path -LiteralPath $backendErr)) {
        (Get-Content -LiteralPath $backendErr -Tail 60) -join " | "
    } else { "sem log do backend" }
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($backendProc -and -not $backendProc.HasExited) {
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
    docker stop $dbContainer 2>$null | Out-Null
    Remove-SmokeRootSafely $smokeRoot
    throw "$failureMessage Backend: $backendTail"
}
