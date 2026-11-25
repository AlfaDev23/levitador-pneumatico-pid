# Ensaios e análise

## Gravar um ensaio

O script `ensaio.ps1` (Windows PowerShell) envia comandos ao Arduino, grava a saída em `ensaios/dados` e desliga o motor se a bola passar da altura máxima, se o sensor falhar ou se o Arduino parar de responder. Feche o Monitor Serial antes.

> [!WARNING]
> O motor liga durante o ensaio. Fique ao lado do tubo, com a mão na chave da bateria.

Rampa de PWM, para descobrir quando a bola sai do fundo:

```powershell
.\ensaios\ensaio.ps1 -Porta COM10 -Modo rampa
```

Roteiro de comandos, no formato `comando@segundos`. O script envia o `z` sozinho no começo e o `s` no fim:

```powershell
.\ensaios\ensaio.ps1 -Porta COM10 -Modo roteiro -Nome voo -HMax 23 -Roteiro "r 13@0.2;a@24;r 16@22"
```

Resumo do ensaio mais recente com um nome:

```powershell
.\ensaios\resumo.ps1 -Nome voo
```

## Scripts de análise

Rode a partir da pasta `ensaios`:

```bash
pip install -r requirements.txt
cd ensaios
python graficos.py
```

| Script | Função |
|:--|:--|
| `graficos.py` | Gera os gráficos do voo e do PWM por altura |
| `metricas.py final2` | Desempenho de um ensaio, por trecho |
| `identificar.py` | Ajuste do modelo aos disparos, que não convergiu para valores confiáveis |
| `identificar_voos.py` | Identificação com filtro de Kalman estendido nos voos |
| `refinar_ident.py` | Refina e valida em voos que ficaram fora do ajuste |
| `prever.py` | Compara modelos pela previsão de 0,2 a 1 s à frente |
| `perfil.py` | Verifica se os dados distinguem as hipóteses |
| `buscar_ganhos.py` | Procura ganhos que sirvam para todos os modelos compatíveis |
| `bateria.py` | Procura variação do PWM de equilíbrio com o tempo |

## Dados

Cada arquivo em `ensaios/dados` traz a saída serial de um ensaio, com nome, data e hora.

| Prefixo | Ensaio |
|:--|:--|
| `rampa` | PWM subindo aos poucos |
| `kp`, `kp2` | Só ação proporcional |
| `pid1` a `pid3` | Primeiras tentativas com PID |
| `parado` | Leituras do sensor com o motor desligado |
| `teto1` a `teto3` | Testes do limite de PWM |
| `voo1` a `voo4` | Voos controlados, usados no ajuste dos ganhos |
| `final1`, `final2` | Ensaios finais. O `final2` é o dos gráficos |
