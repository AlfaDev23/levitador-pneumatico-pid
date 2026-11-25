# Resume o ensaio mais recente com o nome dado (so os trechos em modo auto).
param([string]$Nome, [int]$Cada = 4)
$inv = [Globalization.CultureInfo]::InvariantCulture
$f = Get-ChildItem (Join-Path $PSScriptRoot "dados\${Nome}_*.txt") | Sort-Object LastWriteTime | Select-Object -Last 1
$linhas = Get-Content $f.FullName
$linhas | Where-Object { $_ -match '^# PARADO:' }
$r = @($linhas | ForEach-Object {
  if ($_ -match '^t=\s*([\d.]+) s \| ref=\s*([\d.]+) cm \| h=\s*(-?[\d.]+) cm.*PWM=\s*([\d.]+) \| (Kp=.*Kd=\s*[\d.]+).*\| auto') {
    [pscustomobject]@{ t=[double]::Parse($matches[1],$inv); ref=[double]::Parse($matches[2],$inv); h=[double]::Parse($matches[3],$inv); u=[double]::Parse($matches[4],$inv); k="ref=$($matches[2]) " + ($matches[5] -replace '\s+',' ') } } })
$grupos = New-Object System.Collections.Generic.List[object]
foreach ($x in $r) { if ($grupos.Count -eq 0 -or $grupos[-1].k -ne $x.k) { $grupos.Add([pscustomobject]@{ k=$x.k; d=(New-Object System.Collections.Generic.List[object]) }) }; $grupos[-1].d.Add($x) }
foreach ($g in $grupos) {
  $s = $g.d.h | Measure-Object -Average -Minimum -Maximum
  "{0} | {1:F1} s | h med={2:F1} min={3:F1} max={4:F1} | u med={5:F1}" -f $g.k, ($g.d.Count*0.04), $s.Average, $s.Minimum, $s.Maximum, ($g.d.u | Measure-Object -Average).Average
  $hs=@(); $us=@(); for ($i=0; $i -lt $g.d.Count; $i+=$Cada) { $hs += $g.d[$i].h.ToString('F0',$inv); $us += $g.d[$i].u.ToString('F0',$inv) }
  "  h: " + ($hs -join ' '); "  u: " + ($us -join ' ')
}
"SEM ECO: " + @($linhas -match 'SEM ECO').Count
