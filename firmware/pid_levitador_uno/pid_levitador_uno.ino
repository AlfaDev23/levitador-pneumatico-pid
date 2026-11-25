/*
  Controle PID de altura - levitador pneumatico - Arduino Uno
  (placa na IDE: "Arduino Uno")

  Malha: sensor ultrassonico (topo) -> altura h -> PID + u0 -> PWM -> ventilador

  Ligacoes:
    Potenciometro (referencia de altura): cursor no A0, extremos em 5V e GND
    MOSFET: gate no D9 (100-220 ohm em serie + 10k do gate para o GND)
      O PWM usa o Timer1, por isso precisa ser o pino 9.
    HC-SR04: VCC no 5V, GND no GND, TRIG no D6, ECHO no D7 (direto, sem divisor)
    GND do Uno ligado ao GND da bateria (16 V)

  Internamente o PID usa as unidades do Simulink: altura em metros, saida em
  PWM (0-255), ganhos em PWM/m. No Monitor Serial as alturas aparecem em cm.
    u = u0 + Kp*e + Ki*integral(e) + Kd*de/dt      (forma paralela)

  Comandos no Monitor Serial (115200, terminar com Enter):
    z          zera a altura: deixe a bola parada no FUNDO e envie "z"
    s          para o motor (PWM = 0)
    a          liga o PID (decola sozinho; "auto-dec" = decolando)
    m 150      modo manual com PWM fixo (aceita decimais: m 122.5)
    f 300      muda a frequencia do PWM [Hz] (100 a 40000)
    r 14       referencia fixa em centimetros (melhor entre 13 e 17)
    p          referencia pelo potenciometro (12 a 17 cm)
    kp 130     | ki 5 | kd 250 | u0 127   -> altera os parametros
    lim 45     teto do PWM no ar = u0 + 45
    n 25       filtro da derivada [rad/s]
    wd 1       para o motor se o PC ficar 1 s sem enviar nada (wd 0 desliga)
    ?          mostra os parametros atuais

  Saida (uma linha a cada Ts):
    t=  12.34 s | ref= 25.0 cm | h= 24.3 cm | erro=   0.7 cm | PWM=130.50 | Kp= 56.00 Ki= 49.00 Kd= 16.00 | auto
  Ao ligar, o motor fica PARADO. Envie "z" e depois "a".

  Sintonia por Ziegler-Nichols (2o metodo) no sistema real:
    1) ki 0 e kd 0;  2) aumente kp ate a bola oscilar com amplitude constante
       -> esse kp e o Ku, e o periodo da oscilacao e o Tu (medir no grafico)
    3) kp = 0.6*Ku, ki = kp/(Tu/2), kd = kp*(Tu/8)
*/

// ---------------- Pinos ----------------
const int PINO_POT  = A0;
const int PINO_PWM  = 9;              // OC1A (Timer1)
const int PINO_TRIG = 6;
const int PINO_ECHO = 7;

// ---------------- Parametros ----------------
const float Ts = 0.040;               // periodo de amostragem [s]
const unsigned long TS_US = 40000UL;
unsigned long pwmFreq = 300;          // [Hz] (alteravel pelo comando "f")
const float PWM_MIN = 0, PWM_MAX = 255;   // escala usada no PID e no Simulink

// Ganhos obtidos por ajuste experimental na planta (ensaios voo3 e voo4).
float Kp = 130.0;                     // [PWM/m]
float Ki = 5.0;                       // [PWM/(m.s)]
float Kd = 250.0;                     // [PWM.s/m]
float u0 = 127.0;                     // PWM medio de equilibrio com a bola entre 12 e 18 cm
float N_filtro = 25.0;                // filtro da derivada [rad/s] (comando "n")

// Protecoes do modo automatico
float folga = 45.0;                   // teto do PWM no ar = u0 + folga (comando "lim")

