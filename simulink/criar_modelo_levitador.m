function criar_modelo_levitador()
%CRIAR_MODELO_LEVITADOR Gera o modelo Simulink levitador_bola.slx.
%   Malha fechada igual ao codigo do Arduino Uno (bola ja no ar):
%   referencia -> PID discreto (derivada na medicao) + u0 -> teto do PWM ->
%   ventilador -> bola (NAO linear, com PWM de equilibrio dependente da altura) ->
%   sensor (amostragem, ruido, resolucao, mediana de 3) -> realimentacao.
%   Os parametros vem do workspace (rode parametros_levitador antes de simular).

mdl = 'levitador_bola';
pasta = fileparts(mfilename('fullpath'));
if bdIsLoaded(mdl), close_system(mdl, 0); end
arq = fullfile(pasta, [mdl '.slx']);
if exist(arq, 'file'), delete(arq); end

new_system(mdl);
set_param(mdl, 'Solver', 'ode45', 'StopTime', 't_final', ...
    'MaxStep', 'Ts/8', 'ReturnWorkspaceOutputs', 'on');

%% ---------------- Nivel principal ----------------
add_block('simulink/Sources/From Workspace', [mdl '/Referencia [m]'], ...
    'VariableName', 'ref_ts', 'SampleTime', 'Ts', 'Interpolate', 'off', ...
    'OutputAfterFinalValue', 'Holding final value', 'Position', [10 83 75 117]);

% Referencia e medida relativas a h_ini: o erro nao muda e o filtro da derivada parte de zero
add_block('simulink/Math Operations/Bias', [mdl '/ref - h_ini'], 'Bias', '-h_ini', 'Position', [105 85 145 115]);
add_block('simulink/Math Operations/Bias', [mdl '/h - h_ini'], 'Bias', '-h_ini', 'Position', [105 140 145 170]);

% PID de 2 graus de liberdade com b = 1 e c = 0: P e I no erro, D so na medicao
add_block('simulink/Discrete/Discrete PID Controller (2DOF)', [mdl '/PID'], ...
    'Controller', 'PID', 'Form', 'Parallel', 'SampleTime', 'Ts', ...
    'P', 'Kp', 'I', 'Ki', 'D', 'Kd', 'N', 'N_filtro', 'b', '1', 'c', '0', ...
    'IntegratorMethod', 'Forward Euler', 'FilterMethod', 'Backward Euler', ...
    'LimitOutput', 'on', 'UpperSaturationLimit', 'folga', ...
    'LowerSaturationLimit', 'u_min - u0', 'AntiWindupMode', 'clamping', ...
    'Position', [180 85 270 170]);

add_block('simulink/Sources/Constant', [mdl '/u0 (feedforward)'], ...
    'Value', 'u0', 'Position', [215 205 270 235]);
add_block('simulink/Math Operations/Sum', [mdl '/Soma u0'], ...
    'Inputs', '|++', 'IconShape', 'round', 'Position', [310 118 330 138]);
add_block('simulink/Discontinuities/Saturation', [mdl '/PWM 0-255'], ...
    'UpperLimit', 'u_max', 'LowerLimit', 'u_min', 'Position', [365 113 405 143]);

add_subsystem_ventilador([mdl '/Ventilador'], [450 108 550 148]);
add_subsystem_bola([mdl '/Bola (nao linear)'], [610 108 720 148]);
add_subsystem_sensor([mdl '/Sensor ultrassonico'], [610 250 720 290]);

% Visualizacao e exportacao
add_block('simulink/Signal Routing/Mux', [mdl '/Mux'], 'Inputs', '3', ...
    'Position', [800 40 805 100]);
add_block('simulink/Sinks/Scope', [mdl '/Altura (ref, real, medida)'], 'Position', [880 55 910 85]);
add_block('simulink/Sinks/Scope', [mdl '/PWM'], 'Position', [450 -20 480 10]);
ws = {'ref', [105 -15 165 5]; 'h', [800 165 860 185]; ...
      'h_med', [800 300 860 320]; 'u', [450 45 510 65]};
for k = 1:size(ws,1)
    add_block('simulink/Sinks/To Workspace', [mdl '/ws_' ws{k,1}], ...
        'VariableName', ws{k,1}, 'SaveFormat', 'Timeseries', ...
        'SampleTime', 'Ts', 'Position', ws{k,2});
end

