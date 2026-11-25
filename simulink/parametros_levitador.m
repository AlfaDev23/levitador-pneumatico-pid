%% PARAMETROS_LEVITADOR
% Parametros do levitador pneumatico (bola em tubo de ar, ventilador embaixo,
% sensor ultrassonico em cima), com os dados dos ensaios de 23/11/2026.
%
% Origem de cada valor:
%   [MEDIDO]  medido no sistema real      [PROJETO] arquivos das pecas 3D
%   [CODIGO]  igual ao Arduino Uno        [AJUSTE]  identificado, com incerteza
% Para escolher o modelo, defina "candidato" antes de rodar (1 = padrao).

if ~exist('candidato', 'var'), candidato = 1; end

%% 1) Constantes e geometria
g       = 9.81;         % gravidade [m/s^2]
D_bola  = 0.0495;       % diametro da bola de PLA [m]          [PROJETO]
D_tubo  = 0.0594;       % diametro interno do tubo PET [m]     [PROJETO]
obstrucao = (D_bola/D_tubo)^2;   % fracao da area do tubo ocupada pela bola
h_max   = 0.23;         % altura util da bola [m]              [MEDIDO]

%% 2) PWM medio que sustenta a bola em cada altura             [MEDIDO]
%  Medias em malha fechada, 5 voos (ensaios/graficos.py); desvio de 2 a 4 PWM.
h_eq   = [0     0.017 0.080 0.103 0.138 0.157 0.22 ];   % [m]
pwm_eq = [143.6 141.1 133.2 129.0 126.7 127.3 127.3];   % acima de 0,157 m: suposto constante

%% 3) Ventilador e bola: tau_v*dv/dt + v = K_v*u               [AJUSTE]
%  Identificados nos voos por maxima verossimilhanca. A estimativa muda com a
%  hipotese de turbulencia, por isso ha dois candidatos.
switch candidato
    case 1   % turbulencia correlacionada (0,06 s)
        K_v = 0.0163;  tau_v = 1.00;  turb_sd = 1.0;  turb_f = exp(-0.04/0.06);
    case 2   % turbulencia branca (melhor verossimilhanca)
        K_v = 0.0063;  tau_v = 0.56;  turb_sd = 4.0;  turb_f = 0;
end
u_min = 0;  u_max = 255;

%% 4) Sensor e microcontrolador                                [CODIGO/MEDIDO]
Ts      = 0.04;         % periodo de amostragem [s]
q_sens  = 0.003;        % resolucao observada do sensor [m]
ruido_s = (0.0025)^2;   % variancia do ruido de medicao [m^2]
semente = 1;            % semente dos ruidos

%% 5) Controlador gravado no Uno                               [CODIGO]
Kp = 130;  Ki = 5;  Kd = 250;       % forma paralela [PWM/m, PWM/(m.s), PWM.s/m]
N_filtro = 25;                      % filtro da derivada [rad/s]
u0    = 127;                        % feedforward no ar [PWM]
folga = 45;                         % teto do PWM = u0 + folga

%% 6) Ponto de operacao e funcao de transferencia em torno de h0
h0 = 0.14;                          % regiao em que o PWM quase nao depende da altura
pwm0 = interp1(h_eq, pwm_eq, h0);
v0 = K_v*pwm0;                      % velocidade media do ar no equilibrio [m/s]
a  = 2*g/v0;                        % polo da dinamica da bola [1/s]
%                   K_v * a
%   G(s) = ---------------------------
%           s * (s + a) * (tau_v*s + 1)
s  = tf('s');
G_vent = K_v/(tau_v*s + 1);         % PWM  -> velocidade do ar
G_bola = a/(s*(s + a));             % v_ar -> posicao da bola
G      = minreal(G_vent*G_bola);    % PWM  -> posicao da bola
G.InputName = 'PWM';  G.OutputName = 'altura [m]';

% Mais embaixo (h = 9 cm) o PWM de equilibrio cai com a altura: polo instavel
h1 = 0.09;
dpwm = (interp1(h_eq, pwm_eq, h1 + 0.005) - interp1(h_eq, pwm_eq, h1 - 0.005))/0.01;  % [PWM/m]
pwm1 = interp1(h_eq, pwm_eq, h1);
a1 = 2*g/(K_v*pwm1);
rigidez = -2*g*dpwm/pwm1;           % [1/s^2] (> 0: empurra para longe do equilibrio)
G_baixo = minreal(K_v/(tau_v*s + 1)*a1/(s^2 + a1*s - rigidez));
G_baixo.InputName = 'PWM';  G_baixo.OutputName = 'altura [m]';

%% 7) Ganho critico TEORICO pelo criterio de Routh (nao medido na planta)
Ku = (1 + a*tau_v)/(tau_v*K_v);     % [PWM/m]
wu = sqrt(a/tau_v);                 % [rad/s]
Tu = 2*pi/wu;                       % [s]

%% 8) Ensaio simulado: mesmos degraus do voo final2
t_final  = 66;
ref_ts   = timeseries([0.13; 0.16; 0.13], [0; 22; 44]);
h_ini    = 0.13;                    % bola ja no ar
v_ar_ini = K_v*pwm0;