// Decolagem: no fundo a bola pede mais PWM, e o ventilador demora a frear.
// Sobe com U0_DEC e teto baixo; ao passar de H_DECOLOU volta para u0.
const float U0_DEC = 138.0;
const float TETO_DEC = 149.0;
const float H_DECOLOU = 0.04;         // acima disso esta no ar
const float H_CAIU = 0.03;            // abaixo disso por T_CAIU: caiu, decola de novo
const byte  N_CAIU = 50;              // 2 s
const float H_REF_DEC = 0.08;         // decola mirando baixo e depois sobe em rampa
const float V_RAMPA = 0.02;           // [m/s]
bool noAr = false;
bool emRampa = true;                  // subindo da decolagem ate a referencia
float refRampa = H_REF_DEC;
byte nBaixo = 0;
const float H_FUNDO = 0.01;           // abaixo disso a bola esta no fundo: nao integra para cima
const float MARGEM_FUNDO = 0.03;      // leitura alem do fundo + margem e impossivel
const byte MAX_FALHAS = 8;            // leituras ruins seguidas (0,32 s) ate parar o motor
byte falhas = 0;
bool vigiarPC = false;                // "wd 1": para o motor se o computador ficar mudo por 1 s
unsigned long ultimoRx = 0;
const unsigned long TEMPO_MUDO_MS = 1000;

// Faixa de referencia [m]: o maximo sai do "z" (distFundo), para caber em qualquer tubo
const float H_REF_MIN = 0.02;         // margem no fundo
const float H_POT_MIN = 0.12;         // faixa do potenciometro: regiao em que o controle e estavel
const float H_POT_MAX = 0.17;
const float MARGEM_TOPO = 0.04;       // o HC-SR04 nao mede bem a menos de ~3 cm

// Sensor
const float VEL_SOM = 343.0;          // [m/s]
const unsigned long ECHO_TIMEOUT_US = 6000;   // ~1 m de distancia
float distFundo = 0.60;               // distancia sensor -> bola no fundo [m] (ajustada por "z")

// ---------------- Estado ----------------
enum Modo { PARADO, MANUAL, AUTOMATICO };
Modo modo = PARADO;
bool refPeloPot = true;
float refFixa = 0.30;
float pwmManual = 0;

float integral = 0;
float derivada = 0;
float hAnterior = 0;
float hBuf[3] = {0, 0, 0};
float ultimaDist = 0.60;
bool ecoOk = false;                   // a ultima medicao teve eco?
bool zerado = false;                  // o PID so liga depois de um "z" valido
unsigned long proximo = 0;

char entrada[24];
byte nEntrada = 0;

// ---------------- PWM (Timer1, phase correct, TOP = ICR1) ----------------
// Recebe o PWM na escala 0-255 (com casas decimais)
void escreverPWM(float pwm) {
  unsigned long duty = lround(constrain(pwm, PWM_MIN, PWM_MAX) / 255.0 * ICR1);
  noInterrupts();
  OCR1A = (uint16_t)duty;
  interrupts();
}

void configurarPWM(unsigned long freq) {
  bool baixa = freq < 150;            // abaixo disso o TOP nao cabe em 16 bits sem prescaler
  unsigned long top = F_CPU / (2UL * (baixa ? 8UL : 1UL) * freq);
  noInterrupts();
  TCCR1B = 0;                         // para o timer durante a troca
  TCCR1A = _BV(COM1A1) | _BV(WGM11);
  ICR1 = (uint16_t)top;
  OCR1A = 0;
  TCNT1 = 0;
  TCCR1B = _BV(WGM13) | (baixa ? _BV(CS11) : _BV(CS10));
  interrupts();
}

// ---------------- Sensor ----------------
float lerDistancia() {
  digitalWrite(PINO_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PINO_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PINO_TRIG, LOW);
  unsigned long t = pulseIn(PINO_ECHO, HIGH, ECHO_TIMEOUT_US);
  float d = t * 1e-6 * VEL_SOM / 2.0;
  ecoOk = (t != 0) && !(zerado && d > distFundo + MARGEM_FUNDO);
  if (!ecoOk) return ultimaDist;      // sem eco ou impossivel: mantem a ultima (a saida avisa)
  ultimaDist = d;
  return ultimaDist;
}

