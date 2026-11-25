/*
  Controle PID de altura - levitador pneumatico - ESP32-C3 Super Mini
  (placa na IDE: "ESP32C3 Dev Module", "USB CDC On Boot: Enabled")

  Malha: sensor ultrassonico (topo) -> altura h -> PID + u0 -> PWM -> ventilador

  Ligacoes:
    Potenciometro (referencia de altura): cursor no GPIO 3, extremos em 3V3 e GND
    MOSFET: gate no GPIO 4 (100-220 ohm em serie + 10k para o GND)
    HC-SR04: TRIG no GPIO 6, ECHO no GPIO 7
      HC-SR04 de 5 V: VCC no 5V e divisor no ECHO (1k em serie, 2k para o GND)
      HC-SR04P / RCWL-1601 (3,3 V): VCC no 3V3, ECHO direto
    Pinos do C3 a evitar: 2, 8, 9 (strapping), 18, 19 (USB). ADC so no GPIO 0-4.

  Internamente o PID usa as unidades do Simulink: altura em metros, saida em
  PWM (0-255), ganhos em PWM/m. No Monitor Serial as alturas aparecem em cm.
    u = u0 + Kp*e + Ki*integral(e) + Kd*de/dt      (forma paralela)

  Comandos no Monitor Serial (115200, terminar com Enter):
    z          zera a altura: deixe a bola parada no FUNDO e envie "z"
    s          para o motor (PWM = 0)
    a          liga o PID (modo automatico)
    m 150      modo manual com PWM fixo (aceita decimais: m 242.5)
    f 20000    muda a frequencia do PWM [Hz] (100 a 40000)
    r 25       referencia fixa em centimetros
    p          referencia pelo potenciometro
    kp 56      | ki 49 | kd 16 | u0 144   -> altera os parametros
    ?          mostra os parametros atuais

  Saida (uma linha a cada Ts):
    t=  12.34 s | ref= 25.0 cm | h= 24.3 cm | erro=  0.7 cm | PWM=130.50 | Kp= 56.00 Ki= 49.00 Kd= 16.00 | auto
  Ao ligar, o motor fica PARADO. Envie "z" e depois "a".

  Sintonia por Ziegler-Nichols (2o metodo) no sistema real:
    1) ki 0 e kd 0;  2) aumente kp ate a bola oscilar com amplitude constante
       -> esse kp e o Ku, e o periodo da oscilacao e o Tu (medir no grafico)
    3) kp = 0.6*Ku, ki = kp/(Tu/2), kd = kp*(Tu/8)
*/

#include "driver/gpio.h"

// ---------------- Pinos ----------------
const int PINO_POT  = 3;
const int PINO_PWM  = 4;
const int PINO_TRIG = 6;
const int PINO_ECHO = 7;

// ---------------- Parametros ----------------
const float Ts = 0.040;               // periodo de amostragem [s]
uint32_t    pwmFreq = 300;            // [Hz] baixa para o IRLZ44N nao esquentar (comando "f")
const int   PWM_BITS = 10;            // 0..1023 no hardware: passos de 0,25 na escala 0-255
const float PWM_MIN = 0, PWM_MAX = 255;   // escala usada no PID e no Simulink
const float PWM_ESCALA = ((1 << PWM_BITS) - 1) / 255.0;

// Ganhos iniciais = Ziegler-Nichols do modelo do Simulink (valores tipicos).
// Ajustar depois de medir u0 e fazer o ensaio de ganho critico.
float Kp = 56.0;                      // [PWM/m]
float Ki = 49.0;                      // [PWM/(m.s)]
float Kd = 16.0;                      // [PWM.s/m]
float u0 = 122.0;                     // PWM de equilibrio (medido com "m", 300 Hz)
float N_filtro = 10.0;                // filtro da derivada [rad/s]

// Faixa de referencia pelo potenciometro [m]
float H_REF_MIN = 0.10;
float H_REF_MAX = 0.45;

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
String entrada;

// ---------------- PWM ----------------
// Recebe o PWM na escala 0-255 (com casas decimais) e converte para 10 bits
void escreverPWM(float pwm) {
  ledcWrite(PINO_PWM, (uint32_t)lroundf(constrain(pwm, PWM_MIN, PWM_MAX) * PWM_ESCALA));
}

