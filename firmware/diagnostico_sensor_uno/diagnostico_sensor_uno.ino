/*
  Diagnostico do HC-SR04 dentro do tubo - Arduino Uno
  O MOTOR FICA SEMPRE DESLIGADO (D9 em nivel baixo).

  Ligacoes: TRIG no D6, ECHO no D7 (direto), VCC no 5V, GND no GND

  Mostra a leitura bruta, sem filtro e sem repetir a ultima leitura.
  A cada 50 disparos imprime um resumo.

  Comandos no Monitor Serial (115200, terminar com Enter):
    t 60    intervalo entre disparos em ms (30 a 500)
    r 20    distancia real medida com a regua [cm], para calcular o erro
    r 0     esquece a distancia real
    l       liga/desliga a impressao de cada leitura (o resumo continua)
    ?       mostra a configuracao

  Resultado de cada disparo:
    OK        eco valido
    SEM ALVO  o sensor respondeu, mas nao recebeu eco em 2 m
    MUDO      o ECHO nunca subiu: fio, alimentacao ou disparo ignorado
    PRESO     o ECHO ja estava alto antes do disparo: fio solto ou ainda
              ocupado com o disparo anterior
*/

const int PINO_PWM  = 9;
const int PINO_TRIG = 6;
const int PINO_ECHO = 7;

const float CM_POR_US = 0.0343 / 2.0;
const unsigned long ESPERA_SUBIR_US = 5000;    // o ECHO sobe ~0,5 ms depois do disparo
const unsigned long MAX_ECO_US = 11700;        // ~2 m

const int N = 50;                              // disparos por resumo
int leituras[N];                               // leituras validas [mm]
int nOk = 0, nSemAlvo = 0, nMudo = 0, nPreso = 0, nTotal = 0;
int nSaltos = 0;                               // diferenca > 3 cm para a leitura valida anterior
int anterior = -1;

unsigned long periodoMs = 60;
unsigned long proximo = 0;
float distReal = 0;
bool imprimirCada = true;

char entrada[16];
byte nEntrada = 0;

enum Resultado { OK, SEM_ALVO, MUDO, PRESO };

Resultado medir(unsigned long &largura) {
  largura = 0;
  if (digitalRead(PINO_ECHO) == HIGH) return PRESO;

  digitalWrite(PINO_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PINO_TRIG, LOW);

  unsigned long t0 = micros();
  while (digitalRead(PINO_ECHO) == LOW) {
    if (micros() - t0 > ESPERA_SUBIR_US) return MUDO;
  }
  unsigned long subida = micros();
  while (digitalRead(PINO_ECHO) == HIGH) {
    if (micros() - subida > MAX_ECO_US) return SEM_ALVO;
  }
  largura = micros() - subida;
  return OK;
}

void ordenar(int *v, int n) {
  for (int i = 1; i < n; i++) {
    int x = v[i], j = i - 1;
    while (j >= 0 && v[j] > x) { v[j + 1] = v[j]; j--; }
    v[j + 1] = x;
  }
}

void mostrarConfig() {
  Serial.print(F("# intervalo = "));
  Serial.print(periodoMs);
  Serial.print(F(" ms | distancia real = "));
  if (distReal > 0) { Serial.print(distReal, 1); Serial.println(F(" cm")); }
  else Serial.println(F("nao informada"));
}

void zerarResumo() {
  nOk = nSemAlvo = nMudo = nPreso = nTotal = nSaltos = 0;
  anterior = -1;
}

void mostrarResumo() {
  Serial.print(F("# RESUMO ["));
  Serial.print(periodoMs);
  Serial.print(F(" ms] OK="));
  Serial.print(100L * nOk / N);
  Serial.print(F("% SEM ALVO="));
  Serial.print(100L * nSemAlvo / N);
  Serial.print(F("% MUDO="));
  Serial.print(100L * nMudo / N);
  Serial.print(F("% PRESO="));
  Serial.print(100L * nPreso / N);
  Serial.print(F("%"));
  if (nOk > 0) {
    ordenar(leituras, nOk);
    Serial.print(F(" | min="));
    Serial.print(leituras[0] / 10.0, 1);
    Serial.print(F(" mediana="));
    Serial.print(leituras[nOk / 2] / 10.0, 1);
    Serial.print(F(" max="));
    Serial.print(leituras[nOk - 1] / 10.0, 1);
    Serial.print(F(" cm | saltos="));
    Serial.print(nSaltos);
    if (distReal > 0) {
      Serial.print(F(" | real="));
      Serial.print(distReal, 1);
      Serial.print(F(" erro="));
      Serial.print(leituras[nOk / 2] / 10.0 - distReal, 1);
      Serial.print(F(" cm"));
    }
  }
  Serial.println();
}

void tratarComando(char *cmd) {
  char *nome = strtok(cmd, " ");
  if (nome == NULL) return;
  strlwr(nome);
  char *arg = strtok(NULL, " ");

  if (!strcmp(nome, "t") && arg) {
    periodoMs = constrain(atol(arg), 30L, 500L);
    proximo = millis();
    mostrarConfig();
  } else if (!strcmp(nome, "r") && arg) {
    distReal = atof(arg);
    mostrarConfig();
  } else if (!strcmp(nome, "l")) {
    imprimirCada = !imprimirCada;
  } else if (!strcmp(nome, "?")) {
    mostrarConfig();
  } else {
    Serial.println(F("# comandos: t 60 | r 20 | l | ?"));
    return;
  }
  zerarResumo();                      // nao mistura configuracoes no mesmo resumo
}

void lerSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      entrada[nEntrada] = '\0';
      tratarComando(entrada);
      nEntrada = 0;
    } else if (nEntrada < sizeof(entrada) - 1) {
      entrada[nEntrada++] = c;
    }
  }
}

void setup() {
  digitalWrite(PINO_PWM, LOW);
  pinMode(PINO_PWM, OUTPUT);          // motor sempre desligado
  digitalWrite(PINO_TRIG, LOW);
  pinMode(PINO_TRIG, OUTPUT);
  pinMode(PINO_ECHO, INPUT_PULLUP);   // fio solto aparece como PRESO, e nao como leitura falsa

  Serial.begin(115200);
  Serial.println(F("# Diagnostico do HC-SR04 - motor sempre DESLIGADO"));
  Serial.println(F("# comandos: t 60 | r 20 | l | ?"));
  mostrarConfig();
  proximo = millis();
}

void loop() {
  lerSerial();
  if ((long)(millis() - proximo) < 0) return;
  proximo += periodoMs;

  unsigned long largura;
  Resultado r = medir(largura);
  nTotal++;

  if (r == OK) {
    int mm = (int)(largura * CM_POR_US * 10.0 + 0.5);
    leituras[nOk++] = mm;
    if (anterior >= 0 && abs(mm - anterior) > 30) nSaltos++;
    anterior = mm;
    if (imprimirCada) {
      Serial.print(F("OK  d="));
      Serial.print(mm / 10.0, 1);
      Serial.print(F(" cm  ("));
      Serial.print(largura);
      Serial.println(F(" us)"));
    }
  } else {
    if (r == SEM_ALVO) nSemAlvo++;
    else if (r == MUDO) nMudo++;
    else nPreso++;
    if (imprimirCada) {
      if (r == SEM_ALVO) Serial.println(F("SEM ALVO"));
      else if (r == MUDO) Serial.println(F("MUDO"));
      else Serial.println(F("PRESO"));
    }
  }

  if (nTotal >= N) {
    mostrarResumo();
    zerarResumo();
  }
}