%% Ligacoes
L = @(a,b) add_line(mdl, a, b, 'autorouting', 'smart');
L('Referencia [m]/1', 'ref - h_ini/1');
L('ref - h_ini/1', 'PID/1');
L('Sensor ultrassonico/1', 'h - h_ini/1');
L('h - h_ini/1', 'PID/2');
L('PID/1', 'Soma u0/1');
L('u0 (feedforward)/1', 'Soma u0/2');
L('Soma u0/1', 'PWM 0-255/1');
L('PWM 0-255/1', 'Ventilador/1');
L('Ventilador/1', 'Bola (nao linear)/1');
L('Bola (nao linear)/1', 'Sensor ultrassonico/1');
L('Referencia [m]/1', 'Mux/1');
L('Bola (nao linear)/1', 'Mux/2');
L('Sensor ultrassonico/1', 'Mux/3');
L('Mux/1', 'Altura (ref, real, medida)/1');
L('PWM 0-255/1', 'PWM/1');
L('Referencia [m]/1', 'ws_ref/1');
L('Bola (nao linear)/1', 'ws_h/1');
L('Sensor ultrassonico/1', 'ws_h_med/1');
L('PWM 0-255/1', 'ws_u/1');

add_block('built-in/Note', [mdl '/Levitador pneumatico - controle PID de altura da bola'], ...
    'Position', [330 350]);

save_system(mdl, arq);
close_system(mdl);
fprintf('Modelo salvo em %s\n', arq);
end

%% ---------------- Subsistemas ----------------
function add_subsystem_ventilador(sys, pos)
% tau_v * dv_ar/dt = K_v*u - v_ar, partindo de v_ar_ini
add_block('simulink/Ports & Subsystems/Subsystem', sys, 'Position', pos);
Simulink.SubSystem.deleteContents(sys);
add_block('simulink/Sources/In1', [sys '/PWM'], 'Position', [20 48 50 62]);
add_block('simulink/Math Operations/Gain', [sys '/K_v'], 'Gain', 'K_v', 'Position', [80 40 120 70]);
add_block('simulink/Math Operations/Sum', [sys '/Dif'], 'Inputs', '+-', 'Position', [150 45 170 75]);
add_block('simulink/Math Operations/Gain', [sys '/1//tau_v'], 'Gain', '1/tau_v', 'Position', [200 45 250 75]);
add_block('simulink/Continuous/Integrator', [sys '/Motor + helice'], ...
    'InitialCondition', 'v_ar_ini', 'Position', [285 45 315 75]);
add_block('simulink/Sinks/Out1', [sys '/v_ar [m//s]'], 'Position', [380 53 410 67]);
add_line(sys, 'PWM/1', 'K_v/1');
add_line(sys, 'K_v/1', 'Dif/1');
add_line(sys, 'Dif/1', '1//tau_v/1');
add_line(sys, '1//tau_v/1', 'Motor + helice/1');
add_line(sys, 'Motor + helice/1', 'v_ar [m//s]/1');
add_line(sys, 'Motor + helice/1', 'Dif/2', 'autorouting', 'smart');
end