float mediana3(float a, float b, float c) {
  if (a > b) { float x = a; a = b; b = x; }
  if (b > c) { float x = b; b = c; c = x; }
  if (a > b) { float x = a; a = b; b = x; }
  return b;
}

float lerAltura() {
  float h = distFundo - lerDistancia();
  hBuf[0] = hBuf[1]; hBuf[1] = hBuf[2]; hBuf[2] = h;
  return mediana3(hBuf[0], hBuf[1], hBuf[2]);   // remove picos isolados do sensor
}

float refMaxima() {
  return max(H_REF_MIN, distFundo - MARGEM_TOPO);
}

float lerReferenciaPot() {
  long soma = 0;
  for (int i = 0; i < 8; i++) soma += analogRead(PINO_POT);
  float r = H_POT_MIN + (soma / 8.0) / 1023.0 * (H_POT_MAX - H_POT_MIN);
  return min(r, refMaxima());
}

// ---------------- PID ----------------
void resetarPID(float h) {
  integral = 0;
  derivada = 0;
  hAnterior = h;
}

float calcularPID(float ref, float h) {
  float e = ref - h;

  // Derivada sobre a medicao (evita pico na mudanca de referencia), filtrada
  float alfa = Ts / (Ts + 1.0 / N_filtro);
  derivada += alfa * (-(h - hAnterior) / Ts - derivada);
  hAnterior = h;

  float P = Kp * e;
  float D = Kd * derivada;
  // Decolagem automatica (e nova decolagem se a bola cair e ficar no fundo)
  if (!noAr && h > H_DECOLOU) { noAr = true; nBaixo = 0; }
  if (noAr) {
    nBaixo = (h < H_CAIU) ? nBaixo + 1 : 0;
    if (nBaixo >= N_CAIU) { noAr = false; nBaixo = 0; integral = 0; emRampa = true; }
  }
  float uBase = noAr ? u0 : U0_DEC;
  float uMax  = noAr ? constrain(u0 + folga, PWM_MIN, PWM_MAX) : TETO_DEC;
  float uSemI = uBase + P + Ki * integral + D;

  // Anti-windup por clamping: so integra se nao estiver saturado
  // ou se o erro estiver tirando a saida da saturacao.
  // Com a bola presa no fundo tambem nao integra para cima.
  bool satCima  = uSemI >= uMax && e > 0;
  bool satBaixo = uSemI <= PWM_MIN && e < 0;
  bool noFundo  = h < H_FUNDO && e > 0;
  if (!satCima && !satBaixo && !noFundo) integral += e * Ts;

  float u = uBase + P + Ki * integral + D;
  return constrain(u, PWM_MIN, uMax);
}

// ---------------- Impressao ----------------
// O printf do AVR nao imprime float: usa dtostrf para alinhar as colunas
void imprimir(const __FlashStringHelper *rotulo, float valor, int largura, int casas) {
  char buf[16];
  dtostrf(valor, largura, casas, buf);
  Serial.print(rotulo);
  Serial.print(buf);
}

void mostrarParametros() {
  imprimir(F("# Kp="), Kp, 1, 2);
  imprimir(F(" Ki="), Ki, 1, 2);
  imprimir(F(" Kd="), Kd, 1, 2);
  imprimir(F(" | u0="), u0, 1, 2);
  imprimir(F(" | lim=u0+"), folga, 1, 1);
  imprimir(F(" | N="), N_filtro, 1, 1);
  imprimir(F(" | fundo="), distFundo * 100, 1, 1);
  Serial.print(F(" cm | fPWM="));
  Serial.print(pwmFreq);
  Serial.print(F(" Hz | ref="));
  if (refPeloPot) {
    Serial.println(F("potenciometro"));
  } else {
    Serial.print(refFixa * 100, 1);
    Serial.println(F(" cm"));
  }
}