// ---------------- Sensor ----------------
float lerDistancia() {
  digitalWrite(PINO_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PINO_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PINO_TRIG, LOW);
  unsigned long t = pulseIn(PINO_ECHO, HIGH, ECHO_TIMEOUT_US);
  if (t == 0) return ultimaDist;      // sem eco: mantem a ultima leitura
  ultimaDist = t * 1e-6 * VEL_SOM / 2.0;
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

float lerReferenciaPot() {
  long soma = 0;
  for (int i = 0; i < 8; i++) soma += analogRead(PINO_POT);
  return H_REF_MIN + (soma / 8.0) / 4095.0 * (H_REF_MAX - H_REF_MIN);
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
  float uSemI = u0 + P + Ki * integral + D;

  // Anti-windup por clamping: so integra se nao estiver saturado
  // ou se o erro estiver tirando a saida da saturacao
  bool satCima  = uSemI >= PWM_MAX && e > 0;
  bool satBaixo = uSemI <= PWM_MIN && e < 0;
  if (!satCima && !satBaixo) integral += e * Ts;

  float u = u0 + P + Ki * integral + D;
  return constrain(u, PWM_MIN, PWM_MAX);
}

// ---------------- Comandos ----------------
void mostrarParametros() {
  Serial.printf("# Kp=%.2f Ki=%.2f Kd=%.2f | u0=%.2f | N=%.1f | fundo=%.1f cm | fPWM=%lu Hz | ref=%s\n",
                Kp, Ki, Kd, u0, N_filtro, distFundo * 100, (unsigned long)pwmFreq,
                refPeloPot ? "potenciometro" : (String(refFixa * 100, 1) + " cm").c_str());
}

void tratarComando(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;
  int esp = cmd.indexOf(' ');
  String nome = (esp < 0 ? cmd : cmd.substring(0, esp));
  nome.toLowerCase();
  float valor = (esp < 0 ? NAN : cmd.substring(esp + 1).toFloat());

  if (nome == "z") {
    float soma = 0;
    for (int i = 0; i < 10; i++) { soma += lerDistancia(); delay(30); }
    distFundo = soma / 10;
    for (int i = 0; i < 3; i++) hBuf[i] = 0;
    Serial.printf("# zero: distancia ate a bola no fundo = %.1f cm\n", distFundo * 100);
  } else if (nome == "s") {
    modo = PARADO;
    Serial.println("# PARADO");
  } else if (nome == "a") {
    resetarPID(hBuf[2]);
    modo = AUTOMATICO;
    Serial.println("# PID ligado");
  } else if (nome == "m" && !isnan(valor)) {
    pwmManual = constrain(valor, PWM_MIN, PWM_MAX);
    modo = MANUAL;
    Serial.printf("# MANUAL: PWM = %.2f\n", pwmManual);
  } else if (nome == "f" && !isnan(valor)) {
    pwmFreq = constrain((uint32_t)valor, 100UL, 40000UL);
    if (ledcChangeFrequency(PINO_PWM, pwmFreq, PWM_BITS) == 0)
      Serial.println("# erro ao mudar a frequencia");
    else
      Serial.printf("# frequencia do PWM = %lu Hz\n", (unsigned long)pwmFreq);
  } else if (nome == "r" && !isnan(valor)) {
    refFixa = valor / 100.0; refPeloPot = false;   // comando em cm, PID em m
    Serial.printf("# referencia fixa = %.1f cm\n", refFixa * 100);
  } else if (nome == "p") {
    refPeloPot = true;
    Serial.println("# referencia pelo potenciometro");
  } else if (nome == "kp" && !isnan(valor)) { Kp = valor; mostrarParametros(); }
  else if (nome == "ki" && !isnan(valor)) { Ki = valor; integral = 0; mostrarParametros(); }
  else if (nome == "kd" && !isnan(valor)) { Kd = valor; mostrarParametros(); }
  else if (nome == "u0" && !isnan(valor)) { u0 = valor; mostrarParametros(); }
  else if (nome == "?") { mostrarParametros(); }
  else { Serial.println("# comando invalido (envie ? para ver os parametros)"); }
}

void lerSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { tratarComando(entrada); entrada = ""; }
    else entrada += c;
  }
}

// ---------------- Setup / Loop ----------------
void setup() {
  Serial.begin(115200);
  pinMode(PINO_TRIG, OUTPUT);
  pinMode(PINO_ECHO, INPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(PINO_POT, ADC_11db);
  ledcAttach(PINO_PWM, pwmFreq, PWM_BITS);
  // Corrente maxima no pino: carrega o gate do MOSFET mais rapido (menos aquecimento)
  gpio_set_drive_capability((gpio_num_t)PINO_PWM, GPIO_DRIVE_CAP_3);
  escreverPWM(0);

  delay(1000);
  Serial.println("# PID levitador - motor PARADO. Envie 'z' (bola no fundo) e depois 'a'.");
  mostrarParametros();
  Serial.println("# ganhos em PWM/m (mesmas unidades do Simulink)");
}

void loop() {
  static unsigned long proximo = micros();
  lerSerial();
  if ((long)(micros() - proximo) < 0) return;
  proximo += (unsigned long)(Ts * 1e6);

  float h   = lerAltura();
  float ref = refPeloPot ? lerReferenciaPot() : refFixa;

  float pwm = 0;
  if (modo == AUTOMATICO) pwm = calcularPID(ref, h);
  else if (modo == MANUAL) pwm = pwmManual;
  escreverPWM(pwm);

  const char *nomeModo = modo == AUTOMATICO ? "auto" : (modo == MANUAL ? "manual" : "parado");
  Serial.printf("t=%7.2f s | ref=%5.1f cm | h=%5.1f cm | erro=%6.1f cm | PWM=%6.2f | Kp=%6.2f Ki=%6.2f Kd=%6.2f | %s\n",
                millis() / 1000.0, ref * 100, h * 100, (ref - h) * 100, pwm, Kp, Ki, Kd, nomeModo);
}