function add_subsystem_bola(sys, pos)
% y'' = g*( (v_ar - y')*|v_ar - y'| / v_eq(y)^2 - 1 ) + turbulencia ,  0 <= y <= h_max
% v_eq(y) = K_v*PWM_eq(y): curva medida nos voos (equivale a c(y)/m = g/v_eq(y)^2)
add_block('simulink/Ports & Subsystems/Subsystem', sys, 'Position', pos);
Simulink.SubSystem.deleteContents(sys);
add_block('simulink/Sources/In1', [sys '/v_ar'], 'Position', [20 43 50 57]);
add_block('simulink/Lookup Tables/1-D Lookup Table', [sys '/v_eq(h)'], ...
    'Table', 'K_v*pwm_eq', 'BreakpointsForDimension1', 'h_eq', ...
    'ExtrapMethod', 'Clip', 'Position', [30 140 80 180]);
add_block('simulink/Signal Routing/Mux', [sys '/Mux'], 'Inputs', '3', 'Position', [110 35 115 105]);
add_block('simulink/User-Defined Functions/Fcn', [sys '/Arrasto por massa'], ...
    'Expr', 'g*(u(1)-u(2))*abs(u(1)-u(2))/(u(3)*u(3))', 'Position', [145 55 320 85]);
add_block('simulink/Sources/Constant', [sys '/g'], 'Value', 'g', 'Position', [330 105 360 125]);
add_block('simulink/Sources/Random Number', [sys '/Ruido turb'], 'Variance', '1', ...
    'SampleTime', 'Ts', 'Seed', 'semente', 'Position', [145 190 185 220]);
add_block('simulink/Discrete/Discrete Transfer Fcn', [sys '/Turbulencia'], ...
    'Numerator', '[turb_sd*sqrt(1-turb_f^2)]', 'Denominator', '[1 -turb_f]', ...
    'SampleTime', 'Ts', 'Position', [215 185 320 225]);
add_block('simulink/Math Operations/Sum', [sys '/Soma'], 'Inputs', '+-+', 'Position', [400 55 420 115]);
add_block(sprintf('simulink/Continuous/Integrator,\nSecond-Order\nLimited'), ...
    [sys '/Integrador (limites do tubo)'], 'ICX', 'h_ini', 'ICDXDT', '0', 'LimitX', 'on', ...
    'UpperLimitX', 'h_max', 'LowerLimitX', '0', 'Position', [460 60 540 110]);
add_block('simulink/Sinks/Out1', [sys '/h [m]'], 'Position', [610 68 640 82]);
add_line(sys, 'v_ar/1', 'Mux/1');
add_line(sys, 'v_eq(h)/1', 'Mux/3', 'autorouting', 'smart');
add_line(sys, 'Mux/1', 'Arrasto por massa/1');
add_line(sys, 'Arrasto por massa/1', 'Soma/1');
add_line(sys, 'g/1', 'Soma/2', 'autorouting', 'smart');
add_line(sys, 'Ruido turb/1', 'Turbulencia/1');
add_line(sys, 'Turbulencia/1', 'Soma/3', 'autorouting', 'smart');
add_line(sys, 'Soma/1', 'Integrador (limites do tubo)/1');
add_line(sys, 'Integrador (limites do tubo)/1', 'h [m]/1');
add_line(sys, 'Integrador (limites do tubo)/1', 'v_eq(h)/1', 'autorouting', 'smart');
add_line(sys, 'Integrador (limites do tubo)/2', 'Mux/2', 'autorouting', 'smart');
end

function add_subsystem_sensor(sys, pos)
% h -> amostragem -> ruido -> resolucao -> mediana de 3 (como no codigo)
add_block('simulink/Ports & Subsystems/Subsystem', sys, 'Position', pos);
Simulink.SubSystem.deleteContents(sys);
add_block('simulink/Sources/In1', [sys '/h'], 'Position', [20 43 50 57]);
add_block('simulink/Discrete/Zero-Order Hold', [sys '/Amostragem'], 'SampleTime', 'Ts', 'Position', [80 35 120 65]);
add_block('simulink/Sources/Random Number', [sys '/Ruido'], 'Variance', 'ruido_s', ...
    'SampleTime', 'Ts', 'Seed', 'semente+1', 'Position', [80 95 120 125]);
add_block('simulink/Math Operations/Sum', [sys '/Soma ruido'], 'Inputs', '++', 'Position', [150 40 170 80]);
add_block('simulink/Discontinuities/Quantizer', [sys '/Resolucao'], 'QuantizationInterval', 'q_sens', 'Position', [200 45 240 75]);
add_block('simulink/Discrete/Unit Delay', [sys '/z1'], 'InitialCondition', 'h_ini', 'SampleTime', 'Ts', 'Position', [270 95 305 125]);
add_block('simulink/Discrete/Unit Delay', [sys '/z2'], 'InitialCondition', 'h_ini', 'SampleTime', 'Ts', 'Position', [330 145 365 175]);
add_block('simulink/Math Operations/MinMax', [sys '/min ab'], 'Function', 'min', 'Inputs', '2', 'Position', [420 40 450 70]);
add_block('simulink/Math Operations/MinMax', [sys '/max ab'], 'Function', 'max', 'Inputs', '2', 'Position', [420 95 450 125]);
add_block('simulink/Math Operations/MinMax', [sys '/min maxc'], 'Function', 'min', 'Inputs', '2', 'Position', [490 105 520 135]);
add_block('simulink/Math Operations/MinMax', [sys '/mediana'], 'Function', 'max', 'Inputs', '2', 'Position', [560 45 590 75]);
add_block('simulink/Sinks/Out1', [sys '/h_med [m]'], 'Position', [630 53 660 67]);
S = @(a,b) add_line(sys, a, b, 'autorouting', 'smart');
S('h/1', 'Amostragem/1');
S('Amostragem/1', 'Soma ruido/1');
S('Ruido/1', 'Soma ruido/2');
S('Soma ruido/1', 'Resolucao/1');
S('Resolucao/1', 'z1/1');
S('z1/1', 'z2/1');
S('Resolucao/1', 'min ab/1');
S('z1/1', 'min ab/2');
S('Resolucao/1', 'max ab/1');
S('z1/1', 'max ab/2');
S('max ab/1', 'min maxc/1');
S('z2/1', 'min maxc/2');
S('min ab/1', 'mediana/1');
S('min maxc/1', 'mediana/2');
S('mediana/1', 'h_med [m]/1');
end