// ---------------- Comandos ----------------
void tratarComando(char *cmd) {
  char *nome = strtok(cmd, " ");
  if (nome == NULL) return;
  strlwr(nome);
  char *arg = strtok(NULL, " ");
  bool temValor = (arg != NULL);
  float valor = temValor ? atof(arg) : 0;

  if (!strcmp(nome, "z")) {
    // Mediana de 25 leituras: a media desloca o zero quando alguma leitura pula
    float v[25];
    int validas = 0;
    zerado = false;                   // aceita qualquer distancia enquanto mede o fundo
    for (int i = 0; i < 25; i++) {
      float d = lerDistancia();
      if (ecoOk) {
        int j = validas++;
        while (j > 0 && v[j - 1] > d) { v[j] = v[j - 1]; j--; }
        v[j] = d;
      }
      delay(38);
    }
    if (validas < 20) {
      Serial.println(F("# ERRO: sensor sem eco, zero NAO gravado"));
    } else {
      distFundo = v[validas / 2];
      zerado = true;
      imprimir(F("# leituras do zero: min="), v[0] * 100, 1, 1);
      imprimir(F(" max="), v[validas - 1] * 100, 1, 1);
      Serial.println(F(" cm"));
      for (int i = 0; i < 3; i++) hBuf[i] = 0;
      imprimir(F("# zero: distancia ate a bola no fundo = "), distFundo * 100, 1, 1);
      imprimir(F(" cm | referencia de "), H_REF_MIN * 100, 1, 1);
      imprimir(F(" a "), refMaxima() * 100, 1, 1);
      Serial.println(F(" cm"));
    }
    proximo = micros();               // o zero demora: recomeca a contagem do Ts
  } else if (!strcmp(nome, "s")) {
    modo = PARADO;
    Serial.println(F("# PARADO"));
  } else if (!strcmp(nome, "a") && !zerado) {
    Serial.println(F("# envie 'z' antes, com a bola parada no fundo"));
  } else if (!strcmp(nome, "a")) {
    resetarPID(hBuf[2]);
    falhas = 0;
    noAr = false;
    emRampa = true;
    nBaixo = 0;
    modo = AUTOMATICO;
    Serial.println(F("# PID ligado"));
  } else if (!strcmp(nome, "m") && temValor) {
    pwmManual = constrain(valor, PWM_MIN, PWM_MAX);
    modo = MANUAL;
    imprimir(F("# MANUAL: PWM = "), pwmManual, 1, 2);
    Serial.println();
  } else if (!strcmp(nome, "f") && temValor) {
    pwmFreq = constrain((long)valor, 100L, 40000L);
    configurarPWM(pwmFreq);
    Serial.print(F("# frequencia do PWM = "));
    Serial.print(pwmFreq);
    Serial.println(F(" Hz"));
  } else if (!strcmp(nome, "r") && temValor) {
    refFixa = valor / 100.0; refPeloPot = false;   // comando em cm, PID em m
    imprimir(F("# referencia fixa = "), refFixa * 100, 1, 1);
    Serial.println(F(" cm"));
  } else if (!strcmp(nome, "p")) {
    refPeloPot = true;
    Serial.println(F("# referencia pelo potenciometro"));
  } else if (!strcmp(nome, "kp") && temValor) { Kp = valor; mostrarParametros(); }
  else if (!strcmp(nome, "ki") && temValor) { Ki = valor; integral = 0; mostrarParametros(); }
  else if (!strcmp(nome, "kd") && temValor) { Kd = valor; mostrarParametros(); }
  else if (!strcmp(nome, "u0") && temValor) { u0 = valor; mostrarParametros(); }
  else if (!strcmp(nome, "wd") && temValor) {
    vigiarPC = (valor != 0);
    Serial.println(vigiarPC ? F("# vigia do PC LIGADA (1 s)") : F("# vigia do PC desligada"));
  }
  else if (!strcmp(nome, "n") && temValor) { N_filtro = constrain(valor, 1.0, 100.0); mostrarParametros(); }
  else if (!strcmp(nome, "lim") && temValor) { folga = constrain(valor, 0.0, 255.0); mostrarParametros(); }
  else if (!strcmp(nome, "?")) { mostrarParametros(); }
  else { Serial.println(F("# comando invalido (envie ? para ver os parametros)")); }
}

void lerSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    ultimoRx = millis();              // qualquer byte (ate Enter sozinho) vale como sinal do PC
    if (c == '\n' || c == '\r') {
      entrada[nEntrada] = '\0';
      tratarComando(entrada);
      nEntrada = 0;
    } else if (nEntrada < sizeof(entrada) - 1) {
      entrada[nEntrada++] = c;
    }
  }
}

// ---------------- Setup / Loop ----------------
void setup() {
  digitalWrite(PINO_PWM, LOW);        // motor desligado antes de tudo
  pinMode(PINO_PWM, OUTPUT);
  configurarPWM(pwmFreq);

  Serial.begin(115200);
  pinMode(PINO_TRIG, OUTPUT);
  pinMode(PINO_ECHO, INPUT);

  delay(1000);
  Serial.println(F("# PID levitador (Uno) - motor PARADO. Envie 'z' (bola no fundo) e depois 'a'."));
  mostrarParametros();
  Serial.println(F("# ganhos em PWM/m (mesmas unidades do Simulink)"));
  proximo = micros();
}

void loop() {
  lerSerial();
  if ((long)(micros() - proximo) < 0) return;
  proximo += TS_US;

  float h   = lerAltura();
  float ref = refPeloPot ? lerReferenciaPot() : constrain(refFixa, H_REF_MIN, refMaxima());

  // Sensor perdido no automatico: para em vez de controlar com leitura velha
  falhas = ecoOk ? 0 : min(falhas + 1, 255);
  if (modo == AUTOMATICO && falhas >= MAX_FALHAS) {
    modo = PARADO;
    Serial.println(F("# PARADO: sensor sem leitura valida"));
  }

  // Referencia da decolagem: 8 cm no chao, depois rampa; em voo os degraus passam direto
  if (modo == AUTOMATICO && emRampa) {
    if (!noAr) refRampa = min(H_REF_DEC, ref);
    else if (refRampa + V_RAMPA * Ts < ref) refRampa += V_RAMPA * Ts;
    else emRampa = false;
    if (emRampa) ref = refRampa;
  }

  if (vigiarPC && modo != PARADO && millis() - ultimoRx > TEMPO_MUDO_MS) {
    modo = PARADO;
    Serial.println(F("# PARADO: sem sinal do computador"));
  }

  float pwm = 0;
  if (modo == AUTOMATICO) pwm = calcularPID(ref, h);
  else if (modo == MANUAL) pwm = pwmManual;
  escreverPWM(pwm);

  imprimir(F("t="), millis() / 1000.0, 7, 2);
  imprimir(F(" s | ref="), ref * 100, 5, 1);
  imprimir(F(" cm | h="), h * 100, 5, 1);
  imprimir(F(" cm | erro="), (ref - h) * 100, 6, 1);
  imprimir(F(" cm | PWM="), pwm, 6, 2);
  imprimir(F(" | Kp="), Kp, 6, 2);
  imprimir(F(" Ki="), Ki, 6, 2);
  imprimir(F(" Kd="), Kd, 6, 2);
  Serial.print(F(" | "));
  if (modo == AUTOMATICO) Serial.print(noAr ? F("auto") : F("auto-dec"));
  else if (modo == MANUAL) Serial.print(F("manual"));
  else Serial.print(F("parado"));
  Serial.println(ecoOk ? F("") : F(" | SEM ECO"));
}
