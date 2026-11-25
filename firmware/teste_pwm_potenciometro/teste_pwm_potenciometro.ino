/*
  Teste de PWM do levitador pneumatico - ESP32-C3 Super Mini
  (placa na IDE: "ESP32C3 Dev Module")

  Pinos do C3 a evitar: GPIO 18/19 (USB), GPIO 2, 8, 9 (strapping; LED no 8)

  Le um potenciometro e aplica o valor como PWM (0-255) no gate do MOSFET
  que aciona o ventilador.

  Ligacoes:
    Potenciometro: extremos em 3V3 e GND, cursor no GPIO 1 (entrada ADC)
    MOSFET (logic-level, ex. AO3400 / IRLB8721):
      Gate   <- GPIO 7 (via resistor de 100-220 ohm) + 10k do gate para o GND
      Source -> GND (comum com o GND do ESP e da fonte do ventilador)
      Drain  -> (-) do ventilador
    Ventilador: (+) na fonte externa (ex. 12 V)
    Diodo de roda livre em paralelo com o ventilador (catodo no +)

  Monitor Serial (115200, com "USB CDC On Boot: Enabled"):
    digite um numero de 0 a 255 + Enter -> PWM fixo (ignora o potenciometro)
    digite "p" + Enter                  -> volta a usar o potenciometro
  O modo fixo serve para achar o PWM de equilibrio u0 (bola parada).
*/

const int PINO_POT = 3;          // precisa ser ADC1: GPIO 0-4 (GPIO 5 e ADC2, nao funciona no C3)
const int PINO_PWM = 4;          // gate do MOSFET

const int PWM_FREQ = 20000;      // 20 kHz: acima da faixa audivel
const int PWM_BITS = 8;          // 0..255, igual ao modelo do Simulink

const int AMOSTRAS_ADC = 16;     // media para reduzir ruido do potenciometro
const unsigned long PERIODO_MS = 40;  // mesmo Ts do modelo (0,04 s)

bool modoFixo = false;
int pwmFixo = 0;
String entrada;

int lerPotenciometro() {
  long soma = 0;
  for (int i = 0; i < AMOSTRAS_ADC; i++) {
    soma += analogRead(PINO_POT);
  }
  return soma / AMOSTRAS_ADC;    // 0..4095
}

void lerSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      entrada.trim();
      if (entrada.length() > 0) {
        if (entrada == "p" || entrada == "P") {
          modoFixo = false;
          Serial.println("# modo potenciometro");
        } else {
          pwmFixo = constrain(entrada.toInt(), 0, 255);
          modoFixo = true;
          Serial.printf("# modo fixo: PWM = %d\n", pwmFixo);
        }
      }
      entrada = "";
    } else {
      entrada += c;
    }
  }
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(PINO_POT, ADC_11db);   // faixa completa 0-3,3 V

  ledcAttach(PINO_PWM, PWM_FREQ, PWM_BITS);
  ledcWrite(PINO_PWM, 0);

  delay(500);
  Serial.println("# Teste PWM - levitador pneumatico");
  Serial.println("# tempo_ms;adc;pwm;modo");
}

void loop() {
  static unsigned long ultimo = 0;
  lerSerial();

  unsigned long agora = millis();
  if (agora - ultimo < PERIODO_MS) return;
  ultimo = agora;

  int adc = lerPotenciometro();
  int pwm;
  if (modoFixo) {
    pwm = pwmFixo;
  } else {
    pwm = map(adc, 0, 4095, 0, 255);
    if (pwm < 3) pwm = 0;              // garante motor desligado no inicio do curso
  }

  ledcWrite(PINO_PWM, pwm);

  Serial.printf("%lu;%d;%d;%s\n", agora, adc, pwm, modoFixo ? "fixo" : "pot");
}
