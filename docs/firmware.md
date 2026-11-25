# Firmware

## Programas

| Pasta | Placa | Para que serve |
|:--|:--|:--|
| `pid_levitador_uno` | Arduino Uno | **Versão principal**, calibrada e usada nos ensaios |
| `pid_levitador_uno_bateria` | Arduino Uno | Compensa a queda da bateria. Compila, mas **não foi testada** no sistema real |
| `diagnostico_sensor_uno` | Arduino Uno | Testa o HC-SR04 com o motor desligado |
| `pid_levitador` | ESP32-C3 | Versão antiga do PID |
| `teste_pwm_potenciometro` | ESP32-C3 | Primeiro teste de acionamento do motor |

## Lei de controle

$$u = u_0 + K_p\,e + K_i\int e\,dt - K_d\,\frac{dh}{dt}, \qquad e = r - h$$

- `u0` entrega quase todo o ar necessário, e o PID cuida das correções.
- A derivada usa a altura medida, o que evita um tranco quando a referência muda, e passa por um filtro de 25 rad/s.
- A integral para de acumular quando o PWM satura ou quando a bola está no fundo (anti-windup).
- A altura é a distância medida com a bola no fundo menos a distância atual, e usa a mediana das três últimas leituras.

## Decolagem automática

Sair do fundo exige mais ar do que flutuar, então a decolagem tem valores próprios:

| Fase | `u0` | Limite de PWM | Referência |
|:--|--:|--:|:--|
| No fundo | 138 | 149 | 8 cm |
| No ar (acima de 4 cm) | 127 | 172 | Sobe 2 cm/s até a altura pedida |

Se a bola passar 2 s abaixo de 3 cm, o programa decola de novo.

## Proteções

- O motor começa parado, e o PID só liga depois de um `z` válido.
- Oito leituras ruins seguidas (0,32 s) param o motor.
- Leituras além do fundo são descartadas.
- Com `wd 1`, o motor para se o computador ficar 1 s sem enviar dados.

## Comandos (115200 baud, terminar com Enter)

| Comando | Efeito |
|:--|:--|
| `z` | Zera a altura, com a bola parada no fundo |
| `a` | Liga o PID e decola |
| `s` | Para o motor |
| `m 120` | Modo manual, com PWM fixo e **sem** o limite do modo automático |
| `r 14` | Referência fixa, em cm |
| `p` | Referência pelo potenciômetro (12 a 17 cm) |
| `kp 130`, `ki 5`, `kd 250` | Ganhos |
| `u0 127` | PWM de equilíbrio |
| `lim 45` | Limite de PWM no ar, acima de `u0` |
| `n 25` | Filtro da derivada, em rad/s |
| `f 300` | Frequência do PWM, em Hz |
| `wd 1` | Vigia do computador (`wd 0` desliga) |
| `?` | Mostra os parâmetros atuais |

## Saída serial

Uma linha a cada 40 ms:

```text
t=  12.34 s | ref= 14.0 cm | h= 13.6 cm | erro=   0.4 cm | PWM=130.50 | Kp=130.00 Ki=  5.00 Kd=250.00 | auto
```

O último campo é `parado`, `manual`, `auto-dec` (decolando) ou `auto`. Quando o sensor falha, a linha termina com `SEM ECO`.
