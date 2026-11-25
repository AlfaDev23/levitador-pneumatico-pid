# Ensaios do levitador pelo Arduino Uno (feche o Monitor Serial antes).
# O MOTOR LIGA: fique ao lado do tubo, com a mao na chave da bateria.
#
#  Rampa (acha o PWM em que a bola sai do fundo):
#    .\ensaio.ps1 -Porta COM10 -Modo rampa
#  Roteiro ("comando@segundos", separados por ponto e virgula):
#    .\ensaio.ps1 -Porta COM10 -Modo roteiro -Roteiro "ki 0@0.2;kd 0@0.2;kp 20@0.2;r 10@0.2;a@10"
#
# Para o motor sozinho se: h > HMax, 5 linhas seguidas SEM ECO, 0,6 s sem dados
# ou TempoMax. No fim sempre envia "s" e reinicia o Uno (que liga parado).
param(
  [Parameter(Mandatory=$true)][string]$Porta,
  [ValidateSet('rampa','roteiro')][string]$Modo = 'rampa',
  [string]$Roteiro = '',
  [double]$HMax = 15,
  [int]$LinhasHMax = 1,
  [double]$PwmIni = 40, [double]$PwmFim = 200, [double]$Passo = 1, [double]$TPasso = 0.4,
  [double]$HSaiu = 3,
  [double]$TempoMax = 80,
  [string]$Nome = 'ensaio'
)
$inv = [Globalization.CultureInfo]::InvariantCulture
$pasta = Join-Path $PSScriptRoot 'dados'
if (-not (Test-Path $pasta)) { New-Item -ItemType Directory -Path $pasta | Out-Null }
$arq = Join-Path $pasta ("{0}_{1:yyyyMMdd_HHmmss}.txt" -f $Nome, (Get-Date))
$log = New-Object System.Collections.Generic.List[string]
$script:buf = ''; $script:h = [double]::NaN; $script:semEco = 0; $script:alto = 0
$script:ultimo = Get-Date; $script:motivo = ''; $script:linhas = 0; $script:vigiar = $false
$inicio = Get-Date; $script:batida = Get-Date

function Enviar($c) { $log.Add(">> $c"); $p.WriteLine($c) }

function Processar {
  # sinal de vida: sem ele o Uno desliga o motor sozinho (comando "wd 1")
  if ($script:vigiar -and ((Get-Date) - $script:batida).TotalMilliseconds -gt 200) { $p.Write("`n"); $script:batida = Get-Date }
  $script:buf += $p.ReadExisting()
  while (($i = $script:buf.IndexOf("`n")) -ge 0) {
    $l = $script:buf.Substring(0, $i).Trim(); $script:buf = $script:buf.Substring($i + 1)
    if (-not $l) { continue }
    $log.Add($l); $script:ultimo = Get-Date
    if ($l -match '^t=.*\| h=\s*(-?[\d.]+) cm') {
      $script:h = [double]::Parse($matches[1], $inv); $script:linhas++
      if ($l -match 'SEM ECO') { $script:semEco++ } else { $script:semEco = 0 }
      if ($script:h -gt $HMax) { $script:alto++ } else { $script:alto = 0 }
      if ($script:vigiar) {
        if ($script:alto -ge $LinhasHMax) { $script:motivo = "h=$($script:h) acima de $HMax cm" }
        if ($script:semEco -ge 5) { $script:motivo = 'sensor sem eco' }
      }
    }
  }
  if ($script:vigiar -and ((Get-Date) - $script:ultimo).TotalSeconds -gt 0.6) { $script:motivo = 'sem dados do Uno' }
  if (((Get-Date) - $inicio).TotalSeconds -gt $TempoMax) { $script:motivo = 'tempo maximo' }
}

function Esperar([double]$s) {
  $fim = (Get-Date).AddSeconds($s)
  while ((Get-Date) -lt $fim -and -not $script:motivo) { Processar; Start-Sleep -Milliseconds 10 }
}

$p = New-Object System.IO.Ports.SerialPort $Porta, 115200
$p.DtrEnable = $true; $p.RtsEnable = $true; $p.NewLine = "`n"; $p.WriteTimeout = 500
$parou = $false
try {
  $p.Open()
  Esperar 3.5
  Enviar 'z'; Esperar 2.5
  $zero = $log | Where-Object { $_ -match '^# (zero|ERRO|leituras do zero)' }
  $zero
  if (-not ($zero -match '^# zero')) { throw 'zero nao gravado: motor nao foi ligado' }
  if ([math]::Abs($script:h) -gt 1.5) { throw "h=$($script:h) depois do zero: motor nao foi ligado" }
  Enviar 'wd 1'; Esperar 0.4
  if (-not ($log -match 'vigia do PC LIGADA')) { throw 'vigia do PC nao confirmada: motor nao foi ligado' }
  $script:vigiar = $true

  if ($Modo -eq 'rampa') {
    $saiu = 0; $u = $PwmIni
    while ($u -le $PwmFim -and -not $script:motivo) {
      Enviar ("m " + $u.ToString($inv)); Esperar $TPasso
      if ($script:h -gt $HSaiu) { $saiu++ } else { $saiu = 0 }
      if ($saiu -ge 2) { $script:motivo = "bola saiu do fundo (h=$($script:h))" }
      if (-not $script:motivo) { $u += $Passo }
    }
    "PWM ao terminar a rampa: $u"
  } else {
    foreach ($item in ($Roteiro -split ';')) {
      if ($script:motivo) { break }
      $x = $item -split '@'
      Enviar $x[0].Trim()
      if ($x[1] -match '^h(.+)$') {
        # "@h4": espera a bola passar de 4 cm (no maximo 12 s)
        $alvo = [double]::Parse($matches[1], $inv); $fim = (Get-Date).AddSeconds(12)
        while ($script:h -le $alvo -and -not $script:motivo) {
          Processar; Start-Sleep -Milliseconds 10
          if ((Get-Date) -gt $fim) { $script:motivo = "a bola nao passou de $alvo cm" }
        }
      } else { Esperar ([double]::Parse($x[1], $inv)) }
    }
  }
} catch { "ERRO: $($_.Exception.Message)" }
finally {
  $script:vigiar = $false
  try {
    foreach ($k in 1..3) { $log.Add('>> s'); $p.WriteLine('s'); Start-Sleep -Milliseconds 60 }
    $fim = (Get-Date).AddSeconds(1.2)
    while ((Get-Date) -lt $fim) { Start-Sleep -Milliseconds 20; $log.Add(($p.ReadExisting()).TrimEnd()) }
    $parou = (($log | Select-Object -Last 30) -join "`n") -match 'parado'
    $p.DtrEnable = $false; Start-Sleep -Milliseconds 100; $p.DtrEnable = $true
    Start-Sleep -Milliseconds 200; $p.Close()
  } catch { "FALHA AO PARAR: DESLIGUE A BATERIA ($($_.Exception.Message))" }
  if (-not $parou) { 'ATENCAO: parada nao confirmada, desligue a bateria' } else { 'motor parado (confirmado)' }
  [IO.File]::WriteAllLines($arq, $log)
  "fim: $(if ($script:motivo) { $script:motivo } else { 'roteiro completo' }) | linhas: $($script:linhas)"
  "arquivo: $arq"
}
